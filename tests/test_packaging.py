#!/usr/bin/env python3
"""Packaging metadata must match the supported Python and dependency versions.

Python 3.10 reached end of life on 2026-10-01; the project supports every
CPython release still supported upstream (3.11+), and moves its minimum when
the oldest one reaches end of life. requirements-min.txt pins the oldest
supported dependencies, which setup.py must accept.
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SETUP = (ROOT / "setup.py").read_text(encoding="utf-8")
MIN_REQUIREMENTS_FILE = ROOT / "requirements-min.txt"

MINIMUM_PYTHON = (3, 11)
SUPPORTED = ["3.11", "3.12", "3.13", "3.14", "3.15"]


def test_python_requires_matches_minimum():
    assert "python_requires='>=%d.%d'" % MINIMUM_PYTHON in SETUP


def test_install_time_check_matches_minimum():
    assert "required = (%d, %d)" % MINIMUM_PYTHON in SETUP
    assert "Python %d.%d or later is required" % MINIMUM_PYTHON in SETUP


def test_classifiers_list_exactly_the_supported_versions():
    declared = re.findall(r"Programming Language :: Python :: (3\.\d+)'", SETUP)
    assert declared == SUPPORTED
    assert "Programming Language :: Python :: Free Threading" in SETUP


def test_ssim_extra_declares_numpy():
    match = re.search(r"extras_require=\{'ssim': \[([^\]]*)\]\}", SETUP)
    assert match, "extras_require ssim not found"
    assert re.search(r"'numpy>=1\.26'", match.group(1))


@pytest.mark.skipif(not MIN_REQUIREMENTS_FILE.exists(),
                    reason="requirements-min.txt not present")
def test_minimum_requirements_satisfy_setup():
    # The oldest pinned versions must be accepted by setup.py's ranges.
    pins = dict(re.findall(r"^([A-Za-z0-9_-]+)==([\d.]+)",
                           MIN_REQUIREMENTS_FILE.read_text(encoding="utf-8"),
                           re.M))
    floors = dict(re.findall(r"'([A-Za-z0-9_-]+)>=([\d.]+)'", SETUP))
    for name, floor in floors.items():
        key = next((p for p in pins if p.lower() == name.lower()), None)
        if key is None:
            continue
        pinned = tuple(int(x) for x in pins[key].split("."))
        assert pinned >= tuple(int(x) for x in floor.split(".")), name
