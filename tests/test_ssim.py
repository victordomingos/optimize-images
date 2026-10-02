#!/usr/bin/env python3
"""Behavioral tests for SSIM quality control (optional scikit-image backend).

Self-contained: images are generated under pytest's ``tmp_path``. Tests that
need a real score skip themselves when scikit-image is not installed; the
missing-backend behavior tests run everywhere by faking the backend flag.
"""
import io
import os
import subprocess
import sys
import warnings

import pytest
from PIL import Image
from types import SimpleNamespace

from optimize_images import img_ssim
from optimize_images.api import PublicBatchOptions, convert_image_data, \
    optimize_as_batch, optimize_image_data, optimize_single_image
from optimize_images.data_structures import OutputConfiguration
from optimize_images.exceptions import OISSIMNotAvailableError
from optimize_images.img_aux_processing import is_worth_keeping
from optimize_images.img_ssim import compute_ssim, ssim_available
from optimize_images.platforms import IconGenerator
from optimize_images.reporting import show_file_status

requires_backend = pytest.mark.skipif(
    not ssim_available(), reason="scikit-image not installed")


def _photo(path, fmt='JPEG', size=(320, 240), **save):
    rows = []
    for y in range(size[1]):
        for x in range(size[0]):
            rows.extend(((x * 2) % 256, (y * 3) % 256, (x * y) % 256))
    img = Image.frombytes('RGB', size, bytes(rows))
    img.save(path, fmt, **save)
    return path


def test_compute_ssim_identical():
    if not ssim_available():
        pytest.skip("scikit-image not installed")
    img = Image.new('RGB', (32, 32), (120, 60, 30))
    assert compute_ssim(img, img.copy()) == pytest.approx(1.0)


def test_compute_ssim_size_mismatch():
    a = Image.new('RGB', (10, 10), (120, 60, 30))
    b = Image.new('RGB', (12, 10), (120, 60, 30))
    assert compute_ssim(a, b) is None


def test_compute_ssim_backend_missing(monkeypatch):
    monkeypatch.setattr(img_ssim, "_HAS_SKIMAGE", False)
    img = Image.new('RGB', (10, 10), (120, 60, 30))
    assert compute_ssim(img, img.copy()) is None


def test_ensure_raises_when_backend_missing(monkeypatch):
    monkeypatch.setattr(img_ssim, "_HAS_SKIMAGE", False)
    with pytest.raises(OISSIMNotAvailableError):
        img_ssim.ensure_ssim_available()


def test_is_worth_keeping_ssim_gate():
    assert is_worth_keeping(50, 100, True, ssim_min=0.5, ssim=None) is False
    assert is_worth_keeping(50, 100, True, ssim_min=0.5, ssim=0.4) is False
    assert is_worth_keeping(50, 100, True, ssim_min=0.5, ssim=0.9) is True
    assert is_worth_keeping(150, 100, False, ssim_min=0.5, ssim=None) is False
    assert is_worth_keeping(150, 100, False, ssim_min=0.5, ssim=0.9) is True
    assert is_worth_keeping(50, 100, True) is True


@requires_backend
def test_single_image_gate_rejects_low_score(tmp_path):
    # fast_mode pins the encoder quality (dynamic quality would pick a
    # high score), so quality=10 produces a visibly degraded encoding.
    path = _photo(tmp_path / "img.jpg")
    before = path.read_bytes()
    result = optimize_single_image(str(path), fast_mode=True, quality=10,
                                   ssim_min=0.9)
    assert result.ssim is not None and result.ssim < 0.9
    assert not result.was_optimized
    assert path.read_bytes() == before


@requires_backend
def test_single_image_gate_keeps_high_score(tmp_path):
    path = _photo(tmp_path / "img.jpg")
    result = optimize_single_image(str(path), fast_mode=True, quality=10,
                                   ssim_min=0.3)
    assert result.ssim is not None and result.ssim >= 0.3
    assert result.was_optimized


@requires_backend
def test_single_image_show_ssim_without_threshold(tmp_path):
    path = _photo(tmp_path / "img.jpg")
    result = optimize_single_image(str(path), fast_mode=True, quality=50,
                                   show_ssim=True)
    assert result.ssim is not None
    assert result.was_optimized


