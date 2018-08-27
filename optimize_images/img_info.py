# encoding: utf-8
import os

from io import BytesIO

try:
    from PIL import Image, ImageFile
except ImportError:
    msg = 'This application requires Pillow to be installed. Please, install it first.'
    raise ImportError(msg)

from optimize_images.img_aux_processing import downsize_img
from optimize_images.constants import MIN_BIG_IMG_SIZE, MIN_BIG_IMG_AREA


def is_big_png_photo(src_path: str) -> bool:
    """Try to determine if a given image if a big photo in PNG format

    Expects a path to a PNG image file. Returns True if the image is a PNG
    with an area bigger than MIN_BIG_IMG_AREA pixels that when resized to 1600
    pixels (wide or high) converts to a JPEG bigger than MIN_BIG_IMG_SIZE.
    Returns False otherwise.

    Inspired by an idea first presented by Stephen Arthur
    (https://engineeringblog.yelp.com/2017/06/making-photos-smaller.html)
    """
    img = Image.open(src_path)
    orig_format = img.format
    orig_mode = img.mode

    if orig_format != 'PNG' or orig_mode in ['P', 'L', 'LA']:
        return False

    w, h = img.size
    if (w * h) >= MIN_BIG_IMG_AREA:
        unique_colors = {img.getpixel((x, y)) for x in range(w) for y in range(h)}
        if len(unique_colors) > 2 ** 16:
            img = img.convert("RGB")
            if w > h:
                img, status = downsize_img(img, 1600, 0)
            else:
                img, status = downsize_img(img, 0, 1600)

            tempfile = BytesIO()
            try:
                img.save(tempfile, quality=80, format="JPEG")
            except IOError:
                ImageFile.MAXBLOCK = img.size[0] * img.size[1]
                img.save(tempfile, quality=80, format="JPEG")

            final_size = tempfile.getbuffer().nbytes
            return final_size > MIN_BIG_IMG_SIZE

    return False
