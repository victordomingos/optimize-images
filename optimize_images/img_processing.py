# encoding: utf-8
import os
import shutil

import piexif

from PIL import Image, ImageFile
from typing import Tuple

from optimize_images.constants import *
from optimize_images.data_structures import Task, TaskResult
from optimize_images.data_structures import ImageType
from optimize_images.img_info import is_big_png_photo


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


def do_optimization(t: Task) -> TaskResult:
    """ Try to reduce file size of an image.

    Expects a Task object containing all the parameters for the image processing.

    If file reduction is successful, this function will replace the original
    file with the optimized version and return some report data (file path,
    image format, image color mode, original file size, resulting file size,
    and resulting status of the optimization.

    :param t: A Task object containing all the parameters for the image processing.
    :return: A TaskResult object containing information for single file report.
    """
    img = Image.open(t.src_path)
    orig_format = img.format
    orig_mode = img.mode

    folder, filename = os.path.split(t.src_path)
    temp_file_path = os.path.join(folder + "/~temp~" + filename)
    orig_size = os.path.getsize(t.src_path)
    if orig_mode == 'P':
        orig_colors = len(img.getpalette()) // 3
        final_colors = orig_colors
    else:
        orig_colors, final_colors = 0, 0

    if orig_format.upper() == 'PNG':
        had_exif = has_exif = False  # Currently no exif methods for PNG files
        if t.conv_big and is_big_png_photo(t.src_path):
            # convert to jpg format
            filename = os.path.splitext(os.path.basename(t.src_path))[0]
            conv_file_path = os.path.join(folder + "/" + filename + ".jpg")

            if t.max_w or t.max_h:
                img, was_downsized = downsize_img(img, t.max_w, t.max_h)
            else:
                was_downsized = False

            img = remove_transparency(img, t.bg_color)
            img = img.convert("RGB")

            try:
                img.save(
                    conv_file_path,
                    quality=t.quality,
                    optimize=True,
                    progressive=True,
                    format="JPEG")
            except IOError:
                ImageFile.MAXBLOCK = img.size[0] * img.size[1]
                img.save(
                    conv_file_path,
                    quality=t.quality,
                    optimize=True,
                    progressive=True,
                    format="JPEG")

            # Only save the converted file if conversion did save any space
            final_size = os.path.getsize(conv_file_path)
            if orig_size - final_size > 0:
                was_optimized = True
                if t.force_del:
                    try:
                        os.remove(t.src_path)
                    except OSError as e:
                        print(
                            "\nError while replacing original PNG with the new JPEG version.\n{e}\n"
                        )
            else:
                final_size = orig_size
                was_optimized = False
                try:
                    os.remove(conv_file_path)
                except OSError as e:
                    print(
                        "\nError while removing temporary JPEG converted file.\n{e}\n"
                    )

            result_format = "JPEG"
            return TaskResult(t.src_path, orig_format, result_format,
                              orig_mode, img.mode, orig_colors, final_colors,
                              orig_size, final_size, was_optimized,
                              was_downsized, had_exif, has_exif)

        # if PNG and user didn't ask for PNG to JPEG conversion, do this instead.
        else:
            result_format = "PNG"

            if t.max_w or t.max_h:
                img, was_downsized = downsize_img(img, t.max_w, t.max_h)
            else:
                was_downsized = False

            if t.reduce_colors:
                img, orig_colors, final_colors = do_reduce_colors(
                    img, t.max_colors)

            try:
                img.save(temp_file_path, optimize=True, format=result_format)
            except IOError:
                ImageFile.MAXBLOCK = img.size[0] * img.size[1]
                img.save(temp_file_path, optimize=True, format=result_format)

    # Doing regular JPEG processing here.
    else:
        result_format = "JPEG"
        try:
            had_exif = True if piexif.load(t.src_path)['Exif'] else False
        except:
            had_exif = False

        if t.max_w or t.max_h:
            img, was_downsized = downsize_img(img, t.max_w, t.max_h)
        else:
            was_downsized = False

        # only use progressive if file size is bigger
        use_progressive_jpg = orig_size > 10000
        try:
            img.save(
                temp_file_path,
                optimize=True,
                progressive=use_progressive_jpg,
                format=result_format)
        except IOError:
            ImageFile.MAXBLOCK = img.size[0] * img.size[1]
            img.save(
                temp_file_path,
                optimize=True,
                progressive=use_progressive_jpg,
                format=result_format)

        if t.keep_exif and had_exif:
            try:
                piexif.transplant(
                    os.path.expanduser(t.src_path), temp_file_path)
                has_exif = True
            except:
                has_exif = False
        else:
            has_exif = False

    final_size = os.path.getsize(temp_file_path)

    # Only replace the original file if compression did save any space
    if orig_size - final_size > 0:
        shutil.move(temp_file_path, os.path.expanduser(t.src_path))
        was_optimized = True
    else:
        final_size = orig_size
        was_optimized = False
        try:
            os.remove(temp_file_path)
        except OSError as e:
            print("\nError while removing temporary file.\n{e}\n")

    return TaskResult(t.src_path, orig_format, result_format, orig_mode,
                      img.mode, orig_colors, final_colors, orig_size,
                      final_size, was_optimized, was_downsized, had_exif,
                      has_exif)
