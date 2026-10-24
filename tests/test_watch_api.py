#!/usr/bin/env python3
"""Public API watch_directory, in process (plan 0.9).

tests/test_watch.py covers -wd through the CLI (YAML cases, needs pyyaml); its
subprocesses are terminated, so they leave no coverage data. These tests run
the watcher in a thread and stop it with ``stop_event``: the API path, the
stop signal and the missing-folder error, on every Python (no pyyaml needed).
Images are generated in memory and written in one call, so the watcher never
sees a half-written file (except in the slow-write test, on purpose);
timeouts are generous because file-system notifications can lag (fsevents on
macOS).
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


def _png_bytes(size=(320, 240)):
    with Image.open(io.BytesIO(_jpeg_bytes(size))) as img:
        buf = io.BytesIO()
        img.save(buf, "PNG")
    return buf.getvalue()


def _start_watching(folder, on_result=None, results=None, **options):
    results = queue.Queue() if results is None else results
    on_result = results.put if on_result is None else on_result
    stop = threading.Event()

    def run():
        # An error in the watcher thread goes to the queue, so the test
        # fails at once with the real cause instead of timing out.
        try:
            watch_directory(PublicBatchOptions(src_path=str(folder), **options),
                            on_result, stop_event=stop)
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


# --------------------------------------------------------------------------
# Robustness: failing callback, renames, re-created files, own output, slow
# writes
# --------------------------------------------------------------------------
#
# A missing result is detected with a sentinel instead of a long timeout: one
# observer thread dispatches the events in order, so once the result for a
# file written after the action comes back, every earlier event has been
# handled. On macOS, FSEvents reports a temp file renamed into place only as
# "moved", a file moved in from another folder only as "created", and a
# delete + re-create as "deleted" then "created".

SENTINEL = "zz-sentinel.jpg"
SETTLE = 0.3  # lets the action's events reach the queue before the sentinel


def _until_sentinel(folder, results, timeout=TIMEOUT):
    """Write the sentinel and return every result up to and including it,
    plus any that arrives shortly after (which would mean the ordering
    assumption failed, so the sentinel must still be last)."""
    time.sleep(SETTLE)
    (folder / SENTINEL).write_bytes(_jpeg_bytes())
    got = []
    deadline = time.monotonic() + timeout
    while not got or os.path.basename(got[-1].img) != SENTINEL:
        got.append(_next_result(results, max(0.1, deadline - time.monotonic())))
    try:
        got.append(_next_result(results, 0.5))
    except queue.Empty:
        pass
    names = [os.path.basename(result.img) for result in got]
    assert names[-1] == SENTINEL, names
    return got


def _results_until_sentinel(folder, results, timeout=TIMEOUT):
    """File names of _until_sentinel()'s results."""
    return [os.path.basename(result.img)
            for result in _until_sentinel(folder, results, timeout)]


def _stop_watching(stop, thread):
    stop.set()
    thread.join(timeout=5)
    assert not thread.is_alive()


def test_watch_directory_survives_a_failing_callback(tmp_path):
    results = queue.Queue()
    calls = []

    def on_result(result):
        calls.append(result)
        if len(calls) == 1:
            raise RuntimeError("callback failed")
        results.put(result)

    # A thread killed by an uncaught exception reports it through
    # threading.excepthook: send it to the queue, so the test fails at once
    # with that exception instead of waiting for a result that never comes.
    # Set inside the test (not with monkeypatch) so pytest's own hook is
    # restored before pytest's call phase restores the original one.
    previous_hook = threading.excepthook
    threading.excepthook = lambda args: results.put(args.exc_value)
    try:
        _, stop, thread = _start_watching(tmp_path, on_result=on_result,
                                          results=results)
        try:
            time.sleep(1)
            (tmp_path / "first.jpg").write_bytes(_jpeg_bytes())
            time.sleep(SETTLE)
            deadline = time.monotonic() + TIMEOUT
            while not calls:
                assert time.monotonic() < deadline, "first.jpg never reported"
                assert thread.is_alive()
                time.sleep(0.05)
            (tmp_path / "second.jpg").write_bytes(_jpeg_bytes())
            result = _next_result(results)
            assert os.path.basename(result.img) == "second.jpg"
        finally:
            _stop_watching(stop, thread)
    finally:
        threading.excepthook = previous_hook


def test_watch_directory_picks_up_a_file_renamed_into_place(tmp_path):
    results, stop, thread = _start_watching(tmp_path)
    try:
        time.sleep(1)
        part = tmp_path / "atomic.jpg.part"
        part.write_bytes(_jpeg_bytes())
        os.replace(part, tmp_path / "atomic.jpg")
        names = _results_until_sentinel(tmp_path, results)
        assert names.count("atomic.jpg") == 1, names
    finally:
        _stop_watching(stop, thread)


