"""Closing the batch stream early: files not started yet are left untouched.

The stream keeps at most `jobs` files in the pool, so when the caller stops
reading only the files already in progress are finished. Before, every file
was submitted at once and a process pool moved some of them to its internal
call queue, where cancel_futures can no longer drop them (4 of 10 files
rewritten with jobs=1 on Linux). Both pool types run on every OS.
"""
import os
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

import pytest
from PIL import Image

import optimize_images.api as api
from optimize_images.api import PublicBatchOptions, optimize_as_batch_stream


def _noise_jpegs(folder, count, size=(600, 450)):
    """JPEGs of random noise: slow enough to encode that a batch lasts a while."""
    folder.mkdir()
    for i in range(count):
        Image.frombytes('RGB', size, os.urandom(size[0] * size[1] * 3)).save(
            folder / f'noise{i:02}.jpg', quality=95)
    return {p: p.read_bytes() for p in folder.iterdir()}


@pytest.mark.parametrize('jobs', [1, 2])
@pytest.mark.parametrize('pool', [ThreadPoolExecutor, ProcessPoolExecutor],
                         ids=['threads', 'processes'])
def test_closing_the_stream_early_cancels_queued_files(tmp_path, monkeypatch,
                                                       pool, jobs):
    monkeypatch.setattr(api, 'adjust_for_platform', lambda: (80, pool, jobs))
    before = _noise_jpegs(tmp_path / 'images', count=10)
    stream = optimize_as_batch_stream(
        PublicBatchOptions(src_path=str(tmp_path / 'images'), jobs=jobs))
    next(stream)
    stream.close()   # the caller stops reading: files not started are dropped
    untouched = sum(path.read_bytes() == data for path, data in before.items())
    # One result read, plus at most `jobs` files in progress (one of them may
    # have finished at the same time as the result that was read).
    assert untouched >= len(before) - (jobs + 1)
    for path in before:
        with Image.open(path) as img:   # nothing truncated or half-written
            img.load()
