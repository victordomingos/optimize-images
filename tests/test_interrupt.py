"""Ctrl-C and early stop: no traceback, no damaged file, queued files untouched.

A terminal Ctrl-C reaches the whole process group, so the CLI is started in its
own session and the signal is sent to the group with os.killpg (signalling the
child alone would never reach pool workers). The signal is sent when the CLI's
own output shows how far it got, not after a fixed delay. POSIX only.
"""
import os
import signal
import subprocess
import sys

import pytest
from PIL import Image

from helpers import REPO_ROOT, _cli_env, cli_command
from optimize_images.api import PublicBatchOptions, optimize_as_batch_stream

pytestmark = pytest.mark.skipif(os.name != 'posix', reason='POSIX signals')

# Runs the CLI with the executor forced to a process pool (the Linux default for
# regular Python builds), so the process-pool path is tested on every POSIX OS.
PROCESS_POOL_DRIVER = """\
import os, runpy, sys
from concurrent.futures import ProcessPoolExecutor

def main():
    sys.path.insert(0, os.getcwd())   # the repository root (cwd), as with -m
    from optimize_images import platforms
    platforms.select_executor = lambda ft, os_name, system, n: (ProcessPoolExecutor, n)
    sys.argv = ['optimize-images', *sys.argv[1:]]
    runpy.run_module('optimize_images', run_name='__main__')

if __name__ == '__main__':
    main()
"""


def _noise_jpegs(folder, count=16, size=(1200, 900)):
    """JPEGs of random noise: slow enough to encode that a batch lasts a while."""
    folder.mkdir()
    for i in range(count):
        Image.frombytes('RGB', size, os.urandom(size[0] * size[1] * 3)).save(
            folder / f'noise{i:02}.jpg', quality=95)
    return {p: p.read_bytes() for p in folder.iterdir()}


def _start(command):
    # Unbuffered, so each per-file line arrives as soon as it is printed.
    env = {**_cli_env(), 'PYTHONUNBUFFERED': '1'}
    return subprocess.Popen(command, cwd=REPO_ROOT, env=env, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            start_new_session=True)


def _interrupt_when(proc, marker):
    """Send Ctrl-C to the process group once a stdout line contains marker."""
    lines = []
    for line in proc.stdout:
        lines.append(line)
        if marker in line:
            os.killpg(proc.pid, signal.SIGINT)
            break
    # Read the rest from the same file objects: communicate() would bypass
    # the text already buffered by the line iteration above.
    out, err = proc.stdout.read(), proc.stderr.read()
    proc.wait(timeout=120)
    return ''.join(lines) + out, err


def _assert_clean_stop(before, out, err):
    assert 'Traceback' not in err, err[-2000:]
    assert 'interrupted by the user' in out
    for path in before:
        with Image.open(path) as img:   # nothing truncated or half-written
            img.load()
    untouched = sum(path.read_bytes() == data for path, data in before.items())
    assert untouched >= 1   # queued files were cancelled, not processed


def test_ctrl_c_stops_a_threaded_batch_cleanly(tmp_path):
    before = _noise_jpegs(tmp_path / 'images')
    proc = _start(cli_command(tmp_path / 'images', '-jobs', '2'))
    out, err = _interrupt_when(proc, 'noise')
    _assert_clean_stop(before, out, err)


def test_ctrl_c_stops_a_process_pool_batch_cleanly(tmp_path):
    driver = tmp_path / 'driver.py'
    driver.write_text(PROCESS_POOL_DRIVER)
    before = _noise_jpegs(tmp_path / 'images')
    proc = _start([sys.executable, str(driver), str(tmp_path / 'images'), '-jobs', '2'])
    out, err = _interrupt_when(proc, 'noise')
    _assert_clean_stop(before, out, err)


def test_early_ctrl_c_does_not_kill_starting_workers(tmp_path):
    # Right after the start header the workers are still being started; a
    # Ctrl-C that killed one there used to break the pool and stop its siblings
    # in the middle of writing an image (a 0-byte file instead of the original).
    driver = tmp_path / 'driver.py'
    driver.write_text(PROCESS_POOL_DRIVER)
    before = _noise_jpegs(tmp_path / 'images', count=12, size=(800, 600))
    proc = _start([sys.executable, str(driver), str(tmp_path / 'images'), '-jobs', '4'])
    out, err = _interrupt_when(proc, 'Recursively searching')
    assert 'Traceback' not in err, err[-2000:]
    for path in before:
        with Image.open(path) as img:
            img.load()


def test_closing_the_stream_early_cancels_queued_files(tmp_path):
    before = _noise_jpegs(tmp_path / 'images', count=10, size=(600, 450))
    stream = optimize_as_batch_stream(
        PublicBatchOptions(src_path=str(tmp_path / 'images'), jobs=1))
    next(stream)
    stream.close()   # the caller stops reading: files not started are dropped
    untouched = sum(path.read_bytes() == data for path, data in before.items())
    assert untouched >= len(before) - 2   # one done, at most one in progress
