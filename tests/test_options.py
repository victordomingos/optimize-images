#!/usr/bin/env python3
"""Behavioural tests for CLI/API options that had no automated coverage.

Self-contained: every image is generated under pytest's ``tmp_path``.
None of these tests needs scikit-image.
"""
import io
import random
from importlib import metadata

import pytest
from PIL import Image

from optimize_images.api import PublicBatchOptions, optimize_as_batch, \
    optimize_image_data, optimize_single_image


def _photo(size=(320, 240), seed=1):
    """Gradients plus seeded noise: lossy encoders give clearly different
    sizes for different quality settings."""
    rng = random.Random(seed)
    width, height = size
    data = bytearray()
    for y in range(height):
        for x in range(width):
            noise = rng.randint(-20, 20)
            data += bytes((max(0, min(255, x * 255 // width + noise)),
                           max(0, min(255, y * 255 // height + noise)),
                           max(0, min(255, (x + y) * 127 // (width + height)
                                          + noise))))
    return Image.frombytes('RGB', size, bytes(data))


def _noise_png(path, size):
    """An RGB PNG with (almost) every pixel a different colour."""
    rng = random.Random(7)
    Image.frombytes('RGB', size, rng.randbytes(size[0] * size[1] * 3)) \
        .save(path, 'PNG')
    return path


def _encode(img, fmt, **save):
    buf = io.BytesIO()
    img.save(buf, fmt, **save)
    return buf.getvalue()


# --- -cb / conv_big: convert only big photographic PNGs -------------------

def test_conv_big_converts_big_photographic_png(tmp_path):
    # Thresholds (constants.py): area >= 800x600, > 2**16 colours, and a
    # JPEG preview bigger than 80 KB.
    src = _noise_png(tmp_path / "big.png", (900, 700))
    result = optimize_single_image(str(src), conv_big=True)
    assert result.was_optimized
    assert result.result_format == 'JPEG'
    assert (tmp_path / "big.jpg").exists()


def test_conv_big_leaves_small_png_as_png(tmp_path):
    src = _noise_png(tmp_path / "small.png", (200, 150))
    result = optimize_single_image(str(src), conv_big=True)
    assert result.result_format == 'PNG'
    assert not (tmp_path / "small.jpg").exists()


# --- force_del: remove the original after a successful conversion --------

def test_force_del_removes_original_after_conversion(tmp_path):
    src = tmp_path / "photo.png"
    _photo().save(src, 'PNG')
    result = optimize_single_image(str(src), convert_all=True, force_del=True)
    assert result.was_optimized
    assert (tmp_path / "photo.jpg").exists()
    assert not src.exists()


def test_force_del_keeps_original_when_conversion_is_rejected(tmp_path):
    # A tiny flat PNG converts to a bigger JPEG: the result is rejected, so
    # the original must survive and no converted file may be left behind.
    src = tmp_path / "flat.png"
    Image.new('RGB', (16, 16), (10, 20, 30)).save(src, 'PNG')
    before = src.read_bytes()
    result = optimize_single_image(str(src), convert_all=True, force_del=True)
    assert not result.was_optimized
    assert src.read_bytes() == before
    assert not (tmp_path / "flat.jpg").exists()


# --- recursive=False (-nr): only the top-level folder ---------------------

def test_non_recursive_batch_skips_subfolders(tmp_path):
    top = tmp_path / "top.jpg"
    nested_dir = tmp_path / "nested"
    nested_dir.mkdir()
    nested = nested_dir / "nested.jpg"
    for path in (top, nested):
        _photo().save(path, 'JPEG', quality=95)
    nested_before = nested.read_bytes()

    result = optimize_as_batch(PublicBatchOptions(src_path=str(tmp_path),
                                                  recursive=False, jobs=1))
    assert [r.img for r in result.results] == [str(top)]
    assert nested.read_bytes() == nested_before


# --- grayscale (-g) -------------------------------------------------------

@pytest.mark.parametrize("fmt", ['JPEG', 'PNG'])
def test_grayscale_output_is_single_channel(fmt):
    data = _encode(_photo(), fmt, **({'quality': 95} if fmt == 'JPEG' else {}))
    out, result = optimize_image_data(data, grayscale=True,
                                      ignore_size_comparison=True)
    assert result.was_optimized
    with Image.open(io.BytesIO(out)) as img:
        assert img.mode == 'L'
        assert img.format == fmt


# --- -q / quality (plan 3.2) ----------------------------------------------

@pytest.mark.xfail(strict=True, reason="plan F3: without fast mode the JPEG "
                   "quality is chosen dynamically and -q is ignored")
def test_quality_option_changes_jpeg_size():
    data = _encode(_photo((640, 480)), 'JPEG', quality=98)
    low, _ = optimize_image_data(data, quality=50,
                                 ignore_size_comparison=True)
    high, _ = optimize_image_data(data, quality=95,
                                  ignore_size_comparison=True)
    assert len(low) < len(high)


def test_quality_option_applies_in_fast_mode():
    data = _encode(_photo((640, 480)), 'JPEG', quality=98)
    low, _ = optimize_image_data(data, quality=50, fast_mode=True,
                                 ignore_size_comparison=True)
    high, _ = optimize_image_data(data, quality=95, fast_mode=True,
                                  ignore_size_comparison=True)
    assert len(low) < len(high)


# --- packaging ------------------------------------------------------------

def test_console_script_entry_point():
    # The tests run the CLI as "python -m optimize_images"; this checks that
    # the declared "optimize-images" command (setup.py console_scripts, as
    # seen by importlib.metadata) still points to the same entry function.
    try:
        dist = metadata.distribution('optimize-images')
    except metadata.PackageNotFoundError:
        pytest.skip("optimize-images is not installed in this venv")
    scripts = {ep.name: ep.value for ep in dist.entry_points
               if ep.group == 'console_scripts'}
    assert scripts.get('optimize-images') == 'optimize_images.__main__:main'
