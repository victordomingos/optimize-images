#!/usr/bin/env python3
# encoding: utf-8
"""
A little command-line interface (CLI) utility written in pure Python to help
you reduce the file size of images.

You must explicitly pass it a path to the source image file or to the
directory containing the image files to be processed. By default, it will go
through all of its subdirectories and try to optimize the images found. You
may however choose to process the specified directory only, without recursion.

Please note that the operation is done DESTRUCTIVELY, by replacing the
original files with the processed ones. You definitely should duplicate the
source file or folder before using this utility, in order to be able to
recover any eventual damaged files or any resulting images that don't have the
desired quality.

This application is intended to be pure Python, with no special dependencies
besides Pillow, therefore ensuring compatibility with a wide range of systems,
including iPhones and iPads running Pythonista 3. If you don't have the need
for such a strict dependency management, you will certainly be better served
by any several other image optimization utilities that are based on some well
known external binaries.

© 2018 Victor Domingos (MIT License)
"""
import os
import re
import shutil
import platform
import concurrent.futures

import piexif

from argparse import ArgumentParser
from PIL import Image, ImageFile
from timeit import default_timer as timer
from typing import Iterable, NamedTuple, Tuple, NewType, Union

from optimize_images.constants import *


ImageType = NewType('ImageType', Image)
PPoolExType = NewType('PPoolExType', concurrent.futures.ProcessPoolExecutor)
TPoolExType = NewType('PPoolExType', concurrent.futures.ThreadPoolExecutor)


class Task(NamedTuple):
    src_path: str
    quality: int
    reduce_colors: bool
    max_colors: int
    max_w: int
    max_h: int
    keep_exif: bool
    conv_big: bool
    force_del: bool
    bg_color: Tuple[int, int, int]


class TaskResult(NamedTuple):
    img: str
    orig_format: str
    result_format: str
    orig_mode: str
    result_mode: str
    orig_colors: int
    final_colors: int
    orig_size: int
    final_size: int
    was_optimized: bool
    was_downsized: bool
    had_exif: bool
    has_exif: bool


def adjust_for_platform() -> Tuple[int, Union[TPoolExType, PPoolExType], int]:
    if platform.system() == 'Darwin':
        if platform.machine().startswith('iPad'):
            device = "iPad"
        elif platform.machine().startswith('iP'):
            device = "iPhone"
        else:
            device = "mac"
    else:
        device = "other"

    if device in ("iPad", "iPhone"):
        # Adapt for smaller screen sizes in iPhone and iPod touch
        import ui
        import console
        console.clear()
        if device == 'iPad':
            font_size = IPAD_FONT_SIZE
        else:
            font_size = IPHONE_FONT_SIZE
        console.set_font(IOS_FONT, font_size)
        screen_width = ui.get_screen_size().width
        char_width = ui.measure_string('.', font=(IOS_FONT, font_size)).width
        line_width = int(screen_width / char_width - 1.5) - 1
        pool_ex = concurrent.futures.ThreadPoolExecutor
        workers = IOS_WORKERS
    else:
        line_width = shutil.get_terminal_size((80, 24)).columns
        pool_ex = concurrent.futures.ProcessPoolExecutor
        from multiprocessing import cpu_count
        workers = cpu_count() + 1
    return line_width, pool_ex, workers


