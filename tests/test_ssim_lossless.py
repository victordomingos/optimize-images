#!/usr/bin/env python3
"""Identical images must score 1.0 without running the SSIM computation
(plan 5.1).

When the encoded result decodes to exactly the same pixels as the reference
(lossless PNG/WebP output, conversions to PNG or lossless WebP), the SSIM is
1.0 by definition, and the scikit-image call is the most expensive part of the
gate (about 7 s for a 30 MB PNG). The comparison happens after flattening both
images over the background colour, like the SSIM itself, so pixels hidden
under full transparency do not matter either.

End-to-end targets live in tests/test_ssim_perf.py
(test_lossless_output_skips_ssim_computation).
"""
import pytest
from PIL import Image

from optimize_images import img_ssim
from optimize_images.img_ssim import compute_ssim, ssim_available

pytestmark = pytest.mark.skipif(not ssim_available(),
                                reason="scikit-image not installed")

@pytest.fixture
def ssim_calls(monkeypatch):
    calls = []
    original = img_ssim._ssim_impl

    def counting(*args, **kwargs):
        calls.append(1)
        return original(*args, **kwargs)

    monkeypatch.setattr(img_ssim, "_ssim_impl", counting)
    return calls


def _gradient(mode="RGB", size=(96, 64)):
    width, height = size
    img = Image.new("RGB", size)
    img.frombytes(bytes(v for y in range(height) for x in range(width)
                        for v in (x * 255 // width, y * 255 // height,
                                  (x * y) % 256)))
    return img.convert(mode)


def test_identical_images_skip_the_computation(ssim_calls):
    img = _gradient()
    assert compute_ssim(img, img.copy()) == 1.0
    assert not ssim_calls


def test_identical_after_flattening_skips_the_computation(ssim_calls):
    # Different RGB hidden under alpha 0: identical once flattened.
    a = _gradient("RGBA")
    b = a.copy()
    a.putalpha(0)
    b.putalpha(0)
    b.paste((10, 200, 30, 0), (0, 0, 20, 20))
    assert compute_ssim(a, b) == 1.0
    assert not ssim_calls


def test_identical_palette_and_rgb_versions_skip_the_computation(ssim_calls):
    # A lossless re-encoding may change the mode (e.g. P -> RGB) but not the
    # pixels: still identical after flattening.
    p = _gradient().quantize(64)
    assert compute_ssim(p, p.convert("RGB")) == 1.0
    assert not ssim_calls


def test_different_images_are_still_scored(ssim_calls):
    a = _gradient()
    b = a.copy()
    b.paste((255, 0, 0), (10, 10, 30, 30))
    score = compute_ssim(a, b)
    assert ssim_calls
    assert score is not None and score < 1.0


def test_one_pixel_difference_is_still_scored(ssim_calls):
    a = _gradient()
    b = a.copy()
    b.putpixel((5, 5), (0, 0, 0))
    score = compute_ssim(a, b)
    assert ssim_calls
    assert score is not None and score < 1.0


def test_different_sizes_still_return_none(ssim_calls):
    assert compute_ssim(_gradient(size=(96, 64)),
                        _gradient(size=(64, 96))) is None
    assert not ssim_calls


def test_score_is_a_plain_float():
    img = _gradient()
    assert type(compute_ssim(img, img.copy())) is float


def test_flatten_out_of_memory_propagates(monkeypatch):
    # Running out of memory is not a score: it propagates to the caller,
    # which keeps the original and reports the file as out of memory.
    def out_of_memory(*_args, **_kwargs):
        raise MemoryError

    monkeypatch.setattr(img_ssim, "_flatten_over", out_of_memory)
    img = _gradient()
    with pytest.raises(MemoryError):
        compute_ssim(img, img.copy())


def test_flatten_value_error_still_returns_none(monkeypatch):
    def bad_input(*_args, **_kwargs):
        raise ValueError

    monkeypatch.setattr(img_ssim, "_flatten_over", bad_input)
    img = _gradient()
    assert compute_ssim(img, img.copy()) is None
