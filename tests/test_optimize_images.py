#!/usr/bin/env python3
import subprocess
import shutil
from pathlib import Path
import os
import yaml
import pytest

from PIL import Image

BASE = Path(__file__).parent
INPUT = BASE / "test-images"
TMP = BASE / "tmp"
TMP.mkdir(exist_ok=True)

_created_tmp_files = set()


def run_optimize(args, input_file):
    tmp_file = TMP / input_file.name
    if tmp_file.exists():
        tmp_file.unlink()
    shutil.copy(input_file, tmp_file)
    _created_tmp_files.add(tmp_file)
    subprocess.run(["optimize-images", str(tmp_file)] + args + ["--quiet"], check=True)

    # If a new file was created with a different extension (-ca), report it.
    # Example: input.png => output.jpg
    stem = tmp_file.stem
    parent = tmp_file.parent
    candidates = [
        parent / f"{stem}.jpg",
        parent / f"{stem}.jpeg",
        parent / f"{stem}.png",
        parent / f"{stem}.webp",
        parent / f"{stem}.avif",
        parent / f"{stem}.heic",
    ]
    for c in candidates:
        if c.exists() and c != tmp_file:
            _created_tmp_files.add(c)
            return c

    return tmp_file


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
def test_optimize_case(case):
    input_file = INPUT / case["input"]
    assert input_file.exists(), f"MISSING input: {case['input']}"

    out_file = run_optimize(case["args"], input_file)

    context = {
        "orig": input_file,
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
    finally:
        # Remove only files we created, leave any pre-existing files intact
        for temp_file in list(_created_tmp_files):
            try:
                if temp_file.exists():
                    temp_file.unlink()
            finally:
                pass
                _created_tmp_files.discard(temp_file)


if __name__ == "__main__":
    import sys
    import pytest

    sys.exit(pytest.main(["-v", "--color=yes", __file__]))
