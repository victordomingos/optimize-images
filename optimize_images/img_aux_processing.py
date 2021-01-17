# encoding: utf-8
import os
from io import BytesIO
from typing import Tuple

from PIL import Image

from .constants import DEFAULT_BG_COLOR
from .reporting import show_img_exception


class Palette:
    def __init__(self):
        self.palette = []

    def add(self, red, green, blue):
        # map rgb tuple to colour index
        rgb = red, green, blue
        try:
            return self.palette.index(rgb)
        except ValueError as vex:
            i = len(self.palette)
            if i >= 256:
                raise RuntimeError("all palette entries are used") from vex
            self.palette.append(rgb)
            return i

    def get_palette(self):
        # return flattened palette
        palette = []
        for red, green, blue in self.palette:
            palette = palette + [red, green, blue]
        return palette


def remove_transparency(
        img: Image.Image,
        bg_color: Tuple[int, int, int] = DEFAULT_BG_COLOR) -> Image.Image:
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


def downsize_img(img: Image.Image,
                 max_width: int,
                 max_height: int) -> Tuple[Image.Image, bool]:
    """ Reduce the size of an image to the indicated maximum dimensions

    This function takes a PIL.Image object and integer values for the maximum
    allowed width and height (a zero value means no maximum constraint),
    calculates the size that meets those constraints and resizes the image. The
    resize is done in place, changing the original object. Returns a boolean
    indicating if the image was changed.
    """
    width, height = img.size
    # Assume 0 as current size
    if not max_width:
        max_width = width
    if not max_height:
        max_height = height

    if (max_width, max_height) == (width, height):  # If no changes, do nothing
        return img, False

    img.thumbnail((max_width, max_height), resample=Image.LANCZOS)
    return img, True


def do_reduce_colors(img: Image.Image,
                     max_colors: int) -> Tuple[Image.Image, int, int]:
    """ Reduce the number of colors of an Image object

    It takes a PIL image object and tries to reduce the total number of colors,
    converting it to an indexed color (mode P) image. If the input image is in
    mode 1, it cannot be further reduced, so it's returned back with no
    changes.

    :param img: a PIL image in color (modes P, RGBA, RGB, CMYK, YCbCr, LAB or HSV)
    :param max_colors: an integer indicating the maximum number of colors allowed.
    :return: a PIL image in mode P (or mode 1, as stated above), an integer
             indicating the original number of colors (0 if source is not a
             mode P or mode 1 image) and an integer stating the resulting
             number of colors.
    """
    orig_mode = img.mode

    if orig_mode == "1":
        return img, 2, 2

    colors = img.getcolors()
    if colors:
        orig_colors = len(colors)
    else:
        orig_colors = 0

    # Intermediate conversion steps when needed
    if orig_mode in ["CMYK", "YCbCr", "LAB", "HSV"]:
        img = img.convert("RGB")
    elif orig_mode == "LA":
        img = img.convert("RGBA")

    # Actual color reduction happening here
    if orig_mode in ["RGB", "L"]:
        palette = Image.ADAPTIVE
    elif orig_mode == "RGBA":
        palette = Image.ADAPTIVE
        transparent = Image.new("RGBA", img.size, (0, 0, 0, 0))
        # blend with transparent image using own alpha
        img = Image.composite(img, transparent, img)
    elif orig_mode == "P":
        palette = img.getpalette()
        img = img.convert("RGBA")
        width, height = img.size
        alpha_layer = Image.new("L", img.size)
        for x in range(width):
            for y in range(height):
                _, _, _, alpha = img.getpixel((x, y))
                alpha_layer.putpixel((x, y), alpha)
        img.putalpha(alpha_layer)
    else:
        return img, 0, 0

    img = img.convert("P", palette=palette, colors=max_colors)
    return img, orig_colors, len(img.getcolors())


def make_grayscale(img: Image.Image) -> Image.Image:
    """ Convert an Image to grayscale

    :param img: a PIL image in color (modes P, RGBA, RGB, CMYK, YCbCr, LAB or HSV)
    :return: a PIL image object in modes P, L or RGBA, if converted, or the
             original Image object in case no conversion is done.
    """
    orig_mode = img.mode

    if orig_mode in ["RGB", "CMYK", "YCbCr", "LAB", "HSV"]:
        return img.convert("L")
    elif orig_mode == "RGBA":
        return img.convert("LA").convert("RGBA")
    elif orig_mode == "P":
        # Using ITU-R 601-2 luma transform:  L = R * 299/1000 + G * 587/1000 + B * 114/1000
        pal = img.getpalette()
        for i in range(len(pal) // 3):
            # Using ITU-R 601-2 luma transform
            gray = (pal[3 * i] * 299 + pal[3 * i + 1] * 587 + pal[3 * i + 2] * 114)
            gray = gray // 1000
            pal[3 * i: 3 * i + 3] = [gray, gray, gray]
        img.putpalette(pal)
        return img
    else:
        return img


def rebuild_palette(img: Image.Image) -> Tuple[Image.Image, int]:
    """ Rebuild the palette of a mode "P" PNG image

    It may allow for other tools, like PNGOUT and AdvPNG, to further reduce the
    size of some indexed PNG images. However, it it was already an optimized PNG,
    the resulting file size may in fact be bigger (which means optimize-images
    may discard it by default). You may also want to use it as an intermediate
    process, before doing a final optimization using those tools.

    :param img: a mode "P" PNG image
    :return: a tuple composed by a mode "P" PNG image object and an integer
             with the resulting number of colors
    """
    width, height = img.size
    img = img.convert("RGBA")
    new_palette = Palette()
    alpha_layer: Image.Image = Image.new("L", img.size)

    for x in range(width):
        for y in range(height):
            red, green, blue, alpha = img.getpixel((x, y))
            alpha_layer.putpixel((x, y), alpha)
            new_palette.add(red, green, blue)

    img.putalpha(alpha_layer)
    palette = new_palette.get_palette()
    num_colors = len(palette) // 3
    img = img.convert("P", palette=palette, colors=num_colors)
    return img, len(img.getcolors())


def save_compressed(src_path: str,
                    tmp_buffer: BytesIO,
                    compare_sizes: bool,
                    force_delete: bool = False,
                    output_path: str = '') -> Tuple[bool, int]:
    """ Check if there were any savings and save or discard temporary file.

        If the user used the option to ignore the file comparison, go ahead
        and replace the original file anyway.
    """
    final_size = tmp_buffer.getbuffer().nbytes
    orig_size: int = os.path.getsize(src_path)

    target_path = output_path if output_path else src_path

    if not compare_sizes or (final_size / orig_size < .99):
        tmp_buffer.seek(0)
        with open(target_path, 'wb') as file:
            file.write(tmp_buffer.getbuffer())

        was_optimized = True
        if force_delete:
            try:
                os.remove(src_path)
            except OSError as osex:
                details = 'Error while removing original file.'
                show_img_exception(osex, src_path, details)
    else:
        # Keep original file
        final_size = orig_size
        was_optimized = False

    return was_optimized, final_size
