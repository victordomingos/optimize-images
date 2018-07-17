# encoding: utf-8

from typing import Tuple

from PIL import Image

from optimize_images.constants import DEFAULT_BG_COLOR
from optimize_images.data_structures import ImageType


def remove_transparency(img: ImageType, bg_color=DEFAULT_BG_COLOR) -> ImageType:
    """Remove alpha transparency from PNG images

    Expects a PIL.Image object and returns an object of the same type with the
    changes applied.

    Special thanks to Yuji Tomita and Takahashi Shuuji
    (https://stackoverflow.com/a/33507138)
    """
    if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
        orig_image = img.convert('RGBA')
        background = Image.new('RGBA', orig_image.size, bg_color)
        img = Image.alpha_composite(background, orig_image)
        return img.convert("RGB")
    else:
        return img


def downsize_img(img: ImageType, max_w: int, max_h: int) -> Tuple[ImageType, bool]:
    """ Reduce the size of an image to the indicated maximum dimensions

    This function takes a PIL.Image object and integer values for the maximum
    allowed width and height (a zero value means no maximum constraint),
    calculates the size that meets those constraints and resizes the image. The
    resize is done in place, changing the original object. Returns a boolean
    indicating if the image was changed.
    """
    w, h = img.size
    # Assume 0 as current size
    if not max_w:
        max_w = w
    if not max_h:
        max_h = h

    if (max_w, max_h) == (w, h):  # If no changes, do nothing
        return img, False

    if img.mode == "P":
        p_mode = True
        img = img.convert("RBGA", dither=None)
    else:
        p_mode = False

    img.thumbnail((max_w, max_h), resample=Image.LANCZOS)
    if p_mode:
        img = img.convert("P",)
    return img, True


def do_reduce_colors(img: ImageType, max_colors: int) -> Tuple[ImageType, int, int]:
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
        transparent = Image.new("RGBA", img.size, (0, 0, 0, 0))
        # blend with transparent image using own alpha
        img = Image.composite(img, transparent, img)

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
