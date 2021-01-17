# encoding: utf-8

from io import BytesIO

from PIL import Image, ImageFile

from .constants import MIN_BIG_IMG_SIZE, MIN_BIG_IMG_AREA
from .img_aux_processing import downsize_img


def is_big_png_photo(src_path: str) -> bool:
    """Try to determine if a given image if a big photo in PNG format

    Expects a path to a PNG image file. Returns True if the image is a PNG
    with an area bigger than MIN_BIG_IMG_AREA pixels that when resized to 1600
    pixels (wide or high) converts to a JPEG bigger than MIN_BIG_IMG_SIZE.
    Returns False otherwise.

    Inspired by an idea first presented by Stephen Arthur
    (https://engineeringblog.yelp.com/2017/06/making-photos-smaller.html)
    """
    with Image.open(src_path) as img:
        img: Image.Image
        orig_format: str = img.format
        orig_mode: str = img.mode

        if orig_format != 'PNG' or orig_mode in ['P', 'L', 'LA']:
            return False

        width, height = img.size
        if (width * height) >= MIN_BIG_IMG_AREA:
            unique_colors = {img.getpixel((x, y))
                             for x in range(width)
                             for y in range(height)}

            if len(unique_colors) > 2 ** 16:
                img = img.convert("RGB")
                if width > height:
                    img, _ = downsize_img(img, 1600, 0)
                else:
                    img, _ = downsize_img(img, 0, 1600)

                tempfile = BytesIO()
                try:
                    img.save(tempfile, quality=80, format="JPEG")
                except IOError:
                    ImageFile.MAXBLOCK = img.size[0] * img.size[1]
                    img.save(tempfile, quality=80, format="JPEG")

                final_size = tempfile.getbuffer().nbytes
                return final_size > MIN_BIG_IMG_SIZE

    return False
