#!/usr/bin/env python3
"""Correctness guards for SSIM performance work.

Every performance change to the SSIM path (lossless short-circuit, size check
before SSIM, float32, per-channel threads) must leave scores and gate
decisions unchanged. These tests compare the production results against an
independent reference computed here (the pre-optimization algorithm: flatten
over the background, float64, scikit-image with pinned parameters), so they
do not depend on golden files that would drift with Pillow's encoders.

Tests marked ``xfail(strict=True)`` describe optimizations not implemented
yet: they start passing when the optimization lands, and strict mode then
turns the XPASS into a failure so the marker gets removed.

Timing is deliberately not asserted here (it would be flaky); speed is
measured with ``benchmarks/ssim_bench.py``.
"""
import io
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Tuple

import pytest
from PIL import Image

from optimize_images import img_ssim
from optimize_images.api import convert_image_data, optimize_image_data, \
    optimize_single_image
from optimize_images.img_aux_processing import do_reduce_colors, \
    downsize_img, make_grayscale, remove_transparency
from optimize_images.img_ssim import compute_ssim, ssim_available

if not ssim_available():
    # The corpus below is built with numpy at import time, so skip the whole
    # module before that (a skip mark would only apply after collection).
    pytest.skip("scikit-image not installed", allow_module_level=True)

WHITE = (255, 255, 255)
SCORE_TOLERANCE = 1e-4  # "same score to 4 decimal places"
THRESHOLDS = [0.0, 0.9, 0.95, 0.98, 0.999, 1.0]


# --------------------------------------------------------------------------
# Deterministic synthetic corpus
# --------------------------------------------------------------------------

