#!/usr/bin/env python3
"""The -i/--info mode prints an image's metadata and leaves it untouched
(plan 0.7).

Info mode is exclusive: only the image path may accompany it. It runs the CLI
through ``run_cli`` on copies made by the ``image_copy`` fixture.
"""
import re

from helpers import run_cli


def test_info_prints_the_metadata(image_copy):
    path = image_copy("jpeg_with_exif.jpg")
    before = path.read_bytes()
    proc = run_cli("-i", path)
    assert proc.returncode == 0, proc.stderr[-2000:]
    out = proc.stdout
    assert f"Image: {path}" in out
    for row in ("Format:", "JPEG", "Mode:", "RGB", "Dimensions:", " px",
                "Alpha:", "ICC profile:", "P3", "EXIF / "):
        assert row in out, row
    assert path.read_bytes() == before


def test_info_shows_alpha_and_no_exif(image_copy):
    path = image_copy("png_with_transparency.png")
    proc = run_cli("--info", path)
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert "PNG" in proc.stdout
    assert re.search(r"Alpha:\s+yes", proc.stdout)
    assert "EXIF: (none)" in proc.stdout


def test_info_rejects_other_options(image_copy):
    path = image_copy("jpeg_with_exif.jpg")
    before = path.read_bytes()
    proc = run_cli("-i", "-g", path)
    assert proc.returncode == 2
    assert "must be used on its own" in proc.stderr + proc.stdout
    assert path.read_bytes() == before


def test_info_reports_a_missing_file(tmp_path):
    missing = tmp_path / "missing.jpg"
    proc = run_cli("-i", missing)
    assert proc.returncode == 2
    assert "File not found" in proc.stderr + proc.stdout


def test_info_reports_an_unreadable_file(image_copy):
    proc = run_cli("-i", image_copy("not_image.txt"))
    assert proc.returncode == 2
    assert "Could not read image" in proc.stderr + proc.stdout
