#!/usr/bin/env python3
from pathlib import Path
import os
import pytest

yaml = pytest.importorskip("yaml")  # dev requirement; may lack a wheel on new Pythons

from PIL import Image

from helpers import TEST_IMAGES, run_cli

BASE = Path(__file__).parent


def run_optimize(args, input_file):
    """Optimize input_file (a copy in tmp_path) and return the output path.

    A conversion (-ca) writes a file with another extension next to it
    (e.g. input.png => input.jpg); that file is returned when it exists.
    """
    proc = run_cli(input_file, *args, "--quiet")
    assert proc.returncode == 0, proc.stderr
    for ext in ("jpg", "jpeg", "png", "webp", "avif", "heic"):
        candidate = input_file.with_suffix(f".{ext}")
        if candidate.exists() and candidate != input_file:
            return candidate
    return input_file


def has_exif(path):
    try:
        with Image.open(path) as img:
            exif = getattr(img, "getexif", None)
            if exif is None:
                return False
            data = exif() if callable(exif) else exif
            return bool(data and len(data) > 0)
    except Exception:
        return False


def file_size(path):
    return os.path.getsize(path)


def palette_color_count(path):
    with Image.open(path) as img:
        if img.mode != "P" or img.palette is None:
            return None
        raw = getattr(img.palette, "palette", None)  # bytes, 3 bytes per color
        return (len(raw) // 3) if raw else 0


def unique_color_count(path, cap=1_000_000):
    with Image.open(path) as img:
        rgba = img.convert("RGBA")
        colors = rgba.getcolors(cap)
        return len(colors) if colors is not None else len(set(rgba.getdata()))


def image_mode(path):
    with Image.open(path) as img:
        return img.mode


def image_info(path):
    with Image.open(path) as img:
        fmt = img.format
        if fmt == "JPG":
            fmt = "JPEG"
        return fmt, img.size, img.info


def load_tests():
    with open(BASE / "tests_config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)["tests"]


def case_id(t):
    base = t.get("name") or t.get("input", "unnamed")
    note = t.get("note")
    return f"{base} [{note}]" if note else base


@pytest.mark.parametrize("case", load_tests(), ids=case_id)
def test_optimize_case(case, image_copy):
    orig = TEST_IMAGES / case["input"]
    assert orig.exists(), f"MISSING input: {case['input']}"

    out_file = run_optimize(case["args"], image_copy(case["input"]))

    context = {
        "orig": orig,
        "out": out_file,
        "file_size": file_size,
        "image_info": image_info,
        "has_exif": has_exif,
        "palette_color_count": palette_color_count,
        "unique_color_count": unique_color_count,
        "image_mode": image_mode,
    }

    try:
        ok = eval(case["check"], context)
    except Exception as e:
        pytest.fail(f"Exception in check: {e}")
    else:
        assert ok, "Check failed"


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main(["-v", "--color=yes", __file__]))
