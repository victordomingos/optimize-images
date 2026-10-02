# encoding: utf-8
"""ICC colour-profile handling for JPEG, PNG, and WebP output.

Extracts the source profile, checks whether it should be attached to the
output (colour-model match + not sRGB-equivalent), and returns the profile
bytes or None.  Called by every transform_* function so that in-memory and
file-based paths behave identically.

When ImageCms is unavailable or the profile is corrupt the profile is kept
without raising.
"""

from io import BytesIO
from typing import Optional

from PIL import Image

# Cache for _is_srgb_equivalent: profile_bytes → bool (or None = unknown).
_srgb_cache: dict[bytes, Optional[bool]] = {}


def _is_srgb_equivalent(profile_bytes: bytes) -> Optional[bool]:
    """Check whether *profile_bytes* is sRGB-equivalent using ImageCms.

    Returns True/False if ImageCms is available and the check succeeds,
    or None when ImageCms is not available or the check failed in any way.

    Uses a 16×16 test cube and considers the profile equivalent when every
    channel differs by at most 1 after round-tripping through it.
    """
    if profile_bytes in _srgb_cache:
        return _srgb_cache[profile_bytes]  # type: ignore[return-value]

    try:
        from PIL import ImageCms
    except ImportError:
        _srgb_cache[profile_bytes] = None
        return None

    try:
        cms_profile = ImageCms.ImageCmsProfile(BytesIO(profile_bytes))
        srgb_profile = ImageCms.createProfile("sRGB")
        test_cube = _get_test_cube()
        transformed = ImageCms.profileToProfile(
            test_cube, cms_profile, srgb_profile, outputMode="RGB")
        orig_data = test_cube.tobytes()
        new_data = transformed.tobytes()
        # Compare every byte; allow ±1 difference per channel (3 bytes per
        # pixel), which means the max difference per sample is 1.
        diff_ok = True
        for i in range(0, len(orig_data), 3):
            for j in range(3):
                d = abs(orig_data[i + j] - new_data[i + j])
                if d > 1:
                    diff_ok = False
                    break
            if not diff_ok:
                break
        result = diff_ok  # True = sRGB-equivalent
    except Exception:
        result = None

    _srgb_cache[profile_bytes] = result
    return result


# ICC profile colour-model signatures (bytes 16-20).
_PROFILE_RGB = (b"RGB ", b"RGB\0", b"RGBx")
_PROFILE_GRAY = (b"GRAY",)
_PROFILE_CMYK = (b"CMYK",)

# Output image modes mapped to ICC model names:
# RGB-family (store colour data that an RGB profile describes):
#   RGB, RGBX, RGBA, RGBa, P, PA.
# Grayscale-family (store luminance data that a GRAY profile describes):
#   1 (1-bit), L, La (grayscale+alpha),
#   I, I;16, I;16L, I;16B, I;16N (integer), F (32-bit float).
# CMYK → "CMYK".
# Unmapped modes fall through to the sentinel "_KEEP_PROFILE"
# which tells get_suitable_icc to keep the profile (don't drop).
_MODE_TO_MODEL: dict[str, str] = {
    "RGB": "RGB", "RGBX": "RGB", "RGBA": "RGB", "RGBa": "RGB",
    "P": "RGB", "PA": "RGB",
    "1": "GRAY", "L": "GRAY", "La": "GRAY",
    "I": "GRAY", "I;16": "GRAY",
    "I;16L": "GRAY", "I;16B": "GRAY", "I;16N": "GRAY",
    "F": "GRAY",
    "CMYK": "CMYK",
}


def _model_from_profile(profile: bytes) -> Optional[str]:
    """Extract the colour model from an ICC profile (bytes 16-20).

    Returns the model string or None if the profile is too short /
    unrecognized.
    """
    if len(profile) < 21:
        return None
    header = profile[16:20]
    if header in _PROFILE_RGB:
        return "RGB"
    if header in _PROFILE_GRAY:
        return "GRAY"
    if header in _PROFILE_CMYK:
        return "CMYK"
    return None


def _output_model_for(mode: str) -> str:
    """Map an output image mode to its ICC colour model name.

    Returns the sentinel "_KEEP_PROFILE" for unknown modes, so that
    get_suitable_icc keeps the profile (never drops)."""
    return _MODE_TO_MODEL.get(mode, "_KEEP_PROFILE")


def get_suitable_icc(profile_bytes: Optional[bytes],
                     result_mode: str,
                     fmt: str) -> Optional[bytes]:
    """Decide which ICC profile (if any) should be attached.

    Parameters
    ----------
    profile_bytes : bytes | None
        The source image's ICC profile (already extracted before any
        transforms).  None means there was no profile.
    result_mode : str
        The colour mode of the output image (e.g. "L" for grayscale).
    fmt : str
        The output format (e.g. "JPEG", "PNG", "WEBP").  Used to skip
        formats whose Pillow encoder does not accept ``icc_profile``.

    Returns
    -------
    bytes | None
        The profile bytes to pass as ``icc_profile=…`` to ``Image.save()``,
        or None when the profile should not be attached.  Returns None
        (don't attach) when: there is no source profile, the output colour
        model does not match the profile model, or the profile is equivalent
        to sRGB (viewers assume sRGB).  Returns the original profile bytes
        otherwise.  If anything goes wrong (ImageCms import failure, corrupt
        profile, check failure) the profile is kept (never raises).

    Note
    ----
    JPEG2000 is excluded: Pillow's JPEG2000 encoder does not accept the
    ``icc_profile`` keyword, so the caller must skip it.
    """
    if fmt == "JPEG2000":
        return None  # encoder does not accept icc_profile

    if profile_bytes is None:
        return None

    # 1. Check colour-model compatibility (compare models, not modes).
    out_model = _model_from_profile(profile_bytes)
    if out_model is None:
        return profile_bytes  # unrecognized model → keep it

    expected_model = _output_model_for(result_mode)
    if expected_model == "_KEEP_PROFILE":
        return profile_bytes  # unknown mode → keep profile (don't drop)
    if out_model != expected_model:
        return None  # e.g. RGB source → L output: drop RGB profile

    # 2. Skip sRGB-equivalent profiles (viewers assume sRGB anyway).
    srgb_result = _is_srgb_equivalent(profile_bytes)
    if srgb_result is True:
        return None  # equivalent to sRGB — drop to save bytes

    # sRGB check failed or ImageCms unavailable → keep the profile.
    return profile_bytes


# Pre-computed test cube (16 values per channel).  Reused for every sRGB
# check to avoid creating the cube repeatedly.
_test_cube: Optional[Image.Image] = None


def _get_test_cube() -> Image.Image:
    """Return a small RGB image with 16 values per channel (cached)."""
    global _test_cube
    if _test_cube is None:
        # 16 values: 0, 17, 34, …, 255  (16 * 17 = 272 ≈ 255)
        values = [v * 17 for v in range(16)]
        width, height = 16, 16
        img = Image.new("RGB", (width, height))
        pixels = img.load()
        for y in range(height):
            for x in range(width):
                pixels[x, y] = (values[x], values[y], values[x ^ y])
        _test_cube = img
    return _test_cube