def get_args():
    desc = "A command-line utility written in pure Python to reduce the file " \
           "size of images. You must explicitly pass it a path to the image " \
           "file or to the directory containing the image files to be " \
           "processed. Please note that the operation is done DESTRUCTIVELY, " \
           "by replacing the original files with the processed ones. You " \
           "definitely should duplicate the original file or folder before " \
           "using this utility, in order to be able to recover any damaged " \
           "files or any resulting images that don't have the desired quality."
    parser = ArgumentParser(description=desc)

    path_help = "The path to the image file or to the folder containing the " \
                "images to be optimized. By default, it will try to process " \
                "any images found in all of its subdirectories."
    parser.add_argument('path', nargs="?", type=str, help=path_help)

    parser.add_argument('-v', '--version', action='version',
                        version=__import__('optimize_images').__version__)

    sf_help = "Display the list of image formats currently supported by this application."
    parser.add_argument('-sf', '--supported-formats',
                        action='store_true', help=sf_help)

    parser.add_argument('-nr', '--no-recursion', action='store_true',
                        help="Don't recurse through subdirectories.")

    size_msg = "These options will be applied individually to each " \
               "image being processed. Any image that has a dimension " \
               "exceeding a specified value will be downsized as the first " \
               "optimization step. The resizing will not take effect if, " \
               "after the whole optimization process, the resulting file " \
               "size isn't any smaller than the original. These options are " \
               "disabled by default."
    size_group = parser.add_argument_group(
        'Image resizing options', description=size_msg)

    mw_help = "The maximum width (in pixels)."
    size_group.add_argument(
        '-mw', "--max-width", type=int, default=0, help=mw_help)

    mh_help = "The maximum height (in pixels)."
    size_group.add_argument(
        '-mh', "--max-height", type=int, default=0, help=mh_help)

    jpg_msg = 'The following options apply only to JPEG image files.'
    jpg_group = parser.add_argument_group(
        'JPEG specific options', description=jpg_msg)

    q_help = "The quality for JPEG files (an integer value, between 1 and " \
             "100). A lower value will reduce the image quality and the " \
             "file size. The default value is 70."
    jpg_group.add_argument(
        '-q', "--quality", type=int, default=DEFAULT_QUALITY, help=q_help)

    jpg_group.add_argument(
        '-ke',
        "--keep-exif",
        action='store_true',
        help="Keep image EXIF data (by default, EXIF data is discarded).")

    png_msg = 'The following options apply only to PNG image files.'
    png_group = parser.add_argument_group(
        'PNG specific options', description=png_msg)

    rc_help = "Reduce colors (PNG) using an adaptive color palette with " \
              "dithering. This option can have a big impact on file size, " \
              "but please note that will also affect image quality."
    png_group.add_argument(
        '-rc', "--reduce-colors", action='store_true', help=rc_help)
    mc_help = "The maximum number of colors for PNG images when using " \
              "the reduce colors (-rc) option (an integer value, between 0 " \
              "and 255). The default is 255."
    png_group.add_argument(
        '-mc', "--max-colors", type=int, default=256, help=mc_help)

    bg_help = "The background color to use when doing operations that remove " \
              "transparency, like reducing colors or converting from PNG to " \
              "JPEG (3 integer values, separated by spaces, between 0 and 255 for " \
              "Red, Green and Blue, e.g.: '255 0 0' for a pure red color). If " \
              "ommited, it will default to a white background white (255 255 255)."
    png_group.add_argument(
        '-bg', "--bg-color", type=int, nargs=3, help=bg_help)

    hbg_help = "The background color (in hexadecimal, HTML style) to use when " \
               "doing operations that remove transparency, like reducing colors " \
               "or converting from PNG to JPEG E.g.: '00FF00' for a pure green " \
               "color. If ommited, it will default to a white background white " \
               "(FFFFFF)."
    png_group.add_argument('-hbg', "--hex-bg-color", type=str, help=hbg_help)

    cb_help = "Automatically convert to JPEG format any big PNG images that " \
              "have with a large number of colors (presumably a photo or " \
              "photo-like image). It uses an algorithm to determine whether " \
              "it is a good idea to convert to JPG and automatically decide " \
              "about it. By default, when using this option, the original PNG " \
              "files will remain untouched and will be kept alongside the " \
              "optimized JPG images in their original folders. IMPORTANT: " \
              "IF A JPEG WITH THE SAME NAME ALREADY EXISTS, IT WILL BE " \
              "REPLACED BY THE JPEG FILE RESULTING FROM THIS CONVERTION."
    png_group.add_argument(
        '-cb', "--convert_big", action='store_true', help=cb_help)

    fd_help = "Force the deletion of the original PNG file when using " \
              "automatic convertion to JPEG."
    png_group.add_argument(
        '-fd', "--force-delete", action='store_true', help=fd_help)

    args = parser.parse_args()
    recursive = not args.no_recursion
    quality = args.quality

    if args.supported_formats:
        formats = ', '.join(SUPPORTED_FORMATS).strip().upper()
        msg = "These are the image formats currently supported (please " \
              "note that any files without one of these file extensions " \
              "will be ignored):"
        msg = f"\n{msg} {formats}\n\n"
        parser.exit(status=0, message=msg)

    if args.path:
        src_path = os.path.expanduser(args.path)
    else:
        msg = "\nPlease specify the path of the image or folder to process.\n\n"
        parser.exit(status=0, message=msg)

    if quality > 100 or quality < 1:
        msg = "\nPlease specify an integer quality value between 1 and 100.\n\n"
        parser.exit(status=0, message=msg)

    if args.max_width < 0 or args.max_height < 0:
        msg = "\nPlease specify image dimensions as positive integers.\n\n"
        parser.exit(status=0, message=msg)

    if args.bg_color and args.hex_bg_color:
        msg = "\nBackground color should be entered only once.\n\n"
        parser.exit(status=0, message=msg)
    elif not args.bg_color and not args.hex_bg_color:
        # By default, apply a white background
        bg_color = (255, 255, 255)
    elif args.bg_color:
        bg_color = tuple(args.bg_color)
    else:
        # Check if hexadecimal is in the expected format
        if not re.search(r'(?:[0-9a-fA-F]{3}){1,2}$', args.hex_bg_color):
            msg = "\nHexadecimal background color was not entered in the correct " \
                  "format. Please follow these examples:\n\nWhite: FFFFFF" \
                  "\nBlack: 000000\nPure Red: FF0000\n\n"
            parser.exit(status=0, message=msg)
        # convert hex to a tuple of integers (RGB)
        bg_color = tuple(
            int(args.hex_bg_color[i:i + 2], 16) for i in (0, 2, 4))

    if min(bg_color) < 0 or max(bg_color) > 255:
        msg = "\nBackground color should be entered as a sequence of 3 " \
              "integer numbers between 0 and 255 (values for Red, Green and " \
              "Blue components) separated by spaces. For instance, for a " \
              "bright red you can use: '-bg 255 0 0' or '-hbg #FF0000'.\n\n"
        parser.exit(status=0, message=msg)

    return src_path, recursive, quality, args.reduce_colors, args.max_colors, \
           args.max_width, args.max_height, args.keep_exif, args.convert_big, \
           args.force_delete, bg_color


