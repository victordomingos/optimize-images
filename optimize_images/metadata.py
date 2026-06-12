# encoding: utf-8
"""Read structured, presentation-neutral metadata from an image file.

This is the engine's source of truth about an image's intrinsic properties.
Values are returned raw - EXIF entries, for instance, are exactly what Pillow
decodes, keyed by their standard tag names - so any human-friendly labelling or
formatting is left to the caller (a GUI, a CLI, a report, ...).
"""
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

from PIL import ExifTags, Image


@dataclass(frozen=True)
class ImageMetadata:
    """Intrinsic properties of a single image, as read from the file.

    ``exif`` groups the metadata by its standardized IFD sections - ``image``
    (main IFD), ``camera`` (Exif sub-IFD) and ``gps`` - each a dict of raw
    values keyed by tag name; binary blobs (maker notes, embedded thumbnails)
    are omitted. Fields that do not apply to a given format are ``None``
    (e.g. ``is_progressive`` for a PNG).
    """
    path: str
    image_format: str  # e.g. "JPEG"; "" if unknown
    mode: str  # e.g. "RGB", "RGBA", "P"
    width: int
    height: int
    has_alpha: bool
    palette_colors: Optional[int] = None  # only for palette ("P") images
    is_progressive: Optional[bool] = None  # JPEG only
    is_interlaced: Optional[bool] = None  # PNG only
    n_frames: int = 1
    dpi: Optional[Tuple[float, float]] = None
    has_icc_profile: bool = False
    icc_profile_description: Optional[str] = None
    exif: Dict[str, Dict[str, object]] = field(default_factory=dict)

    @property
    def is_animated(self) -> bool:
        return self.n_frames > 1


def inspect_image(path: str) -> ImageMetadata:
    """Return :class:`ImageMetadata` for the image at *path*.

    The underlying Pillow/OS error is propagated if the file cannot be opened
    or is not a recognized image, so the caller decides how to react.
    """
    with Image.open(path) as img:
        return _inspect(path, img)


def _inspect(path: str, img) -> ImageMetadata:
    mode = img.mode
    image_format = img.format or ''
    has_alpha = ('A' in mode) or ('transparency' in img.info)

    palette_colors = None
    if mode in ('P', 'PA'):
        palette = img.getpalette()
        if palette:
            palette_colors = len(palette) // 3

    is_progressive = None
    if image_format == 'JPEG':
        is_progressive = bool(img.info.get('progressive')
                              or img.info.get('progression'))

    is_interlaced = None
    if image_format == 'PNG' and 'interlace' in img.info:
        is_interlaced = bool(img.info.get('interlace'))

    dpi = img.info.get('dpi')
    if dpi is not None:
        try:
            dpi = (float(dpi[0]), float(dpi[1]))
        except (TypeError, IndexError, ValueError):
            dpi = None

    icc_data = img.info.get('icc_profile')
    return ImageMetadata(
        path=path,
        image_format=image_format,
        mode=mode,
        width=img.width,
        height=img.height,
        has_alpha=has_alpha,
        palette_colors=palette_colors,
        is_progressive=is_progressive,
        is_interlaced=is_interlaced,
        n_frames=getattr(img, 'n_frames', 1),
        dpi=dpi,
        has_icc_profile=bool(icc_data),
        icc_profile_description=_read_icc_description(icc_data),
        exif=_read_exif(img),
    )


def _read_icc_description(icc_data) -> Optional[str]:
    """Return the embedded ICC profile's description (e.g. the profile name
    shown by color-managed apps, such as 'sRGB IEC61966-2.1'), if readable.
    """
    if not icc_data:
        return None
    try:
        import io
        from PIL import ImageCms
        profile = ImageCms.ImageCmsProfile(io.BytesIO(icc_data))
        description = ImageCms.getProfileDescription(profile).strip()
        return description or None
    except Exception:
        return None


# Tags that merely point to sub-IFDs (not real data): ExifOffset, GPSInfo,
# Interop and PrintIM.
_EXIF_POINTER_TAGS = {0x8769, 0x8825, 0xA005, 0xC4A5}


def _read_exif(img) -> Dict[str, Dict[str, object]]:
    """Return EXIF grouped by its standardized IFD sections.

    Keys (present only when non-empty), in order:
      ``image``  - the main/0th IFD (device and image-level tags);
      ``camera`` - the Exif sub-IFD (capture parameters: exposure, aperture,
                   ISO, focal length, lens, capture date, ...);
      ``gps``    - the GPS IFD.
    Pointer tags and binary blobs (maker notes, thumbnails) are dropped, and
    values are raw, so callers format and label sections as they wish.
    """
    try:
        exif = img.getexif()
    except Exception:
        return {}
    if not exif:
        return {}

    def collect(items, names):
        out: Dict[str, object] = {}
        for tag_id, value in items:
            if isinstance(value, bytes) or tag_id in _EXIF_POINTER_TAGS:
                continue
            out[names.get(tag_id, str(tag_id))] = value
        return out

    sections: Dict[str, Dict[str, object]] = {}
    image = collect(exif.items(), ExifTags.TAGS)
    if image:
        sections['image'] = image
    try:
        camera = collect(exif.get_ifd(0x8769).items(), ExifTags.TAGS)
        if camera:
            sections['camera'] = camera
    except Exception:
        pass
    try:
        gps = collect(exif.get_ifd(0x8825).items(), ExifTags.GPSTAGS)
        if gps:
            sections['gps'] = gps
    except Exception:
        pass
    return sections