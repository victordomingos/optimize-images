#!/usr/bin/env python3
import subprocess
import shutil
from pathlib import Path
from PIL import Image
import os
import yaml
import pytest

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


def image_info(path):
    with Image.open(path) as img:
        return img.format, img.size, img.info


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
    }

    try:
        ok = eval(case["check"], context)
    except Exception as e:
        pytest.fail(f"Exception in check: {e}")
    else:
        assert ok, "Check failed"
    finally:
        # Remove only files we created, leave any pre-existing files intact
        for p in list(_created_tmp_files):
            try:
                if p.exists():
                    p.unlink()
            finally:
                _created_tmp_files.discard(p)


if __name__ == "__main__":
    import sys
    import pytest

    sys.exit(pytest.main(["-v", "--color=yes", __file__]))