def human(number: int, suffix='B') -> str:
    """Return a human readable memory size in a string.

    Initially written by Fred Cirera, modified and shared by Sridhar Ratnakumar
    (https://stackoverflow.com/a/1094933/6167478), edited by Victor Domingos.
    """
    for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
        if abs(number) < 1024.0:
            return f"{number:3.1f} {unit}{suffix}"
        number = number / 1024.0
    return f"{number:.1f}{'Yi'}{suffix}"


def search_images(dirpath: str, recursive: bool) -> Iterable[str]:
    if recursive:
        for root, dirs, files in os.walk(dirpath):
            for f in files:
                if not os.path.isfile(os.path.join(root, f)):
                    continue
                extension = os.path.splitext(f)[1][1:]
                if extension.lower() in SUPPORTED_FORMATS:
                    yield os.path.join(root, f)
    else:
        with os.scandir(dirpath) as directory:
            for f in directory:
                if not os.path.isfile(os.path.normpath(f)):
                    continue
                extension = os.path.splitext(f)[1][1:]
                if extension.lower() in SUPPORTED_FORMATS:
                    yield os.path.normpath(f)


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


def show_file_status(r: TaskResult, line_width: int):
    if r.was_optimized:
        short_img = r.img[-(line_width - 17):].ljust(line_width - 17)
        percent = 100 - (r.final_size / r.orig_size * 100)
        h_orig = human(r.orig_size)
        h_final = human(r.final_size)

        orig_format = r.orig_format.replace('JPEG', 'JPG')
        result_format = r.result_format.replace('JPEG', 'JPG')

        if r.orig_mode == "P":
            o_colors = f"{r.orig_colors}"
        else:
            o_colors = ""

        if r.result_mode == "P":
            colors = f"{r.final_colors}"
        else:
            colors = ""

        exif_str1 = 'ℹ️ ' if r.had_exif else ''
        exif_str2 = 'ℹ️ ' if r.has_exif else ''
        downstr = '⤵ ' if r.was_downsized else ''
        line1 = f'\n✅  [OPTIMIZED] {short_img}\n'
        line2 = f'    {exif_str1}{orig_format}/{r.orig_mode}{o_colors}: {h_orig}  ->  {downstr}{exif_str2}{result_format}/{r.result_mode}{colors}: {h_final} 🔻 {percent:.1f}%'
        img_status = line1 + line2
    else:
        short_img = r.img[-(line_width - 15):].ljust(line_width - 15)
        img_status = f'\n🔴  [SKIPPED] {short_img}'
    print(img_status, end='')


