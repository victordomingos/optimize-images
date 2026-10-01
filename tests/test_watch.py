#!/usr/bin/env python3
import subprocess
import shutil
import time
from pathlib import Path
import os
import pytest

yaml = pytest.importorskip("yaml")  # dev requirement; may lack a wheel on new Pythons

from PIL import Image

from helpers import TEST_IMAGES, start_cli

BASE = Path(__file__).parent

# The watcher gives no signal when its file-system observer is ready.
WATCHER_STARTUP = 1.0
POLL_INTERVAL = 0.1
CHANGE_TIMEOUT = 10.0      # upper bound when a change is expected
NO_CHANGE_WAIT = 1.5       # how long to watch a file that must stay as it is


# --- Helpers ---

def run_watcher(watch_dir, input_file, args=None, subdir=None,
                expect_change=True):
    """Watch watch_dir, copy input_file into it (or into subdir) and return
    the copied file once the watcher has rewritten it (or after a short wait
    when no change is expected)."""
    target_dir = watch_dir / subdir if subdir else watch_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    out_file = target_dir / input_file.name

    proc = start_cli("-wd", watch_dir, *(args or []), "--quiet")
    try:
        time.sleep(WATCHER_STARTUP)
        assert proc.poll() is None, f"watcher exited early: {proc.stderr.read()}"
        shutil.copy(input_file, out_file)
        size_before = os.path.getsize(out_file)
        deadline = time.monotonic() + (CHANGE_TIMEOUT if expect_change
                                       else NO_CHANGE_WAIT)
        while time.monotonic() < deadline:
            if out_file.exists() and os.path.getsize(out_file) != size_before:
                break
            time.sleep(POLL_INTERVAL)
        assert proc.poll() is None, f"watcher exited: {proc.stderr.read()}"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
    stderr = proc.stderr.read()
    assert "Traceback" not in stderr, stderr
    return out_file


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
        fmt = img.format
        if fmt == "JPG":
            fmt = "JPEG"
        return fmt, img.size, img.info


def load_tests():
    with open(BASE / "test_watch_config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)["tests"]


def case_id(t):
    base = t.get("name") or t.get("input", "unnamed")
    note = t.get("note")
    return f"{base} [{note}]" if note else base


# --- Parametrized tests ---

@pytest.mark.parametrize("case", load_tests(), ids=case_id)
def test_watch_case(case, tmp_path):
    input_file = TEST_IMAGES / case["input"]
    assert input_file.exists(), f"MISSING input: {case['input']}"

    out_file = run_watcher(tmp_path, input_file, args=case.get("args"),
                           subdir=case.get("subdir"),
                           expect_change=case.get("expect_change", True))

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


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main(["-v", "--color=yes", __file__]))
