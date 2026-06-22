#!/usr/bin/env python3
"""Tests for free-threading detection, executor selection and parallel batches.

Self-contained: tests that run a batch generate their own images under pytest's
``tmp_path`` instead of operating on the versioned ``tests/test-images`` folder,
which they would otherwise optimize in place and leave modified in the working
tree. Runs with the rest of the suite via ``pytest tests/``.

The parallel tests only run on a free-threaded interpreter (otherwise skipped);
the executor-selection test runs on any Python.
"""
import sys
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

import pytest
from PIL import Image
from optimize_images.api import optimize_as_batch, PublicBatchOptions
from optimize_images.platforms import is_free_threaded, select_executor


def _photo(path, fmt='JPEG', size=(320, 240), **save):
    """A small, deterministic, non-trivial image (so optimizing it helps and
    re-encoding is reproducible for serial-vs-parallel comparison)."""
    img = Image.new('RGB', size)
    px = img.load()
    for y in range(size[1]):
        for x in range(size[0]):
            px[x, y] = ((x * 2) % 256, (y * 3) % 256, (x * y) % 256)
    img.save(path, fmt, **save)
    return path


def _make_set(folder, n=6):
    folder.mkdir(parents=True, exist_ok=True)
    return [_photo(folder / f"img_{i}.jpg", quality=95) for i in range(n)]


def test_free_threading_detection():
    """Detection must agree with the interpreter's actual GIL state."""
    result = is_free_threaded()
    if hasattr(sys, '_is_gil_enabled'):
        assert result == (not sys._is_gil_enabled())
    else:
        assert result is False


@pytest.mark.parametrize("free_threaded, os_name, system, expected", [
    (True, 'posix', 'Linux', ThreadPoolExecutor),  # free-threaded: threads
    (True, 'posix', 'Darwin', ThreadPoolExecutor),
    (False, 'nt', 'Windows', ThreadPoolExecutor),  # Windows: threads
    (False, 'posix', 'Darwin', ThreadPoolExecutor),  # macOS: threads
    (False, 'posix', 'Linux', ProcessPoolExecutor),  # Linux: processes
])
def test_executor_selection(free_threaded, os_name, system, expected):
    """select_executor() picks the intended pool per platform.

    Runs on any Python: the policy is pure, so the platform indicators are
    passed explicitly. (We deliberately do not mutate the global ``os.name`` to
    simulate Windows, because that also drives path semantics process-wide.)
    """
    executor_class, default_workers = select_executor(
        free_threaded, os_name, system, num_cpus=4)
    assert executor_class is expected
    assert default_workers >= 1


@pytest.mark.skipif(not is_free_threaded(),
                    reason="Requires free-threaded Python")
def test_parallel_optimization_produces_valid_smaller_files(tmp_path):
    """A parallel batch finds everything, accounts for it consistently, and
    every output is a valid, smaller JPEG (not just a consistent count)."""
    sources = _make_set(tmp_path, n=6)
    orig_sizes = {p.name: p.stat().st_size for p in sources}

    result = optimize_as_batch(PublicBatchOptions(src_path=str(tmp_path),
                                                  recursive=False, quality=80,
                                                  jobs=4))

    assert result.found_files == 6
    assert result.optimized_files + result.skipped_files == result.found_files
    # These q95 photos must actually shrink, so nothing should be skipped.
    assert result.optimized_files == 6
    # Output integrity: each file is still a valid JPEG and got smaller. A
    # thread-safety bug could keep the counts consistent yet corrupt a file.
    for p in sources:
        with Image.open(p) as img:
            assert img.format == 'JPEG'
            img.verify()
        assert p.stat().st_size < orig_sizes[p.name]


@pytest.mark.skipif(not is_free_threaded(),
                    reason="Requires free-threaded Python")
def test_serial_and_parallel_results_match(tmp_path):
    """Same inputs must give the same outputs whether run with one worker or
    several. A divergence would expose a race in the parallel path."""
    serial_dir = tmp_path / "serial"
    parallel_dir = tmp_path / "parallel"
    _make_set(serial_dir, n=8)
    _make_set(parallel_dir, n=8)

    optimize_as_batch(PublicBatchOptions(src_path=str(serial_dir),
                                         recursive=False, quality=80, jobs=1))
    optimize_as_batch(PublicBatchOptions(src_path=str(parallel_dir),
                                         recursive=False, quality=80, jobs=4))

    serial_sizes = {p.name: p.stat().st_size
                    for p in serial_dir.iterdir()}
    parallel_sizes = {p.name: p.stat().st_size
                      for p in parallel_dir.iterdir()}
    assert serial_sizes == parallel_sizes


if __name__ == "__main__":
    sys.exit(pytest.main(["-v", "--color=yes", __file__]))
