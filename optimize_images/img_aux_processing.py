# encoding: utf-8
from typing import Tuple
from PIL import Image
from collections import Counter

from optimize_images.constants import DEFAULT_BG_COLOR
from optimize_images.data_structures import ImageType


class Palette:
    def __init__(self):
        self.palette = []

    def add(self, r, g, b):
        # map rgb tuple to colour index
        rgb = r, g, b
        try:
            return self.palette.index(rgb)
        except:
            i = len(self.palette)
            if i >= 256:
                raise RuntimeError("all palette entries are used")
            self.palette.append(rgb)
            return i

    def get_palette(self):
        # return flattened palette
        palette = []
        for r, g, b in self.palette:
            palette = palette + [r, g, b]
        return palette


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
            palette = img.get_palette()
            final_colors = orig_colors
    else:
        return img, 0, 0

    img = img.convert("P", palette=palette, colors=final_colors)
    return img, orig_colors, final_colors


def remove_unused_colors(img):
    w, h = img.size
    count = Counter()
    for i in range(w):  # for every pixel:
        for y in range(h):

            color = pixels[i, j][3]
            count += color
    print(count)
    return img


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
        pal = img.get_palette()
        for i in range(len(pal) // 3):
            # Using ITU-R 601-2 luma transform
            g = (pal[3*i] * 299 + pal[3*i+1] * 587 + pal[3*i+2] * 114) // 1000
            pal[3*i: 3*i+3] = [g, g, g]
        img.putpalette(pal)
        img = remove_unused_colors(img)
        return img
    else:
        return img


def rebuild_palette(img: ImageType) -> ImageType:
    """ Rebuild the palette of a mode "P" PNG image

    It may allow for other tools, like PNGOUT and AdvPNG, to further reduce the
    size of some indexed PNG images. However, it it was already an optimized PNG,
    the resulting file size may in fact be bigger (which means optimize-images
    may discard it by default). You may use it as an intermediate process,
    before doing a final optimization using those tools.

    :param img: a mode "P" PNG image
    :return: a mode "P" PNG image
    """
    w, h = img.size
    img = img.convert("RGBA")
    new_palette = Palette()
    alpha_layer = Image.new("L", img.size)

    for x in range(w):
        for y in range(h):
            r, g, b, a = img.getpixel((x,y))
            new_palette.add(r, g, b)
            alpha_layer.putpixel((x,y), a)

    img.putalpha(alpha_layer)
    palette = new_palette.get_palette()
    img = img.convert("P", palette=palette, colors=len(palette) // 3)
    return img
