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

    img.thumbnail((max_w, max_h), resample=Image.LANCZOS)
    return img, True


def do_reduce_colors(img: ImageType, max_colors: int) -> Tuple[ImageType, int, int]:
    orig_mode = img.mode

    if orig_mode == "1":
        return img, 2, 2
    colors = img.getcolors()
    if colors:
        orig_colors = len(colors)
    else:
        orig_colors = 0
    #print(f"DEBUG: {img.format}: {img.mode}/{orig_colors} - {img.size[0]}x{img.size[1]} ")

    if orig_mode in ["RGB", "L"]:
        palette = Image.ADAPTIVE
        final_colors = max_colors
    elif orig_mode == "RGBA":
        palette = Image.ADAPTIVE
        final_colors = max_colors
        transparent = Image.new("RGBA", img.size, (0, 0, 0, 0))
        # blend with transparent image using own alpha
        img = Image.composite(img, transparent, img)

    elif orig_mode == "P":
        orig_colors = len(img.getcolors())
        if orig_colors >= 256:
            palette = Image.ADAPTIVE
            final_colors = max_colors
        else:
            palette = img.getpalette()
            final_colors = orig_colors
    else:
        return img, 0, 0

    img = img.convert("P", palette=palette, colors=final_colors)
    return img, orig_colors, final_colors


def make_grayscale(img: ImageType) -> ImageType:
    orig_mode = img.mode

    if orig_mode in ["RGB", "CMYK", "YCbCr", "LAB", "HSV"]:
        return img.convert("L")
    elif orig_mode == "RGBA":
        return img.convert("LA").convert("RGBA")
        # #Alternative:
        #for i in range(img.size[0]):  # for every pixel:
        #    for j in range(img.size[1]):
        #        g = (pixels[i, j][0] * 299 + pixels[i, j][1] * 587 + pixels[i, j][2] * 114) // 1000
        #        pixels[i, j] = (g, g, g, pixels[i, j][3])
    elif orig_mode == "P":
        # Using ITU-R 601-2 luma transform:  L = R * 299/1000 + G * 587/1000 + B * 114/1000
        pal = img.getpalette()
        for i in range(len(pal) // 3):
            # Using ITU-R 601-2 luma transform
            g = (pal[3*i] * 299 + pal[3*i+1] * 587 + pal[3*i+2] * 114) // 1000
            pal[3*i: 3*i+3] = [g, g, g]
        img.putpalette(pal)
        return img
    else:
        return img