def test_single_image_missing_backend_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(img_ssim, "_HAS_SKIMAGE", False)
    path = _photo(tmp_path / "img.jpg")
    with pytest.raises(OISSIMNotAvailableError):
        optimize_single_image(str(path), ssim_min=0.9)


def test_bytes_api_missing_backend_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(img_ssim, "_HAS_SKIMAGE", False)
    data = _photo(tmp_path / "img.jpg").read_bytes()
    with pytest.raises(OISSIMNotAvailableError):
        optimize_image_data(data, ssim_min=0.9)
    with pytest.raises(OISSIMNotAvailableError):
        convert_image_data(data, to='webp', ssim_min=0.9)


def test_batch_api_missing_backend_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(img_ssim, "_HAS_SKIMAGE", False)
    _photo(tmp_path / "img.jpg")
    with pytest.raises(OISSIMNotAvailableError):
        optimize_as_batch(PublicBatchOptions(
            src_path=str(tmp_path), ssim_min=0.9))


def test_bytes_api_show_ssim_missing_backend_ok(tmp_path, monkeypatch):
    monkeypatch.setattr(img_ssim, "_HAS_SKIMAGE", False)
    data = _photo(tmp_path / "img.jpg").read_bytes()
    out, result = optimize_image_data(data, show_ssim=True)
    assert result.ssim is None
    assert out


@requires_backend
def test_bytes_api_gate_rejects(tmp_path):
    data = _photo(tmp_path / "img.jpg").read_bytes()
    out, result = optimize_image_data(data, fast_mode=True, quality=10,
                                      ssim_min=0.9)
    assert out == data
    assert not result.was_optimized
    assert result.ssim is not None and result.ssim < 0.9


@requires_backend
def test_bytes_api_convert_reports_score(tmp_path):
    data = _photo(tmp_path / "img.png").read_bytes()
    out, result = convert_image_data(data, to='jpeg', ssim_min=0.1)
    assert result.ssim is not None and result.ssim >= 0.1
    assert result.was_optimized
    assert out != data


@requires_backend
def test_bytes_api_convert_gate_rejects(tmp_path):
    data = _photo(tmp_path / "img.png", 'PNG').read_bytes()
    out, result = convert_image_data(data, to='webp', webp_quality=1,
                                     ignore_size_comparison=True,
                                     ssim_min=0.99)
    assert result.ssim is not None and result.ssim < 0.99
    assert not result.was_optimized
    assert out == data
    assert result.result_format == 'PNG'


@requires_backend
def test_single_image_convert_gate_rejects(tmp_path):
    path = _photo(tmp_path / "img.png", 'PNG')
    before = path.read_bytes()
    result = optimize_single_image(str(path), convert_all=True,
                                   convert_to='webp', webp_quality=1,
                                   ignore_size_comparison=True,
                                   ssim_min=0.99)
    assert result.ssim is not None and result.ssim < 0.99
    assert not result.was_optimized
    assert path.read_bytes() == before
    assert not (tmp_path / "img.webp").exists()


@requires_backend
def test_single_image_convert_gate_keeps(tmp_path):
    path = _photo(tmp_path / "img.png", 'PNG')
    result = optimize_single_image(str(path), convert_all=True,
                                   convert_to='webp',
                                   ignore_size_comparison=True,
                                   ssim_min=0.1)
    assert result.ssim is not None and result.ssim >= 0.1
    assert result.was_optimized
    assert (tmp_path / "img.webp").exists()


@requires_backend
def test_gate_applies_without_size_comparison(tmp_path):
    # -nc disables only the size rule; the SSIM threshold still applies.
    path = _photo(tmp_path / "img.jpg")
    before = path.read_bytes()
    result = optimize_single_image(str(path), fast_mode=True, quality=10,
                                   ignore_size_comparison=True, ssim_min=0.9)
    assert result.ssim is not None and result.ssim < 0.9
    assert not result.was_optimized
    assert path.read_bytes() == before

    out, result = optimize_image_data(before, fast_mode=True, quality=10,
                                      ignore_size_comparison=True,
                                      ssim_min=0.9)
    assert not result.was_optimized
    assert out == before


