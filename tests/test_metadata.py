#!/usr/bin/env python3
from PIL import Image

from optimize_images.api import ImageMetadata, inspect_image


def test_jpeg_metadata_and_exif(tmp_path):
    path = tmp_path / "photo.jpg"
    img = Image.new("RGB", (800, 600), (120, 80, 40))
    exif = img.getexif()
    exif[271] = "ACME"        # Make (main IFD)
    exif[272] = "CoolCam"     # Model (main IFD)
    sub = exif.get_ifd(0x8769)
    sub[0x829D] = 8.0         # FNumber (Exif sub-IFD)
    sub[0x8827] = 200         # ISOSpeedRatings (Exif sub-IFD)
    sub[0x920A] = 50.0        # FocalLength (Exif sub-IFD)
    exif[0x8769] = sub
    img.save(path, "JPEG", progressive=True, quality=80, exif=exif)

    meta = inspect_image(str(path))
    assert isinstance(meta, ImageMetadata)
    assert meta.image_format == "JPEG"
    assert (meta.width, meta.height) == (800, 600)
    assert meta.mode == "RGB"
    assert meta.has_alpha is False
    assert meta.is_progressive is True
    assert meta.is_interlaced is None      # not a PNG
    assert meta.exif["image"].get("Make") == "ACME"
    assert meta.exif["image"].get("Model") == "CoolCam"
    # sub-IFD tags must land in the "camera" section, not be lost
    assert meta.exif["camera"].get("FNumber") == 8.0
    assert meta.exif["camera"].get("ISOSpeedRatings") == 200
    assert meta.exif["camera"].get("FocalLength") == 50.0
    # the bare sub-IFD pointer must not leak through
    assert all("ExifOffset" not in section for section in meta.exif.values())


def test_palette_png_metadata(tmp_path):
    path = tmp_path / "icon.png"
    img = Image.new("P", (64, 48))
    img.putpalette([0, 0, 0, 255, 255, 255] * 128)
    img.info["transparency"] = 0
    img.save(path, "PNG")

    meta = inspect_image(str(path))
    assert meta.image_format == "PNG"
    assert meta.mode == "P"
    assert meta.palette_colors == 256
    assert meta.has_alpha is True
    assert meta.is_progressive is None     # not a JPEG
    assert meta.exif == {}
    assert meta.is_animated is False


def test_icc_profile_description(tmp_path):
    from PIL import ImageCms
    path = tmp_path / "srgb.jpg"
    img = Image.new("RGB", (40, 30), (10, 20, 30))
    profile = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB"))
    img.save(path, "JPEG", icc_profile=profile.tobytes())

    meta = inspect_image(str(path))
    assert meta.has_icc_profile is True
    assert meta.icc_profile_description  # e.g. "sRGB built-in"

    plain = tmp_path / "plain.jpg"
    Image.new("RGB", (40, 30)).save(plain, "JPEG")
    assert inspect_image(str(plain)).icc_profile_description is None