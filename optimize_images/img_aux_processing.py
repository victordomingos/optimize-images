# encoding: utf-8
from typing import Tuple

from PIL import Image

from optimize_images.constants import DEFAULT_BG_COLOR
from optimize_images.data_structures import ImageType


def remove_transparency(img: ImageType,
                        bg_color=DEFAULT_BG_COLOR) -> ImageType:
    """Remove alpha transparency from PNG images

    Expects a PIL.Image object and returns an object of the same type with the
    changes applied.

    Special thanks to Yuji Tomita and Takahashi Shuuji
    (https://stackoverflow.com/a/33507138)
    """
    orig_image = img.convert('RGBA')
    background = Image.new('RGBA', orig_image.size, bg_color)
    return Image.alpha_composite(background, orig_image)


def downsize_img(img: ImageType, max_w: int,
                 max_h: int) -> Tuple[ImageType, bool]:
    """ Reduce the size of an image to the indicated maximum dimensions

    This function takes a PIL.Image object and integer values for the maximum
    allowed width and height (a zero value means no maximum constraint),
    calculates the size that meets those constraints and resizes the image. The
    resize is done in place, changing the original object. Returns a boolean
    indicating if the image was changed.
    """
    w, h = img.size

    # Don't upsize images, assume 0 as current size
    if max_w > w or max_w == 0:
        max_w = w
    if max_h > h or max_h == 0:
        max_h = h

    if (max_w, max_h) == (w, h):  # If no changes, do nothing
        return img, False
    else:  # Choose smaller size that fits in max_w and max_h
        width_a, height_a = max_w, int(round(h * max_w / w))
        width_b, height_b = int(round(max_h * w / h)), max_h

        if (width_a * height_a) < (width_b * height_b):
            max_w, max_h = width_a, height_a
        else:
            max_w, max_h = width_b, height_b

        img.thumbnail((max_w, max_h), resample=Image.LANCZOS)

        return img, True


def do_reduce_colors(img: ImageType,
                     max_colors: int) -> Tuple[ImageType, int, int]:
    # TODO - Try to reduce the number of colors without loosing transparency

    mode = "P"
    orig_mode = img.mode
    colors = img.getpalette()
    if colors:
        orig_colors = len(colors) // 3
    else:
        orig_colors = 0

    if orig_mode == "RGB":
        palette = Image.ADAPTIVE
        final_colors = max_colors
    elif orig_mode == "RGBA":
        palette = Image.ADAPTIVE
        final_colors = max_colors
        img = remove_transparency(img, DEFAULT_BG_COLOR)
    elif orig_mode == "P":
        colors = img.getpalette()
        orig_colors = len(colors) // 3
        if orig_colors >= 256:
            palette = Image.ADAPTIVE
            final_colors = max_colors
        else:
            palette = colors
            final_colors = orig_colors
    img = img.convert(mode, palette=palette, colors=final_colors)
    return img, orig_colors, final_colors
