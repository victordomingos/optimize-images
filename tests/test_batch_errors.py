#!/usr/bin/env python3
"""A file that cannot be processed must not abort the batch (plan 1.10).

Running out of memory (MemoryError) or an image above Pillow's pixel limit
(DecompressionBombError) is not an OSError, so today the exception reaches the
batch loop: the CLI prints a traceback, exits with code 1 and shows no summary
(seen on Windows with -jobs 16 and SSIM). The file must instead be reported as
skipped, with its original kept and the reason in the result, and the run must
end normally with a hint to lower -jobs when memory ran out.

Self-contained: every image is generated under pytest's ``tmp_path``.
"""
import os

import pytest
from PIL import Image

from helpers import run_cli
from optimize_images import do_optimization as dispatch
from optimize_images.api import PublicTaskResult
from optimize_images.data_structures import OutputConfiguration, Task, \
    TaskResult
from optimize_images.img_ssim import ssim_available
from optimize_images.platforms import IconGenerator
from optimize_images.reporting import show_file_status, show_final_report

OUTPUT = OutputConfiguration(False, False, False)


def _jpeg(path, size=(320, 240)):
    width, height = size
    img = Image.new("RGB", size)
    img.frombytes(bytes(v for y in range(height) for x in range(width)
                        for v in ((x * 255) // width, (y * 255) // height,
                                  (x * y) % 256)))
    img.save(path, quality=95)
    return path


def _task(path, **fields):
    task = Task(str(path), None, False, False, 256, 0, 0, False, False, False,
                False, (255, 255, 255), False, False, False, OUTPUT)
    return task._replace(**fields)


def _raise_memory_error(*_args, **_kwargs):
    raise MemoryError


def test_memory_error_skips_the_file(tmp_path, monkeypatch):
    path = _jpeg(tmp_path / "photo.jpg")
    original = path.read_bytes()
    monkeypatch.setattr(dispatch, "optimize_jpg", _raise_memory_error)
    result = dispatch.do_optimization(_task(path))
    assert not result.was_optimized
    assert result.final_size == result.orig_size == len(original)
    assert result.error == "out_of_memory"
    assert path.read_bytes() == original


def test_memory_error_while_converting_skips_the_file(tmp_path, monkeypatch):
    path = _jpeg(tmp_path / "photo.jpg")
    original = path.read_bytes()
    monkeypatch.setattr(dispatch, "convert_image", _raise_memory_error)
    result = dispatch.do_optimization(
        _task(path, convert_all=True, convert_to="png"))
    assert not result.was_optimized
    assert result.error == "out_of_memory"
    assert path.read_bytes() == original
    assert sorted(p.name for p in tmp_path.iterdir()) == ["photo.jpg"]


def test_image_above_pixel_limit_skips_the_file(tmp_path, monkeypatch):
    # Pillow raises DecompressionBombError above twice MAX_IMAGE_PIXELS, when
    # the image is opened: a real error, not a mock.
    path = _jpeg(tmp_path / "photo.jpg")
    original = path.read_bytes()
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 1000)
    with pytest.raises(Image.DecompressionBombError):
        Image.open(path)
    result = dispatch.do_optimization(_task(path))
    assert not result.was_optimized
    assert result.error == "image_too_large"
    assert path.read_bytes() == original


@pytest.mark.parametrize("exception, error", [
    (MemoryError, "out_of_memory"),
    (Image.DecompressionBombError, "image_too_large"),
])
def test_failure_while_opening_skips_the_file(tmp_path, monkeypatch,
                                              exception, error):
    path = _jpeg(tmp_path / "photo.jpg")
    original = path.read_bytes()

    def failing_open(*_args, **_kwargs):
        raise exception

    monkeypatch.setattr(dispatch.Image, "open", failing_open)
    result = dispatch.do_optimization(_task(path))
    assert not result.was_optimized
    assert result.error == error
    assert result.final_size == result.orig_size == len(original)
    assert path.read_bytes() == original


def test_results_carry_the_error():
    from optimize_images.api import _to_public_result
    fields = dict(img="a.jpg", orig_format="JPEG", result_format="JPEG",
                  orig_mode="RGB", result_mode="RGB", orig_colors=0,
                  final_colors=0, orig_size=10, final_size=10,
                  was_optimized=False, was_downsized=False, had_exif=False,
                  has_exif=False)
    assert PublicTaskResult(**fields).error is None
    assert TaskResult(**fields, output_config=OUTPUT).error is None
    internal = TaskResult(**fields, output_config=OUTPUT,
                          error="out_of_memory")
    assert _to_public_result(internal).error == "out_of_memory"


