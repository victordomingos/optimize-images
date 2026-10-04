#!/usr/bin/env python3
"""Public API watch_directory, in process (plan 0.9).

tests/test_watch.py covers -wd through the CLI (YAML cases, needs pyyaml); its
subprocesses are terminated, so they leave no coverage data. These tests run
the watcher in a thread and stop it with ``stop_event``: the API path, the
stop signal and the missing-folder error, on every Python (no pyyaml needed).
Images are generated in memory and written in one call, so the watcher never
sees a half-written file; timeouts are generous because file-system
notifications can lag (fsevents on macOS).
"""
import io
import os
import queue
import threading
import time

import pytest
from PIL import Image

from optimize_images.api import PublicBatchOptions, watch_directory

TIMEOUT = 20

# On free-threaded builds, watchdog's native module re-enables the GIL and
# says so with a RuntimeWarning; watch mode is serial, so it is harmless.
pytestmark = pytest.mark.filterwarnings(
    "ignore:The global interpreter lock:RuntimeWarning")


def _jpeg_bytes(size=(320, 240)):
    width, height = size
    img = Image.new("RGB", size)
    img.frombytes(bytes(v for y in range(height) for x in range(width)
                        for v in ((x * 255) // width, (y * 255) // height,
                                  (x * y) % 256)))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=95)
    return buf.getvalue()


def _start_watching(folder):
    results = queue.Queue()
    stop = threading.Event()

    def run():
        # An error in the watcher thread goes to the queue, so the test
        # fails at once with the real cause instead of timing out.
        try:
            watch_directory(PublicBatchOptions(src_path=str(folder)),
                            results.put, stop_event=stop)
        except BaseException as ex:  # noqa: BLE001 - reported to the test
            results.put(ex)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return results, stop, thread


def _next_result(results, timeout=TIMEOUT):
    item = results.get(timeout=timeout)
    if isinstance(item, BaseException):
        raise item
    return item


def test_watch_directory_optimizes_a_new_file(tmp_path):
    results, stop, thread = _start_watching(tmp_path)
    try:
        time.sleep(1)  # let the observer start before the file appears
        (tmp_path / "notes.txt").write_text("not an image")
        data = _jpeg_bytes()
        path = tmp_path / "new.jpg"
        path.write_bytes(data)

        result = _next_result(results)
        assert os.path.basename(result.img) == "new.jpg"
        assert result.was_optimized
        assert path.stat().st_size < len(data)
        with Image.open(path) as img:
            img.verify()
        # The text file is ignored: no second result.
        with pytest.raises(queue.Empty):
            results.get(timeout=1)
    finally:
        stop.set()
        thread.join(timeout=5)
    assert not thread.is_alive()


def test_watch_directory_goes_on_after_a_broken_file(tmp_path):
    # A file that cannot be read is reported as skipped (no error reason,
    # original kept) and the watcher keeps going with the next file.
    results, stop, thread = _start_watching(tmp_path)
    try:
        time.sleep(1)
        broken = tmp_path / "broken.jpg"
        broken_bytes = b"\xff\xd8\xff\xe0 not really a jpeg" * 20
        broken.write_bytes(broken_bytes)
        first = _next_result(results)
        assert os.path.basename(first.img) == "broken.jpg"
        assert not first.was_optimized and first.error is None
        assert broken.read_bytes() == broken_bytes

        data = _jpeg_bytes()
        (tmp_path / "good.jpg").write_bytes(data)
        second = _next_result(results)
        assert os.path.basename(second.img) == "good.jpg"
        assert second.was_optimized
    finally:
        stop.set()
        thread.join(timeout=5)
    assert not thread.is_alive()


def test_watch_directory_rejects_a_missing_folder(tmp_path):
    from optimize_images.exceptions import OIImagesNotFoundError
    with pytest.raises(OIImagesNotFoundError):
        watch_directory(PublicBatchOptions(src_path=str(tmp_path / "nope")),
                        lambda _result: None)