@requires_backend
def test_gate_keeps_original_when_score_fails(tmp_path, monkeypatch):
    # A MemoryError inside the SSIM backend (large image, many workers) must
    # yield no score, and the gate must then keep the original (fail closed).
    def _out_of_memory(*_args, **_kwargs):
        raise MemoryError
    monkeypatch.setattr(img_ssim, "_ssim_impl", _out_of_memory)

    img = Image.new('RGB', (32, 32), (120, 60, 30))
    img2 = img.copy()
    img2.putpixel((0, 0), (121, 60, 30))
    assert compute_ssim(img, img2) is None

    path = _photo(tmp_path / "img.jpg")
    before = path.read_bytes()
    result = optimize_single_image(str(path), fast_mode=True, quality=50,
                                   ignore_size_comparison=True, ssim_min=0.5)
    assert result.ssim is None
    assert not result.was_optimized
    assert path.read_bytes() == before

    out, result = optimize_image_data(before, fast_mode=True, quality=50,
                                      ignore_size_comparison=True,
                                      ssim_min=0.5)
    assert result.ssim is None
    assert not result.was_optimized
    assert out == before


@requires_backend
@pytest.mark.parametrize("ssim_min", [-0.1, 1.01, 95, float('nan')])
def test_api_rejects_out_of_range_threshold(tmp_path, ssim_min):
    path = _photo(tmp_path / "img.jpg")
    data = path.read_bytes()
    with pytest.raises(ValueError):
        optimize_single_image(str(path), ssim_min=ssim_min)
    with pytest.raises(ValueError):
        optimize_image_data(data, ssim_min=ssim_min)
    with pytest.raises(ValueError):
        convert_image_data(data, to='webp', ssim_min=ssim_min)
    with pytest.raises(ValueError):
        optimize_as_batch(PublicBatchOptions(src_path=str(tmp_path),
                                             ssim_min=ssim_min))
    assert path.read_bytes() == data


@requires_backend
@pytest.mark.parametrize("ssim_min", [0.0, 1.0])
def test_api_accepts_threshold_bounds(tmp_path, ssim_min):
    data = _photo(tmp_path / "img.jpg").read_bytes()
    _, result = optimize_image_data(data, ssim_min=ssim_min)
    assert result.ssim is not None


