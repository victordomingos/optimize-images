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

© 2019 Victor Domingos (MIT License)
"""
import os

try:
    from PIL import Image
except ImportError:
    print('\n    This application requires Pillow to be installed. Please, install it first.\n')
    exit()

from timeit import default_timer as timer

from optimize_images.file_utils import search_images
from optimize_images.data_structures import Task, TaskResult
from optimize_images.platforms import adjust_for_platform, IconGenerator
from optimize_images.argument_parser import get_args
from optimize_images.reporting import show_file_status, show_final_report
from optimize_images.img_optimize_png import optimize_png
from optimize_images.img_optimize_jpg import optimize_jpg


def do_optimization(t: Task) -> TaskResult:
    """ Try to reduce file size of an image.

    Expects a Task object containing all the parameters for the image processing.

    The actual processing is done by the corresponding function,
    according to the detected image format.

    :param t: A Task object containing all the parameters for the image processing.
    :return: A TaskResult object containing information for single file report.
    """
    # TODO: Catch exceptions that may occur here.
    img = Image.open(t.src_path)

    # TODO: improve method of image format detection (what should happen if the
    #       file extension does not match the image content's format? Maybe we
    #       should skip unsupported formats?)
    if img.format.upper() == 'PNG':
        return optimize_png(t)
    # elif img.format.upper() == 'JPEG':
    else:
        return optimize_jpg(t)


def main():
    appstart = timer()
    line_width, our_pool_executor, workers = adjust_for_platform()
    (src_path, recursive, quality, remove_transparency, reduce_colors,
     max_colors, max_w, max_h, keep_exif, convert_all, conv_big, force_del, bg_color,
     grayscale, ignore_size_comparison, fast_mode) = get_args()
    found_files = 0
    optimized_files = 0
    total_src_size = 0
    total_bytes_saved = 0

    icons = IconGenerator()

    # Optimize all images in a directory
    if os.path.isdir(src_path):
        recursion_txt = 'Recursively searching' if recursive else 'Searching'
        opt_msg = 'and optimizing image files'
        exif_txt = '(keeping exif data) ' if keep_exif else ''
        print(f"\n{recursion_txt} {opt_msg} {exif_txt}in:\n{src_path}\n")

        tasks = (Task(img_path, quality, remove_transparency, reduce_colors,
                      max_colors, max_w, max_h, keep_exif, convert_all, conv_big,
                      force_del, bg_color, grayscale, ignore_size_comparison, fast_mode)
                 for img_path in search_images(src_path, recursive=recursive)
                 if '~temp~' not in img_path)

        with our_pool_executor(max_workers=workers) as executor:
            for r in executor.map(do_optimization, tasks):
                found_files += 1
                total_src_size += r.orig_size
                if r.was_optimized:
                    optimized_files += 1
                    total_bytes_saved += r.orig_size - r.final_size
                show_file_status(r, line_width, icons)

    # Optimize a single image
    elif os.path.isfile(src_path) and '~temp~' not in src_path:
        found_files += 1

        img_task = Task(src_path, quality, remove_transparency, reduce_colors,
                        max_colors, max_w, max_h, keep_exif, convert_all, conv_big,
                        force_del, bg_color, grayscale, ignore_size_comparison, fast_mode)

        r = do_optimization(img_task)
        total_src_size = r.orig_size
        if r.was_optimized:
            optimized_files = 1
            total_bytes_saved = r.orig_size - r.final_size
        show_file_status(r, line_width, icons)
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
        print("No supported image files were found in the specified directory.\n")


if __name__ == "__main__":
    main()
