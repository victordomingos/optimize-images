"""Shared fixtures. CLI helpers live in helpers.py (import them from there)."""
import shutil
from pathlib import Path

import pytest

from helpers import TEST_IMAGES


@pytest.fixture
def image_copy(tmp_path):
    """Copy a fixture from tests/test-images into tmp_path and return the copy.

    Optimization is destructive, so the versioned fixtures are never used in
    place.
    """
    def copy(name, folder=None):
        target_dir = tmp_path / folder if folder else tmp_path
        target_dir.mkdir(parents=True, exist_ok=True)
        return Path(shutil.copy(TEST_IMAGES / name, target_dir / name))
    return copy
