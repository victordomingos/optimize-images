#!/usr/bin/env python3
"""Worker count of batch runs when the SSIM is computed (plan 5.8).

Measured 2026-10-02 (224-file corpus, 18-core Mac): with the SSIM gate, more
than ~8 concurrent workers makes every task much slower (scipy.ndimage work
competes for memory), so 8 workers beat the defaults: Python with the GIL on
macOS (64 threads) 77-99 s -> 19-20 s, free-threaded (18 threads) 18-48 s
(unstable) -> 16-18 s. Without the SSIM the defaults are fine. Rule:

* SSIM computed (ssim_min or show_ssim) and no explicit jobs:
  workers = min(default workers, 8);
* no SSIM: the platform default, unchanged;
* an explicit jobs value always wins.
"""
from concurrent.futures import ThreadPoolExecutor

import pytest
from PIL import Image

import optimize_images.api as api
from optimize_images.api import PublicBatchOptions, optimize_as_batch
from optimize_images.img_ssim import ssim_available

@pytest.fixture
def recorded_workers(monkeypatch):
    """Make the platform default 18 workers and record the pool size used."""
    used = []

    class RecordingPool(ThreadPoolExecutor):
        def __init__(self, max_workers=None, *args, **kwargs):
            used.append(max_workers)
            super().__init__(max_workers, *args, **kwargs)

    def fake_platform(default=18):
        return 80, RecordingPool, default

    monkeypatch.setattr(api, "adjust_for_platform", fake_platform)
    return used


def _folder(tmp_path):
    Image.new("RGB", (64, 48), (120, 60, 30)).save(tmp_path / "a.jpg",
                                                    quality=95)
    return str(tmp_path)


@pytest.mark.skipif(not ssim_available(), reason="scikit-image not installed")
def test_ssim_gate_caps_workers(tmp_path, recorded_workers):
    optimize_as_batch(PublicBatchOptions(src_path=_folder(tmp_path),
                                         ssim_min=0.5))
    assert recorded_workers == [8]


def test_show_ssim_caps_workers(tmp_path, recorded_workers):
    optimize_as_batch(PublicBatchOptions(src_path=_folder(tmp_path),
                                         show_ssim=True))
    assert recorded_workers == [8]


def test_without_ssim_keeps_platform_default(tmp_path, recorded_workers):
    optimize_as_batch(PublicBatchOptions(src_path=_folder(tmp_path)))
    assert recorded_workers == [18]


@pytest.mark.skipif(not ssim_available(), reason="scikit-image not installed")
def test_explicit_jobs_wins_over_ssim_cap(tmp_path, recorded_workers):
    optimize_as_batch(PublicBatchOptions(src_path=_folder(tmp_path),
                                         ssim_min=0.5, jobs=12))
    assert recorded_workers == [12]


@pytest.mark.skipif(not ssim_available(), reason="scikit-image not installed")
def test_ssim_cap_never_raises_a_smaller_default(tmp_path, monkeypatch):
    used = []

    class RecordingPool(ThreadPoolExecutor):
        def __init__(self, max_workers=None, *args, **kwargs):
            used.append(max_workers)
            super().__init__(max_workers, *args, **kwargs)

    monkeypatch.setattr(api, "adjust_for_platform",
                        lambda: (80, RecordingPool, 4))
    optimize_as_batch(PublicBatchOptions(src_path=_folder(tmp_path),
                                         ssim_min=0.5))
    assert used == [4]
