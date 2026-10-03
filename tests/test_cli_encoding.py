#!/usr/bin/env python3
"""The CLI must not crash when a file name cannot be written in the output
encoding.

On Windows, when the output goes to a pipe or a file (logs, CI, scripts),
Python writes it in the ANSI code page (e.g. cp1252). File names coming from
macOS often store accents as a base letter plus a combining mark (U+0301),
which cp1252 cannot encode; printing such a path crashed the whole run
(found 2026-10-02 on Windows 11 with the benchmark corpus). Simulated here
with PYTHONIOENCODING=cp1252, so it runs on every platform.
"""
import os
import shutil

import pytest

from helpers import TEST_IMAGES, run_cli

UNENCODABLE_NAMES = [
    "cópia.jpg",        # 'ó' as o + combining acute (macOS style)
    "Łódź.jpg",  # 'Ł' is not in cp1252 either
]


@pytest.mark.parametrize("name", UNENCODABLE_NAMES)
def test_cli_survives_unencodable_file_name(tmp_path, name):
    shutil.copy(TEST_IMAGES / "jpeg_with_exif.jpg", tmp_path / name)
    env = {**os.environ, "PYTHONIOENCODING": "cp1252",
           "PYTHONWARNINGS": "error::DeprecationWarning"}
    # The CLI outputs cp1252 bytes (because of PYTHONIOENCODING=cp1252).
    # We must decode the captured output with errors="replace" so the test
    # runner itself does not choke on non-UTF-8 bytes.
    proc = run_cli(tmp_path, env=env, errors="replace")
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert "Optimized 1 files" in proc.stdout