@pytest.mark.parametrize("error, text", [
    ("out_of_memory", "Not enough memory"),
    ("image_too_large", "pixel limit"),
])
def test_file_status_shows_the_reason(capsys, error, text):
    result = PublicTaskResult(
        img="a.jpg", orig_format="JPEG", result_format="JPEG",
        orig_mode="RGB", result_mode="RGB", orig_colors=0, final_colors=0,
        orig_size=10, final_size=10, was_optimized=False,
        was_downsized=False, had_exif=False, has_exif=False, error=error)
    show_file_status(result, 100, IconGenerator())
    out = capsys.readouterr().out
    assert "SKIPPED" in out and text in out
    assert "original was kept" in out


def test_final_report_suggests_lower_jobs(capsys):
    show_final_report(2, 1, 100, 10, 1.0, OUTPUT, memory_errors=1)
    out = capsys.readouterr().out
    assert "memory" in out and "-jobs" in out


def test_final_report_without_memory_errors_has_no_hint(capsys):
    show_final_report(2, 1, 100, 10, 1.0, OUTPUT)
    assert "-jobs" not in capsys.readouterr().out


def test_cli_finishes_when_one_file_is_too_large(tmp_path):
    # A sitecustomize on PYTHONPATH lowers Pillow's pixel limit in the CLI
    # process (and in any worker process it starts), so the big image raises
    # DecompressionBombError while the small one is optimized normally. The
    # limit stays above the 400x400 image the automatic JPEG quality search
    # encodes and reopens (160 000 pixels, no warning below the limit).
    hooks = tmp_path / "hooks"
    hooks.mkdir()
    (hooks / "sitecustomize.py").write_text(
        "import PIL.Image\nPIL.Image.MAX_IMAGE_PIXELS = 200_000\n")
    images = tmp_path / "images"
    images.mkdir()
    _jpeg(images / "small.jpg", size=(320, 240))
    _jpeg(images / "big.jpg", size=(800, 600))  # 480 000 > 2 x limit
    env = {**os.environ, "PYTHONPATH": str(hooks),
           "PYTHONWARNINGS": "error::DeprecationWarning"}
    proc = run_cli(images, env=env)
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert "Traceback" not in proc.stderr
    assert "Optimized 1 files" in proc.stdout
    assert "pixel limit" in proc.stdout


@pytest.mark.skipif(not ssim_available(), reason="scikit-image not installed")
def test_cli_reports_ssim_out_of_memory(tmp_path):
    # The user's case on Windows: many jobs with -ssm on big images. A
    # sitecustomize on PYTHONPATH makes the SSIM backend raise MemoryError
    # (it is imported before optimize_images binds structural_similarity).
    hooks = tmp_path / "hooks"
    hooks.mkdir()
    (hooks / "sitecustomize.py").write_text(
        "import skimage.metrics\n"
        "def _out_of_memory(*args, **kwargs):\n"
        "    raise MemoryError\n"
        "skimage.metrics.structural_similarity = _out_of_memory\n")
    images = tmp_path / "images"
    images.mkdir()
    _jpeg(images / "a.jpg")
    _jpeg(images / "b.jpg", size=(240, 320))
    before = {p.name: p.read_bytes() for p in images.iterdir()}
    env = {**os.environ, "PYTHONPATH": str(hooks),
           "PYTHONWARNINGS": "error::DeprecationWarning"}
    proc = run_cli("-ssm", "0.9", images, env=env)
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert "Traceback" not in proc.stderr
    assert proc.stdout.count("Not enough memory") == 2
    assert "-jobs" in proc.stdout
    assert {p.name: p.read_bytes() for p in images.iterdir()} == before


def test_unreadable_file_keeps_its_size_and_the_batch_goes_on(tmp_path):
    # Plan 0.6: a corrupt file next to a valid one. The batch finishes, the
    # valid file is optimized and the corrupt one is reported as skipped,
    # with its real size (it counts in the processed total) and no error.
    from optimize_images.api import PublicBatchOptions, optimize_as_batch
    _jpeg(tmp_path / "good.jpg")
    broken = tmp_path / "broken.jpg"
    broken.write_bytes(b"\xff\xd8\xff\xe0 not really a jpeg" * 20)
    result = optimize_as_batch(PublicBatchOptions(src_path=str(tmp_path),
                                                  recursive=False, jobs=1))
    by_name = {os.path.basename(r.img): r for r in result.results}
    assert by_name["good.jpg"].was_optimized
    bad = by_name["broken.jpg"]
    assert not bad.was_optimized and bad.error is None
    assert bad.orig_size == broken.stat().st_size
    assert broken.read_bytes() == b"\xff\xd8\xff\xe0 not really a jpeg" * 20
