#!/usr/bin/env python3
"""A parallel batch must give exactly the same files and decisions as a serial
one.

Runs on every build: threads on macOS/Windows and on free-threaded Python,
processes on Linux. Covers the paths that keep per-file state while workers
run at the same time: the palette rebuild (with tRNS), ICC profile handling
(the sRGB-equivalence cache) and the SSIM computation. A race would show up as
different bytes, decisions or scores between ``jobs=1`` and ``jobs=4``.

Self-contained: the images are generated under ``tmp_path``; the only fixture
read (never modified) is the Display P3 profile from ``jpeg_with_exif.jpg``.
"""
import hashlib
import shutil
from pathlib import Path

import pytest
from PIL import Image

from helpers import TEST_IMAGES
from optimize_images import img_icc
from optimize_images.api import PublicBatchOptions, optimize_as_batch_stream
from optimize_images.img_ssim import ssim_available

JOBS = 4


def _gradient(size=(160, 120)):
    width, height = size
    img = Image.new("RGB", size)
    img.frombytes(bytes(v for y in range(height) for x in range(width)
                        for v in ((x * 255) // width, (y * 255) // height,
                                  (x * y) % 256)))
    return img


def _p3_profile():
    with Image.open(TEST_IMAGES / "jpeg_with_exif.jpg") as img:
        return img.info["icc_profile"]


def _palette_with_trns(colors):
    """Palette image using ``colors`` entries, saved with a full 256-entry
    palette, a tRNS chunk and fast compression, so the rebuild shrinks it."""
    img = _gradient().quantize(colors)
    palette = img.getpalette() + [0] * (768 - len(img.getpalette()))
    img.putpalette(palette)
    img.info["transparency"] = bytes([0] + [255] * 255)
    return img


def _make_set(folder):
    folder.mkdir()
    photo = _gradient()
    for i in range(3):
        photo.rotate(90 * i).save(folder / f"photo_{i}.jpg", quality=95)
    for i in range(3):
        photo.rotate(90 * i).save(folder / f"photo_p3_{i}.jpg", quality=95,
                                  icc_profile=_p3_profile())
    for colors in (8, 64):
        _palette_with_trns(colors).save(folder / f"palette_{colors}.png",
                                        compress_level=1)
    rgba = photo.convert("RGBA")
    rgba.putalpha(200)
    rgba.save(folder / "rgba.png", compress_level=1)
    photo.save(folder / "photo.webp", quality=95)


def _run(folder, jobs, **options):
    results = optimize_as_batch_stream(PublicBatchOptions(
        src_path=str(folder), recursive=False, jobs=jobs, **options))
    return {Path(r.img).name: r for r in results}


def _digests(folder):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in folder.iterdir()}


def _serial_and_parallel(tmp_path, **options):
    serial, parallel = tmp_path / "serial", tmp_path / "parallel"
    _make_set(serial)
    shutil.copytree(serial, parallel)
    serial_results = _run(serial, 1, **options)
    # Start the parallel run with cold module caches, so several workers
    # fill the sRGB-equivalence cache and the test cube at the same time
    # (with threads, the serial run would otherwise have filled them).
    img_icc._srgb_cache.clear()
    img_icc._test_cube = None
    parallel_results = _run(parallel, JOBS, **options)
    return serial, parallel, serial_results, parallel_results


def _assert_same(serial, parallel, serial_results, parallel_results):
    assert set(serial_results) == set(parallel_results) == {
        p.name for p in serial.iterdir()}
    assert _digests(serial) == _digests(parallel)
    for name, s in serial_results.items():
        p = parallel_results[name]
        assert (s.was_optimized, s.final_size, s.result_mode, s.ssim) == \
               (p.was_optimized, p.final_size, p.result_mode, p.ssim), name


def test_parallel_batch_matches_serial(tmp_path):
    serial, parallel, s_res, p_res = _serial_and_parallel(tmp_path)
    _assert_same(serial, parallel, s_res, p_res)
    # Guard against a trivial pass: the parallel paths really ran.
    assert s_res["palette_8.png"].was_optimized
    assert s_res["palette_64.png"].was_optimized
    assert s_res["photo_p3_0.jpg"].was_optimized


@pytest.mark.skipif(not ssim_available(), reason="scikit-image not installed")
def test_parallel_batch_with_ssim_matches_serial(tmp_path):
    serial, parallel, s_res, p_res = _serial_and_parallel(
        tmp_path, ssim_min=0.5, show_ssim=True)
    _assert_same(serial, parallel, s_res, p_res)
    for name in ("photo_0.jpg", "photo_p3_0.jpg", "photo.webp"):
        assert s_res[name].ssim is not None, name
        assert s_res[name].was_optimized, name
