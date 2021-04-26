#!/usr/bin/env python3
# encoding: utf-8
"""
A command-line interface (CLI) utility written in pure Python to help you
reduce the file size of images.

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

Some aditional features can be added which require the presence of other
third-party packages that are not written in pure Python, but those packages and
the features depending on them should be treated as optional.

© 2021 Victor Domingos (MIT License)
"""
import concurrent.futures.process
import os
import sys

from optimize_images.exceptions import OIImagesNotFoundError, OIInvalidPathError
from optimize_images.exceptions import OIKeyboardInterrupt

try:
    from PIL import Image
except ImportError:
    print('\n    This application requires Pillow to be installed. '
          'Please, install it first.\n')
    sys.exit()

try:
    import piexif
except ImportError:
    print('\n    This application requires Piexif to be installed. '
          'Please, install it first.\n')
    sys.exit()

from timeit import default_timer as timer

from optimize_images.file_utils import search_images
from optimize_images.data_structures import Task
from optimize_images.do_optimization import do_optimization
from optimize_images.platforms import adjust_for_platform, IconGenerator
from optimize_images.argument_parser import get_args
from optimize_images.reporting import (show_file_status,
                                       show_final_report,
                                       show_img_exception)
from optimize_images.watch import watch_for_new_files


def optimize_batch(src_path, watch_dir, recursive, quality, remove_transparency,
                   reduce_colors, max_colors, max_w, max_h, keep_exif, convert_all,
                   conv_big, force_del, bg_color, grayscale,
                   ignore_size_comparison, fast_mode, jobs):
    appstart = timer()
    line_width, our_pool_executor, workers = adjust_for_platform()
    if jobs != 0:
        workers = jobs

    found_files = 0
    optimized_files = 0
    total_src_size = 0
    total_bytes_saved = 0

    if watch_dir:
        if not os.path.isdir(os.path.abspath(src_path)):
            msg = "\nPlease specify a valid path to an existing folder."
            raise OIInvalidPathError(msg)

        watch_task = Task(src_path, quality, remove_transparency, reduce_colors,
                          max_colors, max_w, max_h, keep_exif, convert_all,
                          conv_big, force_del, bg_color, grayscale,
                          ignore_size_comparison, fast_mode)

        watch_for_new_files(watch_task)
        return

    # Optimize all images in a directory
    elif os.path.isdir(src_path):
        icons = IconGenerator()
        recursion_txt = 'Recursively searching' if recursive else 'Searching'
        opt_msg = 'and optimizing image files'
        exif_txt = '(keeping exif data) ' if keep_exif else ''
        print(f"\n{recursion_txt} {opt_msg} {exif_txt}in:\n{src_path}\n")

        tasks = (Task(img_path, quality, remove_transparency, reduce_colors,
                      max_colors, max_w, max_h, keep_exif, convert_all, conv_big,
                      force_del, bg_color, grayscale, ignore_size_comparison, fast_mode)
                 for img_path in search_images(src_path, recursive=recursive))

        with our_pool_executor(max_workers=workers) as executor:
            current_img = ''
            try:
                for result in executor.map(do_optimization, tasks):
                    current_img = result.img
                    found_files += 1
                    total_src_size += result.orig_size
                    if result.was_optimized:
                        optimized_files += 1
                        total_bytes_saved += result.orig_size - result.final_size
                    show_file_status(result, line_width, icons)
            except concurrent.futures.process.BrokenProcessPool as bppex:
                show_img_exception(bppex, current_img)
            except KeyboardInterrupt:
                msg = "\b \n\n  == Operation was interrupted by the user. ==\n"
                raise OIKeyboardInterrupt(msg)

    # Optimize a single image
    elif os.path.isfile(src_path) and '~temp~' not in src_path:
        icons = IconGenerator()
        found_files += 1

        img_task = Task(src_path, quality, remove_transparency, reduce_colors,
                        max_colors, max_w, max_h, keep_exif, convert_all, conv_big,
                        force_del, bg_color, grayscale, ignore_size_comparison, fast_mode)

        result = do_optimization(img_task)
        total_src_size = result.orig_size
        if result.was_optimized:
            optimized_files = 1
            total_bytes_saved = result.orig_size - result.final_size
        show_file_status(result, line_width, icons)
    else:
        msg = "\nNo image files were found. Please enter a valid path to the " \
              "image file or the folder containing any images to be processed."
        raise OIImagesNotFoundError(msg)

    if found_files:
        time_passed = timer() - appstart
        show_final_report(found_files, optimized_files, total_src_size,
                          total_bytes_saved, time_passed)
    else:
        msg = "\nNo supported image files were found in the specified directory."
        raise OIImagesNotFoundError(msg)


def main():
    args = get_args()
    try:
        optimize_batch(*args)
    except (OIImagesNotFoundError, OIInvalidPathError, OIKeyboardInterrupt) as ex:
        print(ex.message)


if __name__ == "__main__":
    main()
