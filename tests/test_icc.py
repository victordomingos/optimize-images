#!/usr/bin/env python3
"""ICC colour profiles must survive optimization and conversion (plan 7.9).

A profile tells viewers how to interpret the pixel values; dropping a wide-gamut
profile (e.g. Display P3) makes saturated colours look visibly different, while
the pixel values - and therefore the SSIM score - stay the same. Rules:

* a profile that is not equivalent to sRGB is kept, in place and on conversion;
* a profile equivalent to sRGB may be dropped (viewers assume sRGB anyway);
* when the colour model changes (e.g. RGB -> grayscale) the RGB profile no
  longer applies and must not be attached;
* without ImageCms (LittleCMS) the profile is kept and nothing raises.

The Display P3 profile comes from tests/test-images/jpeg_with_exif.jpg (read
only); images are generated in memory.
"""
import io

import pytest
from PIL import Image, ImageCms

from helpers import TEST_IMAGES
from optimize_images import formats
from optimize_images.api import convert_image_data, optimize_image_data, \
    optimize_single_image


def _p3_profile():
    with Image.open(TEST_IMAGES / "jpeg_with_exif.jpg") as img:
        icc = img.info["icc_profile"]
    assert "P3" in ImageCms.getProfileDescription(
        ImageCms.ImageCmsProfile(io.BytesIO(icc)))
    return icc


def _srgb_profile():
    return ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()


def _photo(size=(160, 120)):
    width, height = size
    img = Image.new("RGB", size)
    img.frombytes(bytes(v for y in range(height) for x in range(width)
                        for v in (x * 255 // width, y * 255 // height,
                                  (x * y) % 256)))
    return img


def _encode(fmt, icc, **save):
    buf = io.BytesIO()
    _photo().save(buf, fmt, icc_profile=icc, **save)
    return buf.getvalue()


def _profile_of(data):
    with Image.open(io.BytesIO(data)) as img:
        return img.info.get("icc_profile")


def _pixels(data):
    with Image.open(io.BytesIO(data)) as img:
        return img.convert("RGB").tobytes()


# --- wide-gamut profile is kept -------------------------------------------

def test_jpeg_optimization_keeps_p3_profile():
    icc = _p3_profile()
    out, _ = optimize_image_data(_encode("JPEG", icc, quality=95),
                                 ignore_size_comparison=True)
    assert _profile_of(out) == icc


def test_jpeg_file_optimization_keeps_p3_profile(tmp_path):
    icc = _p3_profile()
    path = tmp_path / "photo.jpg"
    path.write_bytes(_encode("JPEG", icc, quality=95))
    optimize_single_image(str(path), ignore_size_comparison=True)
    assert _profile_of(path.read_bytes()) == icc


def test_webp_optimization_keeps_p3_profile():
    icc = _p3_profile()
    out, _ = optimize_image_data(_encode("WEBP", icc, quality=95),
                                 ignore_size_comparison=True)
    assert _profile_of(out) == icc


def test_png_optimization_keeps_p3_profile():
    # PNG already keeps it today: guard against a regression.
    icc = _p3_profile()
    out, _ = optimize_image_data(_encode("PNG", icc),
                                 ignore_size_comparison=True)
    assert _profile_of(out) == icc


CONVERSIONS = [
    pytest.param("JPEG", "webp", id="jpeg-to-webp"),
    pytest.param("PNG", "jpeg", id="png-to-jpeg"),
    pytest.param("JPEG", "png", id="jpeg-to-png"),
]


@pytest.mark.parametrize("src_fmt, target", CONVERSIONS)
def test_conversion_keeps_p3_profile(src_fmt, target):
    icc = _p3_profile()
    out, result = convert_image_data(_encode(src_fmt, icc), to=target,
                                     ignore_size_comparison=True)
    assert result.was_optimized
    assert _profile_of(out) == icc


# Pillow's AVIF encoder already keeps the profile: regression guard.
@pytest.mark.skipif("avif" not in formats.available_output_formats(),
                    reason="AVIF encoder not available in this Pillow build")
def test_conversion_to_avif_keeps_p3_profile():
    icc = _p3_profile()
    out, _ = convert_image_data(_encode("JPEG", icc, quality=95), to="avif",
                                ignore_size_comparison=True)
    assert _profile_of(out) == icc


# --- profiles that must not be attached -----------------------------------

@pytest.mark.parametrize("fmt", ["JPEG", "WEBP", "PNG"])
def test_srgb_profile_is_dropped(fmt):
    # An sRGB profile adds bytes without changing how the image looks.
    out, _ = optimize_image_data(_encode(fmt, _srgb_profile()),
                                 ignore_size_comparison=True)
    assert _profile_of(out) is None