def _photo_rgb(size=(320, 240), seed=42):
    """Photo-like content: smooth gradients plus seeded noise, so lossy
    encoders produce scores clearly below 1.0."""
    import numpy as np
    w, h = size
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:h, 0:w]
    base = np.stack([(x * 255 // w), (y * 255 // h), ((x + y) * 127 // (w + h))],
                    axis=-1)
    noisy = np.clip(base + rng.normal(0, 18, base.shape), 0, 255)
    return Image.fromarray(noisy.astype('uint8'))


def _logo_rgba(size=(200, 200)):
    """Opaque disc over a transparent background with arbitrary hidden RGB."""
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


def _palette_trns(size=(64, 64)):
    img = Image.new('P', size)
    img.putpalette([i % 256 for i in range(768)])
    img.putdata([(x + y) % 256 for y in range(size[1]) for x in range(size[0])])
    return img


def _encode(img, fmt, **save):
    buf = io.BytesIO()
    img.save(buf, fmt, **save)
    return buf.getvalue()


def _corpus():
    photo = _photo_rgb()
    trns = bytes([0] * 10 + [255] * 246)
    return {
        'jpeg_rgb': _encode(photo, 'JPEG', quality=95),
        'jpeg_gray': _encode(photo.convert('L'), 'JPEG', quality=95),
        'jpeg_cmyk': _encode(photo.convert('CMYK'), 'JPEG', quality=95),
        'png_rgb': _encode(photo, 'PNG'),
        'png_rgba': _encode(_logo_rgba(), 'PNG'),
        'png_p_trns': _encode(_palette_trns(), 'PNG', transparency=trns),
        'webp_lossy_rgb': _encode(photo, 'WEBP', quality=95),
        'webp_lossy_rgba': _encode(_logo_rgba(), 'WEBP', quality=95),
        'webp_lossless_rgb': _encode(photo, 'WEBP', lossless=True),
        'webp_lossless_rgba': _encode(_logo_rgba(), 'WEBP', lossless=True,
                                      exact=True),
        # Larger image: float32 error grows with the number of windows.
        'jpeg_large': _encode(_photo_rgb((1024, 768), seed=7), 'JPEG',
                              quality=95),
    }


CORPUS = _corpus()

# (label, call) pairs covering the in-place and the conversion paths.
OPERATIONS = {
    'optimize': lambda data, **kw: optimize_image_data(data, **kw),
    'to_webp': lambda data, **kw: convert_image_data(data, to='webp', **kw),
    'to_jpeg': lambda data, **kw: convert_image_data(data, to='jpeg', **kw),
    'to_png': lambda data, **kw: convert_image_data(data, to='png', **kw),
}

# Pre-existing failures unrelated to SSIM, kept visible as strict xfails:
# (case, operation) -> (expected exception, reason).
KNOWN_BROKEN: Dict[Tuple[str, str], Tuple[type, str]] = {}


def _cases():
    for name in CORPUS:
        for op in OPERATIONS:
            broken = KNOWN_BROKEN.get((name, op))
            marks = [pytest.mark.xfail(strict=True, raises=broken[0],
                                       reason=broken[1])] if broken else []
            yield pytest.param(name, op, id=f"{name}-{op}", marks=marks)


CASES = list(_cases())
# The large image only matters for score precision (float32); keeping it out
# of the per-threshold decision tests keeps the suite fast.
GATE_CASES = [c for c in CASES if c.values[0] != 'jpeg_large']


def _run(op, name, **kw):
    return OPERATIONS[op](CORPUS[name], **kw)


# --------------------------------------------------------------------------
# Independent reference (the pre-optimization algorithm)
# --------------------------------------------------------------------------

def _reference_ssim(src_bytes, out_bytes, bg_color=WHITE):
    import numpy as np
    from skimage.metrics import structural_similarity

    def flat(data):
        with Image.open(io.BytesIO(data)) as img:
            rgba = img.convert('RGBA')
        bg = Image.new('RGBA', rgba.size, (*bg_color, 255))
        return np.asarray(Image.alpha_composite(bg, rgba).convert('RGB'),
                          dtype=np.float64)

    score: Any = structural_similarity(
        flat(src_bytes), flat(out_bytes), data_range=255, channel_axis=-1,
        win_size=7, gaussian_weights=False, use_sample_covariance=True)
    return float(score)


def _png_bytes(img):
    """Lossless container for an already-transformed reference image."""
    return _encode(img, 'PNG')


def _encoded(op, name):
    """The encoder output, always kept (size comparison off, no gate)."""
    out, result = _run(op, name, ignore_size_comparison=True, show_ssim=True)
    assert result.was_optimized
    return out, result


@pytest.fixture
def ssim_calls(monkeypatch):
    """Count calls into the scikit-image backend (the expensive part).

    Contract for SSIM optimizations: keep calling scikit-image through
    ``img_ssim._ssim_impl``, or this counter stops measuring and the tests
    that use it fail (or XPASS) for the wrong reason.
    """
    calls = []
    original = img_ssim._ssim_impl

    def counting(*args, **kwargs):
        calls.append(1)
        return original(*args, **kwargs)

    monkeypatch.setattr(img_ssim, "_ssim_impl", counting)
    return calls


# --------------------------------------------------------------------------
# Regression: scores and decisions must not change
# --------------------------------------------------------------------------

@pytest.mark.parametrize("name, op", CASES)
def test_score_matches_reference(name, op):
    data = CORPUS[name]
    out, result = _encoded(op, name)
    assert result.ssim is not None
    assert result.ssim == pytest.approx(_reference_ssim(data, out),
                                        abs=SCORE_TOLERANCE)


@pytest.mark.slow
@pytest.mark.parametrize("name, op", GATE_CASES)
def test_gate_decision_matches_reference(name, op):
    """Kept iff at least ~1% smaller AND score >= threshold; the returned
    bytes are the encoder output when kept and the original otherwise."""
    data = CORPUS[name]
    encoded, _ = _encoded(op, name)
    reference = _reference_ssim(data, encoded)
    smaller = len(encoded) / len(data) < .99
    for threshold in THRESHOLDS:
        # A score within the tolerance of the threshold may legitimately flip.
        if abs(reference - threshold) <= SCORE_TOLERANCE:
            continue
        out, result = _run(op, name, ssim_min=threshold)
        expected = smaller and reference >= threshold
        assert result.was_optimized == expected, (threshold, reference)
        assert out == (encoded if expected else data)


@pytest.mark.slow
@pytest.mark.parametrize("name, op", GATE_CASES)
def test_gate_decision_without_size_comparison(name, op):
    """With -nc only the threshold decides, so SSIM must still be computed."""
    data = CORPUS[name]
    encoded, _ = _encoded(op, name)
    reference = _reference_ssim(data, encoded)
    for threshold in THRESHOLDS:
        if abs(reference - threshold) <= SCORE_TOLERANCE:
            continue
        _, result = _run(op, name, ssim_min=threshold,
                         ignore_size_comparison=True)
        assert result.ssim is not None
        assert result.was_optimized == (reference >= threshold)


def test_score_is_deterministic_under_concurrency():
    """Guards per-channel threading and free-threaded execution: the same
    pair must give the same score, sequentially and concurrently."""
    data = CORPUS['jpeg_large']
    out, _ = _encoded('optimize', 'jpeg_large')
    src = Image.open(io.BytesIO(data))
    enc = Image.open(io.BytesIO(out))
    src.load()
    enc.load()
    first = compute_ssim(src, enc)
    assert all(compute_ssim(src, enc) == first for _ in range(3))
    with ThreadPoolExecutor(max_workers=4) as pool:
        scores = list(pool.map(lambda _: compute_ssim(src, enc), range(8)))
    assert all(score == first for score in scores)


def test_ssim_computed_when_size_comparison_disabled(ssim_calls):
    # Must hold before and after the "size before SSIM" change.
    data = _encode(_photo_rgb(), 'JPEG', quality=30)
    _, result = optimize_image_data(data, fast_mode=True, quality=95,
                                    ignore_size_comparison=True,
                                    ssim_min=0.5)
    assert ssim_calls
    assert result.ssim is not None


# --------------------------------------------------------------------------
# Targets for the optimizations (xfail until implemented)
# --------------------------------------------------------------------------

LOSSLESS_OUTPUTS = {
    'png_optimize': lambda: optimize_image_data(CORPUS['png_rgb'],
                                                ssim_min=0.99,
                                                ignore_size_comparison=True),
    'png_p_trns_optimize': lambda: optimize_image_data(
        CORPUS['png_p_trns'], ssim_min=0.99, ignore_size_comparison=True,
        fast_mode=True),
    'webp_lossless_reencode': lambda: optimize_image_data(
        CORPUS['webp_lossy_rgb'], webp_lossless=True, ssim_min=0.99,
        ignore_size_comparison=True),
    'webp_lossless_rgba_reencode': lambda: optimize_image_data(
        CORPUS['webp_lossless_rgba'], webp_lossless=True, ssim_min=0.99,
        ignore_size_comparison=True),
    'convert_to_png': lambda: convert_image_data(
        CORPUS['jpeg_rgb'], to='png', ssim_min=0.99,
        ignore_size_comparison=True),
    'convert_to_webp_lossless': lambda: convert_image_data(
        CORPUS['png_rgba'], to='webp', webp_lossless=True, ssim_min=0.99,
        ignore_size_comparison=True),
}


@pytest.mark.parametrize("case", LOSSLESS_OUTPUTS)
def test_lossless_output_scores_exactly_one(case):
    # Holds today (computed ~1.0) and after the short-circuit (assigned 1.0).
    _, result = LOSSLESS_OUTPUTS[case]()
    assert result.ssim == pytest.approx(1.0, abs=SCORE_TOLERANCE)
    assert result.was_optimized


@pytest.mark.parametrize("case", LOSSLESS_OUTPUTS)
def test_lossless_output_skips_ssim_computation(case, ssim_calls):
    _, result = LOSSLESS_OUTPUTS[case]()
    assert not ssim_calls
    assert result.ssim == 1.0
    assert result.was_optimized


def _bigger_output() -> Tuple[bytes, Dict[str, Any]]:
    # A heavily compressed JPEG re-encoded at high quality grows.
    data = _encode(_photo_rgb(), 'JPEG', quality=30)
    return data, dict(fast_mode=True, quality=95)


def test_size_rejected_file_skips_ssim_computation(ssim_calls):
    # Plan 5.2, option (b): skip only for the gate without --show-ssim.
    data, options = _bigger_output()
    out, result = optimize_image_data(data, **options, ssim_min=0.5)
    assert not result.was_optimized
    assert out == data
    assert not ssim_calls
    assert result.ssim is None


@pytest.mark.parametrize("gate", [dict(show_ssim=True),
                                  dict(show_ssim=True, ssim_min=0.5)])
def test_size_rejected_file_still_scored_with_show_ssim(gate, ssim_calls):
    # Plan 5.2, option (b): --show-ssim always gets the score in the result.
    data, options = _bigger_output()
    out, result = optimize_image_data(data, **options, **gate)
    assert not result.was_optimized
    assert out == data
    assert ssim_calls
    assert result.ssim is not None


def test_size_rejected_file_decision_unchanged():
    # The decision itself must not depend on the evaluation order.
    data, options = _bigger_output()
    gates: Tuple[Dict[str, Any], ...] = (dict(ssim_min=0.5),
                                         dict(ssim_min=0.99), {})
    for gate in gates:
        out, result = optimize_image_data(data, **options, **gate)
        assert not result.was_optimized
        assert out == data


# --------------------------------------------------------------------------
# Transforms: the reference must be the post-transform image (plan F0 0.1)
# --------------------------------------------------------------------------
# Each case replays, on the decoded source, the same transform chain the
# production path applies before encoding. If an optimization moved the
# reference capture before the transforms, the score would change (or become
# None for a resize) and these tests would fail.

def _decoded(name):
    with Image.open(io.BytesIO(CORPUS[name])) as img:
        img.load()
        return img.copy()


def _down(img):
    return downsize_img(img, 160, 0)[0]


TRANSFORM_CASES = {
    # label: (corpus name, operation, options, reference transform chain)
    'png_resize': ('png_rgb', 'optimize', dict(max_w=160), _down),
    'jpeg_resize': ('jpeg_rgb', 'optimize', dict(max_w=160), _down),
    'webp_resize': ('webp_lossy_rgb', 'optimize', dict(max_w=160), _down),
    'jpeg_to_webp_resize': ('jpeg_rgb', 'to_webp', dict(max_w=160), _down),
    'png_to_jpeg_resize': ('png_rgb', 'to_jpeg', dict(max_w=160), _down),
    'png_gray': ('png_rgb', 'optimize', dict(grayscale=True),
                 make_grayscale),
    'jpeg_gray': ('jpeg_rgb', 'optimize', dict(grayscale=True),
                  make_grayscale),
    'jpeg_to_webp_gray': ('jpeg_rgb', 'to_webp', dict(grayscale=True),
                          make_grayscale),
    'png_resize_gray': ('png_rgb', 'optimize',
                        dict(max_w=160, grayscale=True),
                        lambda img: make_grayscale(_down(img))),
    # -rt flattens over the same colour the score composites over, so these
    # two only guard the path; they cannot detect an early reference.
    'png_rt': ('png_rgba', 'optimize',
               dict(remove_transparency=True, bg_color=(0, 0, 255)),
               lambda img: remove_transparency(img, (0, 0, 255))),
    'webp_rt': ('webp_lossy_rgba', 'optimize',
                dict(remove_transparency=True, bg_color=(0, 0, 255)),
                lambda img: remove_transparency(img, (0, 0, 255))),
    'png_rc': ('png_rgb', 'optimize',
               dict(reduce_colors=True, max_colors=64),
               lambda img: do_reduce_colors(img, 64)[0]),
}

# Outputs of these cases are lossless encodings of the transformed image.
LOSSLESS_TRANSFORM_CASES = ['png_resize', 'png_gray', 'png_resize_gray',
                            'png_rt', 'png_rc']


def _transform_run(label, **kw):
    name, op, options, _ = TRANSFORM_CASES[label]
    return OPERATIONS[op](CORPUS[name], **options, **kw)


def _transform_reference(label):
    name, _, options, chain = TRANSFORM_CASES[label]
    return _png_bytes(chain(_decoded(name)))


@pytest.mark.parametrize("label", TRANSFORM_CASES)
def test_transform_score_matches_reference(label):
    bg = TRANSFORM_CASES[label][2].get('bg_color', WHITE)
    out, result = _transform_run(label, ignore_size_comparison=True,
                                 show_ssim=True)
    assert result.was_optimized
    assert result.ssim is not None
    expected = _reference_ssim(_transform_reference(label), out, bg_color=bg)
    assert result.ssim == pytest.approx(expected, abs=SCORE_TOLERANCE)


@pytest.mark.parametrize("label", LOSSLESS_TRANSFORM_CASES)
def test_transform_lossless_output_is_kept_by_strict_gate(label):
    # The sharp guard: resize/grayscale/-rt/-rc followed by a lossless
    # encoding scores 1.0 against the transformed reference, so even a very
    # strict gate keeps it. A reference taken from the untransformed source
    # would score lower (or None after a resize) and reject it.
    out, result = _transform_run(label, ignore_size_comparison=True,
                                 ssim_min=0.99)
    assert result.ssim == pytest.approx(1.0, abs=SCORE_TOLERANCE)
    assert result.was_optimized
    assert out != CORPUS[TRANSFORM_CASES[label][0]]


@pytest.mark.slow
@pytest.mark.parametrize("label", TRANSFORM_CASES)
def test_transform_gate_decision_matches_reference(label):
    bg = TRANSFORM_CASES[label][2].get('bg_color', WHITE)
    out, _ = _transform_run(label, ignore_size_comparison=True,
                            show_ssim=True)
    score = _reference_ssim(_transform_reference(label), out, bg_color=bg)
    for threshold in (0.9, 0.98, 0.999):
        if abs(score - threshold) <= SCORE_TOLERANCE:
            continue
        gated, result = _transform_run(label, ignore_size_comparison=True,
                                       ssim_min=threshold)
        assert result.was_optimized == (score >= threshold), threshold
        assert (gated == out) == result.was_optimized, threshold


# --------------------------------------------------------------------------
# File-based path (save_compressed): same decisions as in memory (F0 0.2)
# --------------------------------------------------------------------------

FILE_CASES = [
    ('jpeg_rgb', 'optimize'), ('webp_lossy_rgb', 'optimize'),
    ('png_rgba', 'optimize'), ('png_rgb', 'to_webp'),
    ('jpeg_rgb', 'to_webp'), ('png_rgba', 'to_jpeg'),
]
FILE_EXT = {'JPEG': 'jpg', 'PNG': 'png', 'WEBP': 'webp'}
TARGET_EXT = {'to_webp': 'webp', 'to_jpeg': 'jpg', 'to_png': 'png'}


def _write_source(tmp_path, name):
    with Image.open(io.BytesIO(CORPUS[name])) as img:
        ext = FILE_EXT[img.format]
    path = tmp_path / f"src.{ext}"
    path.write_bytes(CORPUS[name])
    return path


def _file_run(tmp_path, name, op, **kw):
    path = _write_source(tmp_path, name)
    if op != 'optimize':
        kw.update(convert_all=True, convert_to=op[3:])
    result = optimize_single_image(str(path), **kw)
    return path, result


@pytest.mark.slow
@pytest.mark.parametrize("no_cmp", [False, True], ids=['cmp', 'nc'])
@pytest.mark.parametrize("threshold", [0.9, 0.98, 0.999, 1.0])
@pytest.mark.parametrize("name, op", FILE_CASES,
                         ids=[f"{n}-{o}" for n, o in FILE_CASES])
def test_file_path_matches_in_memory(tmp_path, name, op, threshold, no_cmp):
    mem_out, mem = _run(op, name, ignore_size_comparison=no_cmp,
                        ssim_min=threshold)
    path, res = _file_run(tmp_path, name, op, ignore_size_comparison=no_cmp,
                          ssim_min=threshold)
    assert res.was_optimized == mem.was_optimized
    assert (res.ssim is None) == (mem.ssim is None)
    if mem.ssim is not None:
        assert res.ssim == pytest.approx(mem.ssim, abs=SCORE_TOLERANCE)
    if op == 'optimize':
        assert path.read_bytes() == mem_out
        return
    target = path.with_suffix('.' + TARGET_EXT[op])
    if mem.was_optimized:
        assert target.read_bytes() == mem_out
    else:
        assert not target.exists()
        assert path.read_bytes() == CORPUS[name]


@pytest.mark.parametrize("name, op", [('jpeg_rgb', 'to_webp'),
                                      ('png_rgba', 'to_jpeg')])
def test_ssim_computed_without_size_comparison_on_conversion(name, op,
                                                             ssim_calls):
    _, result = _run(op, name, ignore_size_comparison=True, ssim_min=0.5)
    assert ssim_calls
    assert result.ssim is not None


def test_ssim_computed_without_size_comparison_on_file_path(tmp_path,
                                                            ssim_calls):
    _, result = _file_run(tmp_path, 'jpeg_rgb', 'optimize',
                          ignore_size_comparison=True, ssim_min=0.5)
    assert ssim_calls
    assert result.ssim is not None


# --------------------------------------------------------------------------
# Palette PNG must be optimized losslessly (plan F2)
# --------------------------------------------------------------------------

def _quantized_photo():
    return _encode(_photo_rgb().quantize(256), 'PNG')


PALETTE_SOURCES = {
    'quantized_photo': _quantized_photo,
    'palette_trns': lambda: CORPUS['png_p_trns'],
}


@pytest.mark.parametrize("source", PALETTE_SOURCES)
def test_palette_png_default_optimization_is_lossless(source):
    data = PALETTE_SOURCES[source]()
    with Image.open(io.BytesIO(data)) as img:
        colors_before = len(img.convert('RGBA').getcolors(1 << 24))
    out, result = optimize_image_data(data, ignore_size_comparison=True,
                                      show_ssim=True)
    with Image.open(io.BytesIO(out)) as img:
        colors_after = len(img.convert('RGBA').getcolors(1 << 24))
    assert colors_after == colors_before
    assert _reference_ssim(data, out) == pytest.approx(1.0,
                                                       abs=SCORE_TOLERANCE)