def _logo_rgba(size=(200, 200)):
    """Opaque disc on a fully transparent background whose hidden RGB is
    arbitrary noise, as many editors export it. The WebP encoder discards
    that invisible RGB (exact=False), so it must not affect the score."""
    w, h = size
    rgba = []
    for y in range(h):
        for x in range(w):
            if (x - w // 2) ** 2 + (y - h // 2) ** 2 < (w // 3) ** 2:
                rgba.extend((200, 30, 30, 255))
            else:
                rgba.extend(((x * 37 + y * 11) % 256, (y * 91) % 256,
                             (x * y * 7) % 256, 0))
    return Image.frombytes('RGBA', size, bytes(rgba))


@requires_backend
@pytest.mark.parametrize("webp_lossless", [False, True])
def test_webp_alpha_hidden_rgb_does_not_lower_score(tmp_path, webp_lossless):
    path = tmp_path / "logo.webp"
    _logo_rgba().save(path, 'WEBP', lossless=True, exact=True)
    _, result = optimize_image_data(path.read_bytes(),
                                    webp_lossless=webp_lossless,
                                    ignore_size_comparison=True,
                                    ssim_min=0.95)
    assert result.ssim is not None and result.ssim >= 0.99
    assert result.was_optimized


@requires_backend
def test_convert_rgba_to_webp_hidden_rgb_does_not_lower_score(tmp_path):
    path = tmp_path / "logo.png"
    _logo_rgba().save(path, 'PNG')
    _, result = convert_image_data(path.read_bytes(), to='webp',
                                   ignore_size_comparison=True,
                                   ssim_min=0.95)
    assert result.ssim is not None and result.ssim >= 0.99
    assert result.was_optimized


@requires_backend
def test_convert_palette_transparency_no_pil_warning(tmp_path):
    # A palette PNG with tRNS transparency must be compared without Pillow's
    # "Palette images with Transparency expressed in bytes" UserWarning.
    img = Image.new('P', (64, 64))
    img.putpalette([i % 256 for i in range(768)])
    img.putdata([(x + y) % 256 for y in range(64) for x in range(64)])
    path = tmp_path / "palette.png"
    img.save(path, 'PNG', transparency=bytes([0] * 10 + [255] * 246))
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        _, result = convert_image_data(path.read_bytes(), to='webp',
                                       ignore_size_comparison=True,
                                       show_ssim=True)
    assert result.ssim is not None
    assert not [w for w in caught if issubclass(w.category, UserWarning)
                and 'Palette images with Transparency' in str(w.message)]


def _status_result(was_optimized, ssim, orig_size=1000, final_size=800):
    return SimpleNamespace(
        img='img.jpg', was_optimized=was_optimized, was_downsized=False,
        orig_size=orig_size, final_size=final_size, orig_format='JPEG',
        result_format='JPEG', orig_mode='RGB', result_mode='RGB',
        orig_colors=0, final_colors=0, had_exif=False, has_exif=False,
        ssim=ssim)


def test_report_optimized_shows_ssim(capsys):
    show_file_status(_status_result(True, 0.9712), 0, IconGenerator(),
                     show_ssim=True)
    out = capsys.readouterr().out
    assert 'SSIM: 0.9712' in out


def test_report_optimized_hides_ssim_without_flag(capsys):
    show_file_status(_status_result(True, 0.9712), 0, IconGenerator())
    out = capsys.readouterr().out
    assert 'SSIM' not in out


def test_report_skipped_below_threshold_flagged(capsys):
    show_file_status(_status_result(False, 0.8534), 0, IconGenerator(),
                     show_ssim=True, ssim_min=0.9)
    out = capsys.readouterr().out
    assert '0.8534' in out
    assert 'below threshold' in out


def test_report_skipped_not_smaller_silent(capsys):
    # A size skip with a good score must not look like an SSIM rejection.
    show_file_status(
        _status_result(False, 0.9712, orig_size=1000, final_size=1100), 0,
        IconGenerator(), show_ssim=True, ssim_min=0.9)
    out = capsys.readouterr().out
    assert 'SSIM' not in out


def test_report_skipped_show_only_silent(capsys):
    show_file_status(_status_result(False, 0.9712), 0, IconGenerator(),
                     show_ssim=True)
    out = capsys.readouterr().out
    assert 'SSIM' not in out


def test_report_skipped_no_ssim_silent(capsys):
    show_file_status(_status_result(False, None), 0, IconGenerator(),
                     show_ssim=True, ssim_min=0.9)
    out = capsys.readouterr().out
    assert 'SSIM' not in out


def test_cli_warns_show_ssim_without_backend(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(img_ssim, "_HAS_SKIMAGE", False)
    _photo(tmp_path / "img.jpg")
    from optimize_images.__main__ import optimize_batch
    optimize_batch(
        src_path=str(tmp_path), watch_dir=False, recursive=True, quality=80,
        remove_transparency=False, reduce_colors=False, max_colors=256,
        max_w=0, max_h=0, keep_exif=False, convert_all=False, conv_big=False,
        force_del=False, bg_color=(255, 255, 255), grayscale=False,
        ignore_size_comparison=False, fast_mode=True, jobs=1,
        output_config=OutputConfiguration(False, False, False),
        ssim_min=None, show_ssim=True)
    err = capsys.readouterr().err
    assert 'scikit-image' in err
    assert '--show-ssim' in err


# --- Plan F1 bugs (fixed: the strict xfail markers were removed). ---

def _multi_frame(fmt, size=(64, 48)):
    frames = [Image.new('RGB', size, c)
              for c in ((200, 30, 30), (30, 200, 30), (30, 30, 200))]
    if fmt == 'MPO':
        frames = frames[:2]
    buf = io.BytesIO()
    frames[0].save(buf, format=fmt, save_all=True, append_images=frames[1:])
    return buf.getvalue()


@requires_backend
def test_multi_frame_image_is_left_untouched():
    data = _multi_frame('PNG')
    with Image.open(io.BytesIO(data)) as img:
        assert img.n_frames > 1
    out, result = optimize_image_data(data, ssim_min=0.99,
                                      ignore_size_comparison=True)
    assert out == data
    assert result.was_optimized is False


@requires_backend
def test_multi_frame_file_is_left_untouched(tmp_path):
    path = tmp_path / "anim.png"
    path.write_bytes(_multi_frame('PNG'))
    before = path.read_bytes()
    result = optimize_single_image(str(path), ssim_min=0.99)
    assert result.was_optimized is False
    assert path.read_bytes() == before


@requires_backend
def test_mpo_is_optimized_as_its_primary_image():
    # Camera JPEGs often open as MPO (primary image + embedded preview).
    # They are deliberately optimized as JPEG: the output keeps the primary
    # image only, and the score measures that image. Plan 1.1 must not
    # start skipping them.
    import numpy as np
    from skimage.metrics import structural_similarity
    data = _multi_frame('MPO')
    out, result = optimize_image_data(data, ignore_size_comparison=True,
                                      show_ssim=True)
    assert result.was_optimized
    with Image.open(io.BytesIO(data)) as src:
        primary = np.asarray(src.convert('RGB'), dtype=np.float64)
    with Image.open(io.BytesIO(out)) as img:
        assert getattr(img, 'n_frames', 1) == 1
        got = np.asarray(img.convert('RGB'), dtype=np.float64)
    expected = structural_similarity(
        primary, got, data_range=255, channel_axis=-1, win_size=7,
        gaussian_weights=False, use_sample_covariance=True)
    assert result.ssim == pytest.approx(expected, abs=1e-4)


def _png16_gradient(size=(256, 64)):
    import numpy as np
    width, height = size
    values = (np.arange(width * height, dtype=np.uint32) * 65535
              // (width * height - 1)).astype('<u2')
    img = Image.frombytes('I;16', size, values.tobytes())
    buf = io.BytesIO()
    img.save(buf, 'PNG')
    return buf.getvalue(), (values >> 8).astype(np.uint8).reshape(height,
                                                                  width)


@requires_backend
@pytest.mark.parametrize("target", ['jpeg', 'webp'])
def test_convert_16bit_png_scales_samples(target):
    import numpy as np
    from skimage.metrics import structural_similarity
    data, expected = _png16_gradient()
    out, result = convert_image_data(data, to=target, show_ssim=True,
                                     ignore_size_comparison=True)
    with Image.open(io.BytesIO(out)) as img:
        got = np.asarray(img.convert('L'))
    # Correct 8-bit rendition of the gradient: mean ~127, not almost white.
    assert abs(float(got.mean()) - float(expected.mean())) < 10
    # The reported score must reflect the loss against the real image.
    true_score = structural_similarity(
        expected.astype(np.float64), got.astype(np.float64), win_size=7,
        gaussian_weights=False, use_sample_covariance=True, data_range=255)
    assert result.ssim == pytest.approx(true_score, abs=0.02)



def _gray16(mode):
    import numpy as np
    values = (np.arange(256 * 4, dtype=np.uint32) * 64).reshape(4, 256)
    if mode == 'I':
        img = Image.fromarray(values.astype(np.int32))
    else:
        dtype = '>u2' if mode == 'I;16B' else '<u2'
        img = Image.frombytes(mode, (256, 4), values.astype(dtype).tobytes())
    assert img.mode == mode
    return img, (values >> 8).astype(np.uint8)


@requires_backend
@pytest.mark.parametrize("mode", ['I;16', 'I;16B', 'I'])
def test_16bit_modes_scale_to_8bit(mode):
    import numpy as np
    from optimize_images.img_convert import _to_8bit_grayscale
    img, expected = _gray16(mode)
    got = _to_8bit_grayscale(img)
    assert got.mode == 'L'
    assert np.array_equal(np.asarray(got), expected)

def test_cli_rejects_nan_threshold_cleanly(tmp_path):
    path = _photo(tmp_path / "img.jpg")
    before = path.read_bytes()
    proc = subprocess.run(
        [sys.executable, '-m', 'optimize_images', '-ssm', 'nan',
         str(tmp_path)], capture_output=True, text=True, timeout=60)
    assert 'Traceback' not in proc.stderr
    assert 'nan' in (proc.stdout + proc.stderr).lower()
    assert path.read_bytes() == before


@requires_backend
def test_public_ssim_is_plain_float(tmp_path):
    path = _photo(tmp_path / "img.jpg")
    data = path.read_bytes()
    _, result = optimize_image_data(data, show_ssim=True)
    assert type(result.ssim) is float
    _, result = convert_image_data(data, to='webp', show_ssim=True)
    assert type(result.ssim) is float
    result = optimize_single_image(str(path), show_ssim=True)
    assert type(result.ssim) is float


# --- CLI reporting and scoring of the gate (plan 1.4 and 5.7) ---

def _cli_batch(tmp_path, monkeypatch, results, **kw):
    """Run the CLI batch loop with a fake result stream.

    Returns the PublicBatchOptions the CLI passed to the API and the report
    printed for ``results``.
    """
    from optimize_images import __main__ as cli
    captured = {}

    def fake_stream(options):
        captured['options'] = options
        yield from results

    monkeypatch.setattr(cli, 'optimize_as_batch_stream', fake_stream)
    args = dict(
        src_path=str(tmp_path), watch_dir=False, recursive=True, quality=80,
        remove_transparency=False, reduce_colors=False, max_colors=256,
        max_w=0, max_h=0, keep_exif=False, convert_all=False, conv_big=False,
        force_del=False, bg_color=(255, 255, 255), grayscale=False,
        ignore_size_comparison=False, fast_mode=False, jobs=1,
        output_config=OutputConfiguration(False, False, False))
    args.update(kw)
    cli.optimize_batch(**args)
    return captured['options']


_OPTIMIZED = _status_result(True, 0.9912)
_GATE_REJECTED = _status_result(False, 0.9578)


@requires_backend
def test_cli_auto_show_does_not_force_scoring(tmp_path, monkeypatch, capsys):
    options = _cli_batch(tmp_path, monkeypatch, [_OPTIMIZED],
                         ssim_min=0.98, show_ssim=None)
    assert options.ssim_min == 0.98
    assert options.show_ssim is False


@requires_backend
def test_cli_explicit_show_forces_scoring(tmp_path, monkeypatch, capsys):
    options = _cli_batch(tmp_path, monkeypatch, [_OPTIMIZED],
                         ssim_min=0.98, show_ssim=True)
    assert options.show_ssim is True


@requires_backend
def test_cli_auto_show_reports_scores(tmp_path, monkeypatch, capsys):
    # Plan 5.7 must not change the report: -ssm alone still shows the score
    # of optimized files and the rejection line.
    _cli_batch(tmp_path, monkeypatch, [_OPTIMIZED, _GATE_REJECTED],
               ssim_min=0.98, show_ssim=None)
    out = capsys.readouterr().out
    assert 'SSIM: 0.9912' in out
    assert 'SSIM: 0.9578 below threshold 0.98' in out


@requires_backend
def test_cli_no_show_ssim_keeps_rejection_line(tmp_path, monkeypatch,
                                               capsys):
    # Plan 1.4, option (a): --no-show-ssim hides the scores of optimized
    # files, but the rejection line stays (it explains the skip).
    options = _cli_batch(tmp_path, monkeypatch, [_OPTIMIZED, _GATE_REJECTED],
                         ssim_min=0.98, show_ssim=False)
    out = capsys.readouterr().out
    assert options.show_ssim is False
    assert '0.9912' not in out
    assert 'SSIM: 0.9578 below threshold 0.98' in out


def _option_help(option):
    proc = subprocess.run([sys.executable, '-m', 'optimize_images', '-h'],
                          capture_output=True, text=True, timeout=60,
                          env={**os.environ, 'COLUMNS': '200'})
    lines = proc.stdout.splitlines()
    start = next(i for i, line in enumerate(lines)
                 if line.lstrip().startswith(option))
    text = [lines[start]]
    for line in lines[start + 1:]:
        if line.lstrip().startswith('-') or not line.strip():
            break
        text.append(line)
    return ' '.join(' '.join(text).split())


def test_no_show_ssim_help_mentions_rejection_line():
    text = _option_help('--no-show-ssim')
    assert 'threshold' in text.lower()


# --- orig_size must be passed explicitly to every transform (plan 5.3) ---
# A default of 0 would make every result look "not smaller": with ssim_min
# the score would be skipped and every file silently rejected.

@pytest.mark.parametrize("module, name", [
    ('img_optimize_jpg', 'transform_jpg'),
    ('img_optimize_png', 'transform_png'),
    ('img_optimize_webp', 'transform_webp'),
    ('img_convert', 'transform_convert'),
])
def test_transforms_require_orig_size(module, name):
    import importlib
    import inspect
    func = getattr(importlib.import_module(f'optimize_images.{module}'), name)
    param = inspect.signature(func).parameters['orig_size']
    assert param.default is inspect.Parameter.empty
