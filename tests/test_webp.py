#!/usr/bin/env python3
"""Functional tests for WebP support (optimization, conversion, discovery).

Self-contained: every test generates its own images under pytest's ``tmp_path``
and exercises the public API. Runs together with the rest of the suite via
``pytest tests/``. Requires Pillow built with WebP support.
"""
import os

from PIL import Image
from optimize_images.api import (optimize_single_image, optimize_as_batch,
                                 PublicBatchOptions)
from optimize_images.constants import SUPPORTED_FORMATS
from optimize_images.file_utils import search_images


def _photo(path, fmt, size=(640, 480), **save):
    """A non-trivial image so optimization has something to work on."""
    img = Image.new('RGB', size)
    px = img.load()
    for y in range(size[1]):
        for x in range(size[0]):
            px[x, y] = ((x * 2) % 256, (y * 3) % 256, (x * y) % 256)
    img.save(path, fmt, **save)
    return path


def _alpha(path, fmt, size=(320, 240), **save):
    """An image with a non-trivial alpha channel."""
    img = Image.new('RGBA', size)
    px = img.load()
    for y in range(size[1]):
        for x in range(size[0]):
            px[x, y] = (x % 256, y % 256, (x + y) % 256, x % 256)
    img.save(path, fmt, **save)
    return path


def _animated_webp(path):
    frame1 = Image.new('RGB', (64, 64), (255, 0, 0))
    frame2 = Image.new('RGB', (64, 64), (0, 0, 255))
    frame1.save(path, save_all=True, append_images=[frame2], duration=200,
                loop=0)
    return path


def _mixed_folder(tmp_path):
    """Build the standard mixed set of six images and return the folder."""
    _photo(tmp_path / 'photo.png', 'PNG')
    _photo(tmp_path / 'photo.jpg', 'JPEG', quality=95)
    _photo(tmp_path / 'photo.webp', 'WEBP', quality=95, method=0)
    _alpha(tmp_path / 'alpha.png', 'PNG')
    _alpha(tmp_path / 'alpha.webp', 'WEBP', quality=95, method=0)
    _animated_webp(tmp_path / 'anim.webp')
    return tmp_path


def test_webp_in_supported_formats():
    assert 'webp' in SUPPORTED_FORMATS


def test_reoptimized_webp_is_smaller_and_stays_webp(tmp_path):
    # Saved with method=0 (weak compression) so re-optimizing clearly helps.
    p = _photo(tmp_path / 'photo.webp', 'WEBP', quality=95, method=0)
    before = p.stat().st_size
    optimize_single_image(str(p), webp_quality=80, webp_method=6)
    assert p.stat().st_size < before
    with Image.open(p) as img:
        assert img.format == 'WEBP'


def test_webp_alpha_preserves_transparency(tmp_path):
    p = _alpha(tmp_path / 'alpha.webp', 'WEBP', quality=95, method=0)
    optimize_single_image(str(p), webp_quality=80)
    with Image.open(p) as img:
        assert 'A' in img.mode


def test_animated_webp_is_left_untouched(tmp_path):
    p = _animated_webp(tmp_path / 'anim.webp')
    before = p.stat().st_size
    result = optimize_single_image(str(p))
    assert result.was_optimized is False
    assert p.stat().st_size == before


def test_png_to_jpeg_is_the_default_conversion(tmp_path):
    png = _photo(tmp_path / 'photo.png', 'PNG')
    result = optimize_single_image(str(png), convert_all=True, quality=80)
    assert result.result_format == 'JPEG'
    assert (tmp_path / 'photo.jpg').exists()


def test_png_to_webp_conversion(tmp_path):
    png = _photo(tmp_path / 'photo.png', 'PNG')
    # The synthetic image does not always shrink as WebP; here we test the
    # conversion path itself, not the size outcome, so disable the comparison.
    result = optimize_single_image(str(png), convert_all=True,
                                   convert_to='webp',
                                   ignore_size_comparison=True)
    assert result.result_format == 'WEBP'
    assert (tmp_path / 'photo.webp').exists()


def test_png_alpha_to_webp_preserves_alpha(tmp_path):
    apng = _alpha(tmp_path / 'alpha.png', 'PNG')
    optimize_single_image(str(apng), convert_all=True, convert_to='webp',
                          ignore_size_comparison=True)
    with Image.open(tmp_path / 'alpha.webp') as img:
        assert 'A' in img.mode   # JPEG would have flattened it


def test_search_images_finds_webp(tmp_path):
    _mixed_folder(tmp_path)
    found = search_images(str(tmp_path), recursive=True)
    names = {os.path.basename(p) for p in found}
    assert 'photo.webp' in names


def test_batch_over_mixed_folder(tmp_path):
    _mixed_folder(tmp_path)
    res = optimize_as_batch(PublicBatchOptions(src_path=str(tmp_path),
                                               recursive=True, quality=80,
                                               webp_quality=80))
    # Stable guarantees only: all six are discovered, the counts are
    # consistent, the animated file is always skipped, and the clearly
    # compressible files are optimized. The exact optimized/skipped split is
    # left open because borderline files (e.g. an already-lean PNG) may or may
    # not cross the ~1% threshold depending on the Pillow/zlib version.
    assert res.found_files == 6
    assert res.optimized_files + res.skipped_files == res.found_files
    assert res.skipped_files >= 1
    assert res.optimized_files >= 4


def test_ignore_size_comparison_forces_write(tmp_path):
    # Re-optimizing an already-optimized WebP yields no gain, so by default it
    # is skipped; disabling the comparison must write it anyway.
    p = _photo(tmp_path / 'photo.webp', 'WEBP', quality=95, method=0)
    optimize_single_image(str(p), webp_quality=80, webp_method=6)
    result = optimize_single_image(str(p), webp_quality=80, webp_method=6,
                                   ignore_size_comparison=True)
    assert result.was_optimized is True


if __name__ == "__main__":
    import sys
    import pytest

    sys.exit(pytest.main(["-v", "--color=yes", __file__]))