def test_srgb_check_tells_srgb_from_p3():
    """Verify the sRGB check distinguishes sRGB from P3 profiles."""
    from optimize_images.img_icc import _is_srgb_equivalent
    p3 = _p3_profile()
    srgb = _srgb_profile()
    # sRGB profile must be detected as equivalent to sRGB.
    assert _is_srgb_equivalent(srgb) is True
    # P3 must NOT be detected as sRGB-equivalent.
    assert _is_srgb_equivalent(p3) is False


# WebP has no grayscale mode (it decodes as RGB), so it is not checked here.
@pytest.mark.parametrize("fmt", [
    "JPEG",
    "PNG",
])
def test_grayscale_output_has_no_rgb_profile(fmt):
    out, _ = optimize_image_data(_encode(fmt, _p3_profile()), grayscale=True,
                                 ignore_size_comparison=True)
    with Image.open(io.BytesIO(out)) as img:
        assert img.mode in ("L", "LA")
        assert img.info.get("icc_profile") != _p3_profile()


# --- robustness -----------------------------------------------------------

def test_profile_kept_when_imagecms_is_unavailable(monkeypatch):
    # Without LittleCMS the sRGB check cannot run: keep the profile, no error.
    import builtins
    real_import = builtins.__import__

    def no_imagecms(name, *args, **kwargs):
        if name == "PIL.ImageCms" or (name == "PIL" and args and args[2]
                                      and "ImageCms" in args[2]):
            raise ImportError("ImageCms not available")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_imagecms)
    icc = _p3_profile()
    out, _ = optimize_image_data(_encode("JPEG", icc, quality=95),
                                 ignore_size_comparison=True)
    assert _profile_of(out) == icc


def test_corrupt_profile_does_not_break_optimization():
    out, result = optimize_image_data(_encode("JPEG", b"not an icc profile",
                                              quality=95),
                                      ignore_size_comparison=True)
    assert result.was_optimized
    assert _pixels(out)


def test_profile_does_not_change_pixel_values():
    # The profile only affects how pixels are displayed: the decoded pixels of
    # the optimized output are the same with and without it.
    with_icc, _ = optimize_image_data(_encode("JPEG", _p3_profile(),
                                              quality=95),
                                      ignore_size_comparison=True)
    without, _ = optimize_image_data(_encode("JPEG", None, quality=95),
                                     ignore_size_comparison=True)
    assert _pixels(with_icc) == _pixels(without)


# --- Review of the first implementation (2026-10-02) -----------------------

def _rgba_with_profile(fmt):
    img = Image.new("RGBA", (120, 90), (200, 30, 40, 255))
    img.paste((10, 200, 30, 128), (0, 0, 60, 45))
    buf = io.BytesIO()
    img.save(buf, fmt, icc_profile=_p3_profile())
    return buf.getvalue()


@pytest.mark.parametrize("label, call", [
    pytest.param("png-rt", lambda: optimize_image_data(
        _rgba_with_profile("PNG"), remove_transparency=True,
        ignore_size_comparison=True)),
    pytest.param("png-rc", lambda: optimize_image_data(
        _rgba_with_profile("PNG"), reduce_colors=True,
        ignore_size_comparison=True)),
    pytest.param("webp-rt", lambda: optimize_image_data(
        _rgba_with_profile("WEBP"), remove_transparency=True,
        ignore_size_comparison=True)),
    pytest.param("png-rgba-to-jpeg", lambda: convert_image_data(
        _rgba_with_profile("PNG"), to="jpeg", ignore_size_comparison=True)),
    pytest.param("jpeg-resize", lambda: optimize_image_data(
        _encode("JPEG", _p3_profile(), quality=95), max_w=60,
        ignore_size_comparison=True)),
])
def test_profile_survives_transforms(label, call):
    out, _ = call()
    assert _profile_of(out) == _p3_profile()


@pytest.mark.parametrize("fmt", ["JPEG", "WEBP", "PNG"])
def test_srgb_profile_is_dropped(fmt):
    out, _ = optimize_image_data(_encode(fmt, _srgb_profile()),
                                 ignore_size_comparison=True)
    assert _profile_of(out) is None


def test_srgb_check_tells_srgb_from_p3():
    from optimize_images.img_icc import _is_srgb_equivalent
    assert _is_srgb_equivalent(_srgb_profile()) is True
    assert _is_srgb_equivalent(_p3_profile()) is False


def _gray_profile_stub():
    # Only the colour-model field matters for the model check; the sRGB
    # check fails on it and the profile is kept, as for any unknown profile.
    profile = bytearray(200)
    profile[16:20] = b"GRAY"
    return bytes(profile)


@pytest.mark.parametrize("mode", ["I;16", "1"])
def test_grayscale_png_keeps_gray_profile(mode):
    img = Image.new(mode, (64, 64))
    buf = io.BytesIO()
    img.save(buf, "PNG", icc_profile=_gray_profile_stub())
    out, _ = optimize_image_data(buf.getvalue(), ignore_size_comparison=True)
    assert _profile_of(out) == _gray_profile_stub()
