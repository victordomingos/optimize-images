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
import shutil
import platform
import concurrent.futures

from argparse import ArgumentParser
from PIL import Image, ImageFile
from timeit import default_timer as timer
from typing import Tuple, Iterable

SUPPORTED_FORMATS = ['png', 'jpg', 'jpeg', 'gif']


def adjust_for_platform():
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
            font = ("Menlo", 15)
        else:
            font = ("Menlo", 10)
        console.set_font(*font)
        screen_width = ui.get_screen_size().width
        char_width = ui.measure_string('.',font=font).width
        line_width = int(screen_width / char_width-1.5)
        pool_ex = concurrent.futures.ThreadPoolExecutor
        workers = 2
    else:
        line_width, _ = shutil.get_terminal_size((80, 24))
        pool_ex = concurrent.futures.ProcessPoolExecutor
        from multiprocessing import cpu_count
        workers = cpu_count() + 1
    return line_width, pool_ex, workers


def get_args(*args):
    parser = ArgumentParser(description=
                            "A command-line interface (CLI) utility written in pure Python to help you reduce the file"
                            "size of images. You must explicitly pass it a path to the source image file or to the "
                            "directory containing the image files to be processed. Please note that the operation "
                            "is done DESTRUCTIVELY, by replacing the original files with the processed ones. You "
                            "definitely should duplicate the source file or folder before using this utility, in order "
                            "to be able to recover any eventual damaged files or any resulting images that don't have "
                            "the desired quality.")

    path_help = "The path to the image file or to the folder containing the " \
                "images to be optimized. By default, it will go through all " \
                "of its subdirectories and try to optimize the images found. "

    parser.add_argument('path',
                        nargs="?",
                        type=str,
                        help=path_help)

    parser.add_argument('-nr', "--no-recursion",
                        action='store_true',
                        help="Don't recurse through subdirectories.")
    args = parser.parse_args()
    src_path = os.path.expanduser(args.path)
    recursive = not args.no_recursion

    if not src_path:
        parser.exit(status=0, message="\nPlease specify the path of the image or folder to process.\n\n")

    return src_path, recursive


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


def do_optimization(image_file: str) -> Tuple[str, int, int, bool]:
    folder, filename = os.path.split(image_file)
    temp_file_path = os.path.join(folder + "/~temp~" + filename)

    img = Image.open(image_file)
    img_format = img.format

    # Remove EXIF data
    data = list(img.getdata())
    no_exif_img = Image.new(img.mode, img.size)
    no_exif_img.putdata(data)

    try:
        no_exif_img.save(temp_file_path,
                         quality=70,
                         optimize=True,
                         progressive=True,
                         format=img_format)
    except IOError:
        ImageFile.MAXBLOCK = no_exif_img.size[0] * no_exif_img.size[1]
        no_exif_img.save(temp_file_path,
                         quality=70,
                         optimize=True,
                         progressive=True,
                         format=img_format)

    orig_size = os.path.getsize(image_file)
    final_size = os.path.getsize(temp_file_path)

    # Only replace the original file if compression did save significant space
    if orig_size - final_size > 99:  # Minimal number of saved bytes
        shutil.move(temp_file_path, os.path.expanduser(image_file))
        was_optimized = True
    else:
        final_size = orig_size
        was_optimized = False
        try:
            os.remove(temp_file_path)
        except OSError:
            pass
    return image_file, orig_size, final_size, was_optimized


def show_file_status(img: str, original: int, final: int, was_optimized: bool, line_width: int):
    if was_optimized:
        short_img = img[-(line_width - 17):].ljust(line_width - 17)
        percent = 100 - (final / original * 100)
        line1 = f'\n✅  [OPTIMIZED] {short_img}\n'
        line2 = f'     {human(original)} -> {human(final)} 🔻 {percent:.1f}%'
        img_status = line1 + line2
    else:
        short_img = img[-(line_width - 15):].ljust(line_width - 15)
        img_status = f'\n🔴  [SKIPPED] {short_img}'
    print(img_status, end='')


def show_final_report(found_files: int, optimized_files: int, src_size: int, bytes_saved: int, time_passed: float):
    fps = found_files / time_passed

    if bytes_saved:
        average = bytes_saved / optimized_files
        percent = bytes_saved / src_size * 100
    else:
        average = 0
        percent = 0

    print(f"\n{40*'-'}\n")
    print(
        f"   Processed {found_files} files ({human(src_size)}) in {time_passed:.1f}s ({fps:.1f} f/s).")
    print(f"   Optimized {optimized_files} files.")
    print(f"   Average savings: {human(average)} per optimized file")
    print(f"   Total space saved: {human(bytes_saved)} / {percent:.1f}%\n")


def main(*args):
    appstart = timer()
    line_width, ourPoolExecutor, workers = adjust_for_platform()
    src_path, recursive = get_args()

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
        print(f"\n{recursion_txt} and optimizing image files in:\n{src_path}\n")

        images = (i for i in search_images(src_path, recursive=recursive))
        with ourPoolExecutor(max_workers=workers) as executor:
            for img, orig_size, final_size, was_optimized \
                    in executor.map(do_optimization, images):
                found_files += 1
                total_src_size += orig_size
                if was_optimized:
                    optimized_files += 1
                    total_bytes_saved = total_bytes_saved + (orig_size - final_size)
                show_file_status(img, orig_size, final_size, was_optimized, line_width)

    # Optimize a single image
    elif os.path.isfile(src_path):
        found_files += 1
        img, orig_size, final_size, was_optimized = do_optimization(src_path)
        if was_optimized:
            optimized_files += 1
            total_bytes_saved = total_bytes_saved + (orig_size - final_size)
        show_file_status(img, orig_size, final_size, was_optimized, line_width)

    else:
        print("No image files were found. Please enter a valid path to the "
              "image file or the folder containing any images to be processed.")
        exit()

    if found_files:
        time_passed = timer() - appstart
        show_final_report(found_files, optimized_files, total_src_size, total_bytes_saved, time_passed)
    else:
        print("No supported image files were found in the specified directory.\n")


if __name__ == "__main__":
    main()
