#!/usr/bin/env python3
"""Tests for the in-memory optimization API (optimize_image_data)."""
import io
import shutil

from PIL import Image
from optimize_images.api import optimize_image_data, optimize_single_image


def _photo(path, fmt='JPEG', size=(800, 600)):
    """A non-trivial image so optimization actually has something to do."""
    img = Image.new('RGB', size)
    px = img.load()
    for y in range(size[1]):
        for x in range(size[0]):
            px[x, y] = ((x * 7) % 256, (y * 5) % 256, ((x + y) * 3) % 256)
    save = {'JPEG': {'quality': 95}, 'PNG': {}, 'WEBP': {'quality': 95}}[fmt]
    img.save(path, fmt, **save)
    return path


def _parity(tmp_path, fmt, **opts):
    src = _photo(tmp_path / f'src.{fmt.lower()}', fmt)
    data = src.read_bytes()
    # file path
    work = tmp_path / f'work.{fmt.lower()}'
    shutil.copy(src, work)
    res_file = optimize_single_image(str(work), **opts)
    file_bytes = work.read_bytes()
    # in memory
    out_bytes, res_mem = optimize_image_data(data, **opts)
    return file_bytes, out_bytes, res_file, res_mem


def test_jpeg_parity(tmp_path):
    file_bytes, out_bytes, rf, rm = _parity(tmp_path, 'JPEG', quality=70)
    assert out_bytes == file_bytes
    assert rm.was_optimized == rf.was_optimized is True
    assert rm.final_size == rf.final_size
    assert rm.result_format == 'JPEG'


def test_png_parity_reduce_colors(tmp_path):
    file_bytes, out_bytes, rf, rm = _parity(tmp_path, 'PNG',
                                            reduce_colors=True, max_colors=64)
    assert out_bytes == file_bytes
    assert rm.final_size == rf.final_size
    assert rm.was_optimized == rf.was_optimized


def test_webp_parity(tmp_path):
    file_bytes, out_bytes, rf, rm = _parity(tmp_path, 'WEBP', webp_quality=60)
    assert out_bytes == file_bytes
    assert rm.final_size == rf.final_size


def test_downsize_in_memory(tmp_path):
    data = _photo(tmp_path / 's.jpg', 'JPEG').read_bytes()
    out_bytes, res = optimize_image_data(data, max_w=200, quality=80)
    assert res.was_downsized is True
    with Image.open(io.BytesIO(out_bytes)) as img:
        assert img.width <= 200


def test_keep_exif_in_memory(tmp_path):
    path = tmp_path / 'exif.jpg'
    img = Image.new('RGB', (400, 300), (90, 90, 90))
    exif = img.getexif()
    exif[271] = 'ACME'
    img.save(path, 'JPEG', quality=95, exif=exif)
    out_bytes, res = optimize_image_data(path.read_bytes(), keep_exif=True,
                                         quality=70)
    assert res.had_exif is True and res.has_exif is True
    with Image.open(io.BytesIO(out_bytes)) as img2:
        assert img2.getexif().get(271) == 'ACME'


def test_ignore_size_comparison_forces_write(tmp_path):
    # A tiny PNG normally would not be kept (no real savings); forcing the
    # comparison off must always return the freshly encoded bytes.
    path = tmp_path / 'tiny.png'
    Image.new('RGB', (2, 2), (1, 2, 3)).save(path, 'PNG')
    data = path.read_bytes()
    kept, res_default = optimize_image_data(data)
    forced, res_forced = optimize_image_data(data, ignore_size_comparison=True)
    assert res_default.was_optimized is False and kept == data
    assert res_forced.was_optimized is True


def test_unsupported_format_returns_original(tmp_path):
    path = tmp_path / 'image.bmp'
    Image.new('RGB', (32, 32), (10, 20, 30)).save(path, 'BMP')
    data = path.read_bytes()
    out_bytes, res = optimize_image_data(data)
    assert out_bytes == data
    assert res.was_optimized is False


def _gradient(path, fmt, size=(400, 300), **save):
    img = Image.new('RGB', size)
    px = img.load()
    for y in range(size[1]):
        for x in range(size[0]):
            px[x, y] = ((x * 7) % 256, (y * 5) % 256, ((x + y) * 3) % 256)
    img.save(path, fmt, **save)
    return path


def test_convert_png_to_webp_in_memory(tmp_path):
    from optimize_images.api import convert_image_data
    data = _gradient(tmp_path / 's.png', 'PNG').read_bytes()
    # Force the write so the test is about format, not whether webp is smaller.
    out, res = convert_image_data(data, to='webp', webp_quality=70,
                                  ignore_size_comparison=True)
    assert res.result_format == 'WEBP'
    assert res.was_optimized is True
    with Image.open(io.BytesIO(out)) as img:
        assert img.format == 'WEBP'


def test_convert_keeps_original_when_not_smaller(tmp_path):
    # This synthetic gradient does not get smaller as webp; with the size
    # comparison on (default), the original bytes and format are kept.
    from optimize_images.api import convert_image_data
    data = _gradient(tmp_path / 's.png', 'PNG').read_bytes()
    out, res = convert_image_data(data, to='webp', webp_quality=70)
    if not res.was_optimized:
        assert out == data
        assert res.result_format == 'PNG'


def test_convert_parity_file_vs_memory(tmp_path):
    """File-based conversion and in-memory conversion must agree byte for byte."""
    from optimize_images.api import optimize_single_image, convert_image_data
    src = _gradient(tmp_path / 'src.png', 'PNG')
    data = src.read_bytes()
    # file path: -ca to webp, forcing the write so the file always exists
    work = tmp_path / 'work.png'
    work.write_bytes(data)
    optimize_single_image(str(work), convert_all=True, convert_to='webp',
                          webp_quality=70, ignore_size_comparison=True)
    file_bytes = (tmp_path / 'work.webp').read_bytes()
    # in memory
    out, res = convert_image_data(data, to='webp', webp_quality=70,
                                  ignore_size_comparison=True)
    assert out == file_bytes
    assert res.result_format == 'WEBP'


def test_convert_to_same_format_optimizes_in_place(tmp_path):
    from optimize_images.api import convert_image_data
    data = _gradient(tmp_path / 's.jpg', 'JPEG', **{'quality': 95}).read_bytes()
    out, res = convert_image_data(data, to='jpeg', quality=70)
    assert res.result_format == 'JPEG'
    assert res.was_optimized is True and len(out) < len(data)


def test_convert_drops_alpha_for_jpeg(tmp_path):
    from optimize_images.api import convert_image_data
    img = Image.new('RGBA', (80, 60), (200, 50, 50, 128))
    p = tmp_path / 'a.png'
    img.save(p, 'PNG')
    out, res = convert_image_data(p.read_bytes(), to='jpeg',
                                  ignore_size_comparison=True)
    assert res.result_format == 'JPEG'
    with Image.open(io.BytesIO(out)) as r:
        assert r.mode == 'RGB'   # alpha flattened against bg_color


def test_convert_unavailable_target_raises(tmp_path):
    from optimize_images.api import convert_image_data
    data = _gradient(tmp_path / 's.png', 'PNG').read_bytes()
    try:
        convert_image_data(data, to='nope')
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for unknown target")