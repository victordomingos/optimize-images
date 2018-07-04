# encoding: utf-8
import os

from PIL import Image, ImageFile


def is_big_png_photo(src_path: str) -> bool:
    """Try to determine if a given image if a big photo in PNG format

    Expects a path to a PNG image file. Returns True if the image is a PNG
    with an area bigger than XXXX pixels that when resized to XXXXX pixels
    converts to a JPEG bigger than 300KB. Returns False otherwise.

    Inspired by an idea first presented by Stephen Arthur
    (https://engineeringblog.yelp.com/2017/06/making-photos-smaller.html)
    """
    img = Image.open(src_path)
    orig_format = img.format
    orig_mode = img.mode

    folder = os.path.split(src_path)[0]
    filename = os.path.splitext(os.path.basename(src_path))[0]
    temp_file_path = os.path.join(folder + "/~temp~" + filename + ".jpg")

    w, h = img.size

    if orig_format != 'PNG' or orig_mode == 'P':
        return False
    elif (w * h) < (1024 * 768):
        return False
    else:
        img = img.convert("RGB")
        if w > h:
            img, status = downsize_img(img, 1600, 0)
        else:
            img, status = downsize_img(img, 0, 1600)

        try:
            img.save(temp_file_path, quality=85, optimize=True,
                     progressive=True, format="JPEG")
        except IOError:
            ImageFile.MAXBLOCK = img.size[0] * img.size[1]
            img.save(temp_file_path, quality=85, optimize=True,
                     progressive=True, format="JPEG")

        final_size = os.path.getsize(temp_file_path)

        try:
            os.remove(temp_file_path)
        except OSError as e:
            print("\nError while removing temporary file.\n{e}\n")

        return (final_size > 300000)

