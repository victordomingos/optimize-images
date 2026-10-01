# encoding: utf-8
"""SSIM (Structural Similarity Index) support.

The SSIM features of optimize-images (per-file score reporting and the
``--ssim-min`` quality threshold) rely on scikit-image as an optional
dependency:

    pip install scikit-image

When scikit-image is not installed, scores simply cannot be computed and the
rest of the tool keeps working normally.
"""
from typing import Optional

from PIL import Image

from optimize_images.constants import DEFAULT_BG_COLOR
from optimize_images.exceptions import OISSIMNotAvailableError

try:
    import numpy as np
    from skimage.metrics import structural_similarity as _ssim_impl
    _HAS_SKIMAGE = True
except ImportError:
    np = None  # type: ignore[assignment]
    _ssim_impl = None  # type: ignore[assignment]
    _HAS_SKIMAGE = False


def ssim_available() -> bool:
    """Return True when the SSIM backend (scikit-image) is installed."""
    return _HAS_SKIMAGE


def ensure_ssim_available() -> None:
    """Stop early with a helpful message if scikit-image is missing.

    Called at the entry points (CLI, public batch API) whenever the user
    explicitly requests SSIM-based quality control (``ssim_min``), so the tool
    fails fast instead of running a whole batch that would reject everything.
    """
    if not _HAS_SKIMAGE:
        raise OISSIMNotAvailableError(
            "\nSSIM quality control (--ssim-min) requires scikit-image, which "
            "is not installed. Install it with: pip install scikit-image")


def validate_ssim_min(ssim_min: Optional[float]) -> None:
    """Validate a public-API ``ssim_min`` threshold.

    Mirrors the CLI check, so an API caller cannot silently reject every file
    (threshold above 1.0) or silently disable the gate (threshold below 0.0).
    """
    if ssim_min is not None and not 0.0 <= ssim_min <= 1.0:
        raise ValueError(
            f"ssim_min must be between 0.0 and 1.0, got {ssim_min}")


def _flatten_over(img: Image.Image, bg_color=DEFAULT_BG_COLOR) -> Image.Image:
    """Composite *img* over *bg_color* and return the result as 8-bit RGB.

    Flattening discards the invisible RGB of transparent pixels (which a
    format like WebP throws away anyway) and silences Pillow's warning for
    palette images with tRNS transparency.
    """
    rgba = img.convert('RGBA')
    return Image.alpha_composite(
        Image.new('RGBA', img.size, (*bg_color, 255)), rgba).convert('RGB')


def compute_ssim(img1: Image.Image, img2: Image.Image,
                 bg_color=DEFAULT_BG_COLOR) -> Optional[float]:
    """Compute the SSIM between two images, in memory.

    Both images are composited over ``bg_color`` (transparency flattened to
    8-bit RGB) before the comparison; the SSIM is computed independently for
    each color channel and averaged (``channel_axis=-1``), using the standard
    data_range of 255 for 8-bit data. Returns a plain Python float in [-1, 1]
    (1.0 means identical images) or None when the score cannot be computed
    (backend missing, different sizes, or a MemoryError/ValueError from the
    conversion or the comparison). Any other exception is propagated, so a
    real bug is not masked by a silent fail-closed rejection of every file.
    The window parameters (win_size=7, uniform weights, sample covariance)
    are pinned to scikit-image's current defaults so the calibrated
    thresholds stay valid if a future scikit-image version changes its
    defaults.
    """
    if not _HAS_SKIMAGE or _ssim_impl is None or np is None:
        return None
    if img1.size != img2.size:
        return None
    try:
        r1 = np.asarray(_flatten_over(img1, bg_color), dtype=np.float64)
        r2 = np.asarray(_flatten_over(img2, bg_color), dtype=np.float64)
        # scikit-image returns a numpy scalar; the public result must be a
        # plain Python float (no numpy dependency leaking to API callers).
        return float(_ssim_impl(r1, r2, data_range=255,
                                channel_axis=-1, win_size=7,
                                gaussian_weights=False,
                                use_sample_covariance=True))
    except (MemoryError, ValueError):
        return None
