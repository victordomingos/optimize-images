# encoding: utf-8
"""Format registry and capability discovery.

The set of usable formats depends on the Pillow build actually installed (which
codecs were compiled in), so this module probes the running Pillow instead of
assuming a fixed list. This is the single source of truth used both for image
discovery/optimization and for the ``--convert-to`` output targets, and it is
exposed through the public API so that third-party apps can populate their own
menus from it.
"""
from io import BytesIO
from typing import Dict, List, NamedTuple, Optional

from PIL import Image, features


class FormatInfo(NamedTuple):
    pil: str  # Pillow format name (used on open/save)
    extensions: tuple  # file extensions, lowercase, without the dot
    lossy: bool
    supports_alpha: bool
    supports_animation: bool
    supports_exif: bool
    feature: Optional[str]  # PIL.features codec to gate on, if any
    can_optimize: bool  # has a dedicated in-place optimizer
    can_target: bool  # may be used as a conversion target


# Curated set of sensible raster image formats. Vector/document/scientific
# formats that Pillow also knows (PDF, EPS, WMF, FITS, GRIB, DDS, ...) are
# deliberately left out. Only the formats that actually compress are offered as
# conversion targets.
FORMATS: Dict[str, FormatInfo] = {
    'jpeg': FormatInfo('JPEG', ('jpg', 'jpeg', 'mpo'),
                       True, False, False, True, None, True, True),
    'png': FormatInfo('PNG', ('png',),
                      False, True, False, False, None, True, True),
    'webp': FormatInfo('WEBP', ('webp',),
                       True, True, True, True, 'webp', True, True),
    'avif': FormatInfo('AVIF', ('avif',),
                       True, True, True, True, 'avif', False, True),
    'jpeg2000': FormatInfo('JPEG2000', ('jp2', 'j2k', 'jpf', 'jpx', 'jpm'),
                           True, True, False, False, 'jpg_2000', False, True),
}


def _codec_ok(info: FormatInfo) -> bool:
    """True if the codec this format needs is present in the Pillow build."""
    if info.feature is None:
        return True
    try:
        return bool(features.check(info.feature))
    except Exception:
        return False


def _can_encode(pil_name: str) -> bool:
    """Probe whether this Pillow build can actually encode the format."""
    try:
        Image.new('RGB', (1, 1)).save(BytesIO(), format=pil_name)
        return True
    except Exception:
        return False


def available_output_formats() -> List[str]:
    """Conversion target formats usable on this system (probed)."""
    return [name for name, info in FORMATS.items()
            if info.can_target and _codec_ok(info) and _can_encode(info.pil)]


def available_input_formats() -> List[str]:
    """File extensions of images this build can read and optimize."""
    exts: List[str] = []
    for info in FORMATS.values():
        if info.can_optimize and _codec_ok(info):
            exts.extend(info.extensions)
    seen = set()
    return [e for e in exts if not (e in seen or seen.add(e))]


def format_capabilities() -> Dict[str, dict]:
    """Per-format capability metadata, meant for building UIs."""
    caps = {}
    for name, info in FORMATS.items():
        ok = _codec_ok(info)
        caps[name] = {
            'extensions': list(info.extensions),
            'reads': bool(info.can_optimize and ok),
            'writes': bool(info.can_target and ok and _can_encode(info.pil)),
            'lossy': info.lossy,
            'supports_alpha': info.supports_alpha,
            'supports_animation': info.supports_animation,
        }
    return caps


def normalize_target(value: str) -> str:
    """Validate and normalize a conversion target against availability.

    Treats None/'' as the default ('jpeg'), is case-insensitive and accepts
    'jpg' as an alias for 'jpeg'. Raises ValueError for unknown or unavailable
    targets, distinguishing "not a known format" from "known but missing codec
    in this Pillow build".
    """
    target = (value or 'jpeg').strip().lower()
    if target == 'jpg':
        target = 'jpeg'
    available = available_output_formats()
    if target not in available:
        allowed = ', '.join(available)
        if target in FORMATS:
            raise ValueError(
                f"Conversion target {value!r} is not available in this Pillow "
                f"build (missing codec). Available targets: {allowed}.")
        raise ValueError(
            f"Unsupported convert_to target {value!r}. "
            f"Available targets: {allowed}.")
    return target