def test_watch_directory_processes_a_file_moved_in_once(tmp_path):
    # A file moved in from outside the watched folder is processed exactly
    # once (guards the on_moved handling against double processing).
    watched = tmp_path / "watched"
    outside = tmp_path / "outside"
    watched.mkdir()
    outside.mkdir()
    results, stop, thread = _start_watching(watched)
    try:
        time.sleep(1)
        (outside / "moved.jpg").write_bytes(_jpeg_bytes())
        os.replace(outside / "moved.jpg", watched / "moved.jpg")
        names = _results_until_sentinel(watched, results)
        assert names.count("moved.jpg") == 1, names
    finally:
        _stop_watching(stop, thread)


def test_watch_directory_does_not_reprocess_a_renamed_file(tmp_path):
    # Renaming a file the watcher already optimized is not a new file.
    results, stop, thread = _start_watching(tmp_path)
    try:
        time.sleep(1)
        (tmp_path / "before.jpg").write_bytes(_jpeg_bytes())
        assert os.path.basename(_next_result(results).img) == "before.jpg"
        os.replace(tmp_path / "before.jpg", tmp_path / "after.jpg")
        names = _results_until_sentinel(tmp_path, results)
        assert names == [SENTINEL]
    finally:
        _stop_watching(stop, thread)


@pytest.mark.filterwarnings(
    "ignore::pytest.PytestUnhandledThreadExceptionWarning")
def test_watch_directory_raises_when_the_observer_dies(tmp_path, monkeypatch):
    # If watchdog's observer thread dies, watch_directory raises instead of
    # waiting forever for events that will never come.
    import watchdog.observers
    from optimize_images.exceptions import OIWatchStoppedError

    class DyingObserver(watchdog.observers.Observer):
        def dispatch_events(self, event_queue):
            raise RuntimeError("observer died")

    monkeypatch.setattr(watchdog.observers, "Observer", DyingObserver)
    results, stop, thread = _start_watching(tmp_path)
    try:
        with pytest.raises(OIWatchStoppedError):
            _next_result(results)
    finally:
        _stop_watching(stop, thread)


def test_watch_directory_processes_a_recreated_file(tmp_path):
    results, stop, thread = _start_watching(tmp_path)
    try:
        time.sleep(1)
        path = tmp_path / "same.jpg"
        path.write_bytes(_jpeg_bytes())
        assert os.path.basename(_next_result(results).img) == "same.jpg"
        path.unlink()
        time.sleep(SETTLE)
        path.write_bytes(_jpeg_bytes((330, 250)))
        names = _results_until_sentinel(tmp_path, results)
        assert names.count("same.jpg") == 1, names
    finally:
        _stop_watching(stop, thread)


def test_watch_directory_does_not_reprocess_its_own_output(tmp_path):
    results, stop, thread = _start_watching(tmp_path, convert_all=True)
    try:
        time.sleep(1)
        (tmp_path / "pic.png").write_bytes(_png_bytes())
        first = _next_result(results)
        assert os.path.basename(first.img) == "pic.png"
        assert first.was_optimized
        assert (tmp_path / "pic.jpg").is_file()
        names = _results_until_sentinel(tmp_path, results)
        assert names == [SENTINEL]
    finally:
        _stop_watching(stop, thread)


def test_watch_directory_waits_for_a_slow_write(tmp_path):
    results, stop, thread = _start_watching(tmp_path)
    try:
        time.sleep(1)
        data = _jpeg_bytes((640, 480))
        # About 3 s of writing with 100 ms pauses: the notification surely
        # arrives mid-write, and a pause is still far shorter than any
        # reasonable "the write is over" window.
        chunks = 30
        step = len(data) // chunks + 1
        with open(tmp_path / "slow.jpg", "wb") as file:
            for start in range(0, len(data), step):
                file.write(data[start:start + step])
                file.flush()
                time.sleep(0.1)
        result = _next_result(results)
        assert os.path.basename(result.img) == "slow.jpg"
        assert result.was_optimized
    finally:
        _stop_watching(stop, thread)


def test_watch_directory_keeps_a_users_file_named_like_a_conversion(tmp_path):
    # With -cb a small PNG is optimized in place, not converted: a JPEG of the
    # user's with the same base name is not the conversion's output, and is
    # processed too.
    results, stop, thread = _start_watching(tmp_path, conv_big=True)
    try:
        time.sleep(1)
        (tmp_path / "pic.png").write_bytes(_png_bytes((64, 48)))
        (tmp_path / "pic.jpg").write_bytes(_jpeg_bytes())
        names = _results_until_sentinel(tmp_path, results)
        assert names.count("pic.png") == 1, names
        assert names.count("pic.jpg") == 1, names
    finally:
        _stop_watching(stop, thread)