def show_final_report(found_files: int,
                      optimized_files: int,
                      src_size: int,
                      bytes_saved: int,
                      time_passed: float):
    fps = found_files / time_passed

    if bytes_saved:
        average = bytes_saved / optimized_files
        percent = bytes_saved / src_size * 100
    else:
        average = 0
        percent = 0

    print(f"\n{40*'-'}\n")
    print(
        f"   Processed {found_files} files ({human(src_size)}) in {time_passed:.1f}s ({fps:.1f} f/s)."
    )
    print(f"   Optimized {optimized_files} files.")
    print(f"   Average savings: {human(average)} per optimized file")
    print(f"   Total space saved: {human(bytes_saved)} / {percent:.1f}%\n")


def main():
    appstart = timer()
    line_width, our_pool_executor, workers = adjust_for_platform()
    src_path, recursive, quality, reduce_colors, max_colors, max_w, max_h, keep_exif, conv_big, force_del, bg_color = get_args(
    )
    found_files = 0
    optimized_files = 0
    total_src_size = 0
    total_bytes_saved = 0

    # Optimize all images in a directory
    if os.path.isdir(src_path):
        if recursive:
            recursion_txt = "Recursively searching"
        else:
            recursion_txt = "Searching"
        exif_txt = '(keeping exif data) ' if keep_exif else ''

        print(
            f"\n{recursion_txt} and optimizing image files {exif_txt}in:\n{src_path}\n"
        )

        tasks = (Task(img_path, quality, reduce_colors, max_colors, max_w,
                      max_h, keep_exif, conv_big, force_del, bg_color)
                 for img_path in search_images(src_path, recursive=recursive))

        with our_pool_executor(max_workers=workers) as executor:
            for r in executor.map(do_optimization, tasks):
                found_files += 1
                total_src_size += r.orig_size
                if r.was_optimized:
                    optimized_files += 1
                    total_bytes_saved = total_bytes_saved + (
                            r.orig_size - r.final_size)
                show_file_status(r, line_width)

    # Optimize a single image
    elif os.path.isfile(src_path):
        found_files += 1

        img_task = Task(src_path, quality, reduce_colors, max_colors, max_w,
                        max_h, keep_exif, conv_big, force_del, bg_color)

        r = do_optimization(img_task)
        total_src_size = r.orig_size
        if r.was_optimized:
            optimized_files = 1
            total_bytes_saved = total_bytes_saved + (
                    r.orig_size - r.final_size)
        show_file_status(r, line_width)
    else:
        print(
            "No image files were found. Please enter a valid path to the "
            "image file or the folder containing any images to be processed.")
        exit()

    if found_files:
        time_passed = timer() - appstart
        show_final_report(found_files, optimized_files, total_src_size,
                          total_bytes_saved, time_passed)
    else:
        print(
            "No supported image files were found in the specified directory.\n")


if __name__ == "__main__":
    main()
