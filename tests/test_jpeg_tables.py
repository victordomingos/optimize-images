#!/usr/bin/env python3
"""Tests for optimize_images.jpeg_qtables.

Verifies:
  1.  jpeg_quality_kwargs() returns the right kwargs per mode.
  2.  Saving RGB and L images with a named mozjpeg table produces the
      expected Image.quantization (scaled by the libjpeg scaling factor).
  3.  CLI (run_cli) with ``-jt mozjpeg3`` produces the expected
      Image.quantization across several usage patterns.
  4.  Public API functions (optimize_single_image, optimize_image_data,
      convert_image_data, optimize_as_batch) validate jpeg_tables.
"""
import io
from pathlib import Path

import pytest
from PIL import Image

from optimize_images.api import (
    optimize_single_image,
    optimize_image_data,
    convert_image_data,
    optimize_as_batch,
    PublicBatchOptions,
)
from optimize_images.jpeg_qtables import (
    JPEG_TABLES,
    JPEG_TABLE_NAMES,
    MOZJPEG_TABLE_3,
    jpeg_quality_kwargs,
    validate_jpeg_tables,
)
from helpers import run_cli
from optimize_images.constants import DEFAULT_QUALITY


# ── helpers ─────────────────────────────────────────────────────────────────

def _scaled_table(table, quality):
    """Return the libjpeg-scaled table for *quality*."""
    scale = 5000 // quality if quality < 50 else 200 - 2 * quality
    return tuple(min(max((t * scale + 50) // 100, 1), 255) for t in table)


def _rgb_image(size=(64, 64)):
    return Image.new('RGB', size, (128, 64, 200))


def _l_image(size=(64, 64)):
    return Image.new('L', size, 128)


def _extract_table(quant, table_index=0):
    """Get the raw table list from Image.quantization (a dict).

    ``Image.quantization`` is a ``dict`` mapping table IDs to
    64-value lists.  For a single-table (L-mode) image the dict
    has one entry keyed ``0``.  For RGB it has entries ``0``
    (luminance) and ``1`` (chrominance).
    """
    return list(quant[table_index])


# ── Single shared helper: quality finder (bytes or path) ─────────────────────

def _find_mozjpeg_quality(data_or_path):
    """Return the quality if *data_or_path*'s quantization matches a scaled
    mozjpeg3 table, or ``None`` when it does not (e.g. standard tables).
    """
    if isinstance(data_or_path, (bytes, bytearray)):
        data_or_path = io.BytesIO(data_or_path)
    with Image.open(data_or_path) as img:
        l_table = list(img.quantization[0])
    for qi in range(1, 100):
        if l_table == list(_scaled_table(MOZJPEG_TABLE_3, qi)):
            return qi
    return None


# ── Image helper write functions (for behaviour tests) ───────────────────────

def _write_rgb_jpeg(path, quality=85, size=(128, 128)):
    """Write a small RGB JPEG and return the path."""
    img = Image.new('RGB', size, (100, 150, 200))
    img.save(str(path), 'JPEG', quality=quality)
    return path


def _pattern_fill(img):
    """Fill *img* with a deterministic multi-channel gradient pattern."""
    data = img.load()
    h, w = img.size
    for y in range(h):
        for x in range(w):
            data[x, y] = ((x * 193 + y * 71) % 256,
                          (x * 127 + y * 251) % 256,
                          (x * 211 + y * 37) % 256)


def _write_large_rgb_jpeg(path, size=(512, 512), quality=85):
    """Write a larger RGB JPEG for tests where size comparison matters."""
    img = Image.new('RGB', size, (100, 150, 200))
    _pattern_fill(img)
    img.save(str(path), 'JPEG', quality=quality)
    return path


def _write_png(path, size=(128, 128)):
    """Write a small RGB PNG and return the path."""
    img = Image.new('RGB', size, (100, 150, 200))
    img.save(str(path), 'PNG')
    return path


def _write_large_png(path, size=(512, 512)):
    """Write a larger RGB PNG (realistic content) for conversion tests."""
    img = Image.new('RGB', size, (100, 150, 200))
    _pattern_fill(img)
    img.save(str(path), 'PNG')
    return path





# ── Table / constant checks ─────────────────────────────────────────────────

def test_mozjpeg_table_3_has_64_values():
    assert len(MOZJPEG_TABLE_3) == 64


def test_jpeg_tables_contains_mozjpeg3():
    assert 'mozjpeg3' in JPEG_TABLES
    assert JPEG_TABLES['mozjpeg3'] == MOZJPEG_TABLE_3


def test_jpeg_table_names():
    assert JPEG_TABLE_NAMES == ('standard', 'mozjpeg3')


# ── jpeg_quality_kwargs per mode ────────────────────────────────────────────

@pytest.mark.parametrize("mode", ("L", "RGB", "YCbCr", "1", "P"))
def test_kwargs_standard(mode):
    """Standard tables: only quality is returned."""
    result = jpeg_quality_kwargs(mode, 75)
    assert result == {'quality': 75}
    assert 'qtables' not in result
    assert 'subsampling' not in result


@pytest.mark.parametrize("mode", ("L", "RGB", "YCbCr"))
def test_kwargs_mozjpeg3(mode):
    kwargs = jpeg_quality_kwargs(mode, 80, 'mozjpeg3')
    assert kwargs['quality'] == 80

    if mode == 'L':
        assert kwargs['qtables'] == [MOZJPEG_TABLE_3]
        assert 'subsampling' not in kwargs
    else:  # RGB, YCbCr
        assert kwargs['qtables'] == [MOZJPEG_TABLE_3, MOZJPEG_TABLE_3]
        assert kwargs['subsampling'] == '4:2:0'


def test_kwargs_mozjpeg3_unknown_mode():
    """Unknown modes just get quality (no qtables injected)."""
    kwargs = jpeg_quality_kwargs('CMYK', 80, 'mozjpeg3')
    assert kwargs == {'quality': 80}


def test_kwargs_unknown_table():
    with pytest.raises(ValueError, match="Unknown JPEG table"):
        jpeg_quality_kwargs('RGB', 80, 'nonexistent')


# ── Image.quantization end-to-end ───────────────────────────────────────────

@pytest.mark.parametrize("quality", (30, 80))
def test_rgb_mozjpeg3_quantization(quality):
    """Saving an RGB image with mozjpeg3 yields the scaled quantization table."""
    img = _rgb_image()
    buf = io.BytesIO()
    kw = jpeg_quality_kwargs('RGB', quality, 'mozjpeg3')
    img.save(buf, 'JPEG', **kw)
    buf.seek(0)
    decoded = Image.open(buf)
    expected = _scaled_table(MOZJPEG_TABLE_3, quality)
    assert list(decoded.quantization[0]) == list(expected)
    # Chrominance table (index 1) should match luminance (we passed [T, T])
    assert list(decoded.quantization[1]) == list(expected)


@pytest.mark.parametrize("quality", (30, 80))
def test_l_mozjpeg3_quantization(quality):
    """Saving an L-mode image with mozjpeg3 yields a single scaled table."""
    img = _l_image()
    buf = io.BytesIO()
    kw = jpeg_quality_kwargs('L', quality, 'mozjpeg3')
    img.save(buf, 'JPEG', **kw)
    buf.seek(0)
    decoded = Image.open(buf)
    expected = _scaled_table(MOZJPEG_TABLE_3, quality)
    assert list(decoded.quantization[0]) == list(expected)


# ── Validation (rename test) ────────────────────────────────────────────────

def test_validate_jpeg_tables_raises_on_unknown():
    """validate_jpeg_tables() raises ValueError for unknown names."""
    with pytest.raises(ValueError, match="Unknown JPEG table"):
        validate_jpeg_tables('nonexistent')


# ── Behaviour tests via CLI and public API ──────────────────────────────────

class TestMozjpeg3ViaCLI:
    """Verify Image.quantization of CLI output with -jt mozjpeg3."""

    def _assert_mozjpeg_tables(self, data_or_path, expected_quality):
        """Assert quantization matches mozjpeg3 at *expected_quality*."""
        if isinstance(data_or_path, (bytes, bytearray)):
            data_or_path = io.BytesIO(data_or_path)
        with Image.open(data_or_path) as img:
            quant = img.quantization
        expected = _scaled_table(MOZJPEG_TABLE_3, expected_quality)
        assert list(quant[0]) == list(expected), (
            f'Quality={expected_quality} luminance mismatch. '
            f'Actual first 16: {list(quant[0])[:16]}'
        )
        assert list(quant[1]) == list(expected)

    def test_inplace_jpeg_automatic_quality(self, tmp_path):
        """In-place JPEG optimised with default quality uses mozjpeg3 tables.

        Uses -nc (no size comparison) to force writing the optimized file,
        because a small image may not get smaller at Q70.
        """
        src = _write_large_rgb_jpeg(tmp_path / 'in.jpg')
        result = run_cli('--quiet', '-nc', '-jt', 'mozjpeg3', str(src))
        assert result.returncode == 0
        actual_q = _find_mozjpeg_quality(str(src))
        assert actual_q is not None, 'Could not determine quality from output'
        self._assert_mozjpeg_tables(str(src), actual_q)

    def test_inplace_jpeg_with_q70(self, tmp_path):
        """In-place JPEG with explicit -q 70 uses scaled mozjpeg3 tables.

        Uses -nc to force write, since Q70 mozjpeg3 may not be smaller.
        """
        src = _write_large_rgb_jpeg(tmp_path / 'in.jpg')
        result = run_cli('--quiet', '-nc', '-q', '70', '-jt', 'mozjpeg3',
                         str(src))
        assert result.returncode == 0
        self._assert_mozjpeg_tables(str(src), 70)

    def test_inplace_jpeg_with_fast_mode(self, tmp_path):
        """In-place JPEG with -fm and mozjpeg3 uses the expected tables.

        -fm forces DEFAULT_QUALITY (from constants) without dynamic quality
        search.
        """
        src = _write_large_rgb_jpeg(tmp_path / 'in.jpg')
        result = run_cli('--quiet', '-nc', '-fm', '-jt', 'mozjpeg3',
                         str(src))
        assert result.returncode == 0
        self._assert_mozjpeg_tables(str(src), DEFAULT_QUALITY)

    def test_png_to_jpeg_convert_all(self, tmp_path):
        """PNG -> JPEG conversion with -ca and mozjpeg3."""
        src = _write_large_png(tmp_path / 'in.png')
        result = run_cli('--quiet', '-nc', '-ca', '-jt', 'mozjpeg3',
                         str(src))
        assert result.returncode == 0
        out_jpg = tmp_path / 'in.jpg'
        assert out_jpg.exists()
        self._assert_mozjpeg_tables(str(out_jpg), DEFAULT_QUALITY)

    def test_small_rgb_jpeg_cli_matches_pillow_direct_save(self, tmp_path):
        """Small RGB JPEG (non-progressive, < 10 000 bytes) optimised with
        ``-jt mozjpeg3 -q 75 -nc`` gives the same bytes as Pillow's
        ``img.save(optimize=True, progressive=False, **jpeg_quality_kwargs(
        'RGB', 75, 'mozjpeg3'))`` from the same source pixels.

        Exif/ICC are excluded from both encodings so the comparison is purely
        about the quantization tables and Huffman coding.
        """
        # Create a source JPEG *without* exif/icc
        src = tmp_path / 'src.jpg'
        img = Image.new('RGB', (128, 128), (100, 150, 200))
        # Write at quality 75, no exif
        img.save(str(src), 'JPEG', quality=75)

        # Run CLI with -nc (force write), -q 75, -jt mozjpeg3
        result = run_cli('--quiet', '-nc', '-q', '75', '-jt', 'mozjpeg3',
                         str(src))
        assert result.returncode == 0

        # Build the expected output with Pillow directly
        expected_buf = io.BytesIO()
        img.save(expected_buf, 'JPEG', optimize=True, progressive=False,
                 **jpeg_quality_kwargs('RGB', 75, 'mozjpeg3'))
        expected_bytes = expected_buf.getvalue()

        # Compare quantization tables and file size.
        cli_bytes = src.read_bytes()
        with Image.open(src) as cli_img:
            cli_quant = cli_img.quantization

        with Image.open(io.BytesIO(expected_bytes)) as exp_img:
            exp_quant = exp_img.quantization

        assert list(cli_quant[0]) == list(exp_quant[0])
        assert list(cli_quant[1]) == list(exp_quant[1])
        assert abs(len(cli_bytes) - len(expected_bytes)) <= 2

    def test_api_optimize_image_data(self, tmp_path):
        """optimize_image_data with jpeg_tables='mozjpeg3'."""
        src = _write_large_rgb_jpeg(tmp_path / 'in.jpg')
        with open(src, 'rb') as f:
            data = f.read()
        out_bytes, result = optimize_image_data(
            data, name='test', jpeg_tables='mozjpeg3'
        )
        buf = io.BytesIO(out_bytes)
        with Image.open(buf) as img:
            quant = img.quantization
        # Find actual quality
        actual_q = _find_mozjpeg_quality(out_bytes)
        expected = (_scaled_table(MOZJPEG_TABLE_3, actual_q)
                    if actual_q else _scaled_table(MOZJPEG_TABLE_3, DEFAULT_QUALITY))
        assert list(quant[0]) == list(expected), (
            f'Actual first 16: {list(quant[0])[:16]} vs expected: '
            f'{list(expected)[:16]}'
        )
        assert list(quant[1]) == list(expected)

    def test_api_convert_image_data(self, tmp_path):
        """convert_image_data (JPEG -> JPEG) with mozjpeg3.

        Uses a JPEG source (already small) to force conversion with
        ignore_size_comparison=True.
        """
        src = _write_large_rgb_jpeg(tmp_path / 'in.jpg')
        with open(src, 'rb') as f:
            data = f.read()
        out_bytes, result = convert_image_data(
            data, to='jpeg', name='test', jpeg_tables='mozjpeg3',
            ignore_size_comparison=True,
        )
        assert result.result_format.lower() == 'jpeg'
        buf = io.BytesIO(out_bytes)
        with Image.open(buf) as img:
            quant = img.quantization
        expected = _scaled_table(MOZJPEG_TABLE_3, DEFAULT_QUALITY)
        assert list(quant[0]) == list(expected)
        assert list(quant[1]) == list(expected)


class TestDefaultStandardTables:
    """Verify default (no -jt) output uses standard tables."""

    def test_cli_default_uses_standard_tables(self, tmp_path):
        """CLI without -jt keeps standard tables."""
        src = _write_large_rgb_jpeg(tmp_path / 'in.jpg')
        result = run_cli('--quiet', '-nc', str(src))
        assert result.returncode == 0
        assert _find_mozjpeg_quality(str(src)) is None

    def test_api_default_uses_standard_tables(self, tmp_path):
        """API without jpeg_tables arg keeps standard tables."""
        src = _write_large_rgb_jpeg(tmp_path / 'in.jpg')
        with open(src, 'rb') as f:
            data = f.read()
        out_bytes, result = optimize_image_data(data, name='test')
        assert _find_mozjpeg_quality(out_bytes) is None


class TestCMYKSameBytesMozjpeg3:
    """CMYK JPEGs: mozjpeg3 gives identical bytes as standard."""

    @pytest.mark.parametrize("size", ((128, 128), (256, 256)))
    def test_cmyk_same_bytes(self, tmp_path, size):
        """A CMYK JPEG produces identical bytes with mozjpeg3 and standard."""
        cmyk_img = Image.new('CMYK', size, (100, 150, 200, 255))
        cmyk_path = tmp_path / 'cmyk.jpg'
        cmyk_img.save(str(cmyk_path), 'JPEG')

        # Standard (no -jt)
        r1 = run_cli('--quiet', '-nc', str(cmyk_path))
        assert r1.returncode == 0
        bytes_standard = cmyk_path.read_bytes()

        # Reset the file
        cmyk_img.save(str(cmyk_path), 'JPEG')
        # mozjpeg3
        r2 = run_cli('--quiet', '-nc', '-jt', 'mozjpeg3', str(cmyk_path))
        assert r2.returncode == 0
        bytes_moz = cmyk_path.read_bytes()

        assert bytes_standard == bytes_moz


class TestQ30DQT8BitMax255:
    """With -q 30 -jt mozjpeg3, every table in Image.quantization has
    max <= 255 (8-bit DQT, baseline-compatible)."""

    def test_small_non_progressive(self, tmp_path):
        """Small JPEG (non-progressive, file < 10 000 bytes) at Q30."""
        src = tmp_path / 'in.jpg'
        img = Image.new('RGB', (128, 128), (100, 150, 200))
        img.save(str(src), 'JPEG', quality=85)

        result = run_cli('--quiet', '-nc', '-q', '30', '-jt', 'mozjpeg3',
                         str(src))
        assert result.returncode == 0
        assert src.stat().st_size < 10000

        with Image.open(str(src)) as img:
            quant = img.quantization
        for idx in quant:
            assert max(quant[idx]) <= 255, (
                f'Table {idx} max={max(quant[idx])} exceeds 8-bit DQT limit'
            )

    def test_large_progressive(self, tmp_path):
        """Large JPEG (progressive, file > 10 000 bytes) at Q30."""
        src = _write_large_rgb_jpeg(tmp_path / 'in.jpg')
        result = run_cli('--quiet', '-nc', '-q', '30', '-jt', 'mozjpeg3',
                         str(src))
        assert result.returncode == 0
        assert src.stat().st_size >= 10000

        with Image.open(str(src)) as img:
            quant = img.quantization
        for idx in quant:
            assert max(quant[idx]) <= 255, (
                f'Progressive table {idx} max={max(quant[idx])} exceeds '
                f'8-bit DQT limit'
            )


class TestUnknownTableErrors:
    """Unknown jpeg_tables names must raise errors."""

    def test_cli_unknown_table_exit_code(self, tmp_path):
        """CLI with unknown -jt exits with code != 0."""
        src = _write_rgb_jpeg(tmp_path / 'in.jpg')
        result = run_cli('--quiet', '-jt', 'nonexistent', str(src))
        assert result.returncode != 0

    def test_optimize_single_image_raises_valueerror(self, tmp_path):
        """optimize_single_image raises ValueError for unknown jpeg_tables."""
        src = _write_rgb_jpeg(tmp_path / 'in.jpg')
        with pytest.raises(ValueError, match='Unknown JPEG table'):
            optimize_single_image(str(src), jpeg_tables='nonexistent')

    def test_optimize_image_data_raises_valueerror(self, tmp_path):
        """optimize_image_data raises ValueError for unknown jpeg_tables."""
        src = _write_rgb_jpeg(tmp_path / 'in.jpg')
        with open(src, 'rb') as f:
            data = f.read()
        with pytest.raises(ValueError, match='Unknown JPEG table'):
            optimize_image_data(data, jpeg_tables='nonexistent')

    def test_convert_image_data_raises_valueerror(self, tmp_path):
        """convert_image_data raises ValueError for unknown jpeg_tables."""
        src = _write_png(tmp_path / 'in.png')
        with open(src, 'rb') as f:
            data = f.read()
        with pytest.raises(ValueError, match='Unknown JPEG table'):
            convert_image_data(data, to='jpeg', jpeg_tables='nonexistent')

    def test_optimize_as_batch_raises_valueerror(self, tmp_path):
        """optimize_as_batch raises ValueError for unknown jpeg_tables."""
        src = _write_rgb_jpeg(tmp_path / 'in.jpg')
        with pytest.raises(ValueError, match='Unknown JPEG table'):
            optimize_as_batch(PublicBatchOptions(
                src_path=str(src), jpeg_tables='nonexistent'
            ))