class _SkewedTime:
    """Stands in for the time module in optimize_images.api: the local clock
    runs ahead of the file system's, so new files look older than they are
    (a share whose clock is behind ours)."""

    # Before "def time" below, which shadows the module in the class body.
    monotonic = staticmethod(time.monotonic)
    sleep = staticmethod(time.sleep)
    _real_time = staticmethod(time.time)

    def __init__(self, skew):
        self.skew = skew

    def time(self):
        return self._real_time() + self.skew


def _write_slowly(path, data, chunks=30, pause=0.1):
    step = len(data) // chunks + 1
    with open(path, "wb") as file:
        for start in range(0, len(data), step):
            file.write(data[start:start + step])
            file.flush()
            time.sleep(pause)


def test_watch_directory_waits_for_a_slow_write_with_a_skewed_clock(
        tmp_path, monkeypatch):
    # A file whose mtime looks 2 s old while it is still being written must
    # still be waited for: before the watcher learnt the clock difference
    # from a file it wrote, and after.
    import optimize_images.api as api
    monkeypatch.setattr(api, "time", _SkewedTime(2.0))
    results, stop, thread = _start_watching(tmp_path)
    try:
        time.sleep(1)
        _write_slowly(tmp_path / "slow1.jpg", _jpeg_bytes((640, 480)))
        first = _next_result(results)
        assert os.path.basename(first.img) == "slow1.jpg"
        assert first.was_optimized

        (tmp_path / "quick.jpg").write_bytes(_jpeg_bytes())
        assert _next_result(results).was_optimized  # clock difference learnt

        _write_slowly(tmp_path / "slow2.jpg", _jpeg_bytes((640, 480)))
        second = _next_result(results)
        assert os.path.basename(second.img) == "slow2.jpg"
        assert second.was_optimized
    finally:
        _stop_watching(stop, thread)


@pytest.mark.xfail(strict=True, reason=(
    "known limitation: a writer pausing longer than the 0.5 s write-finish "
    "window gets the file read half-written, and it is not retried because "
    "modified events are not handled"))
def test_watch_directory_retries_a_file_after_a_long_pause(tmp_path):
    results, stop, thread = _start_watching(tmp_path)
    try:
        time.sleep(1)
        data = _jpeg_bytes((640, 480))
        with open(tmp_path / "paused.jpg", "wb") as file:
            file.write(data[:len(data) // 2])
            file.flush()
            time.sleep(1.0)
            file.write(data[len(data) // 2:])
        got = _until_sentinel(tmp_path, results)
        assert any(os.path.basename(r.img) == "paused.jpg" and r.was_optimized
                   for r in got), got
    finally:
        _stop_watching(stop, thread)


def test_watch_directory_does_not_wait_per_file_when_nothing_shrinks(tmp_path):
    # Files that cannot shrink are not rewritten, so the watcher never learns
    # the file system's clock from its own writes. A burst of them must still
    # not pay the 0.5 s write-finish window once per file (the clock is
    # measured with a probe file at start).
    import contextlib
    from optimize_images.api import optimize_as_batch

    prepared = tmp_path / "prepared"
    watched = tmp_path / "watched"
    prepared.mkdir()
    watched.mkdir()
    size = (400, 300)
    for index in range(5):
        img = Image.merge("RGB", (
            Image.linear_gradient("L").resize(size),
            Image.linear_gradient("L").rotate(90).resize(size),
            Image.effect_noise(size, 20 + index)))
        img.save(prepared / f"done_{index}.jpg", "JPEG", quality=95)
    with contextlib.redirect_stdout(io.StringIO()):
        for _ in range(2):  # after two passes there is nothing left to gain
            optimize_as_batch(PublicBatchOptions(src_path=str(prepared)))
    files = sorted(prepared.iterdir())

    results, stop, thread = _start_watching(watched)
    try:
        time.sleep(1)
        for path in files:
            (watched / path.name).write_bytes(path.read_bytes())
        # The per-file wait would cost at least 2.5 s; notification lag is
        # about 0.1 s, so 2 s leaves room for a loaded machine.
        deadline = time.monotonic() + 2.0
        got = [_next_result(results, max(0.1, deadline - time.monotonic()))
               for _ in files]
        assert sorted(os.path.basename(r.img) for r in got) == \
            [path.name for path in files]
        assert not any(r.was_optimized for r in got)
    finally:
        _stop_watching(stop, thread)
