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

This application itself is intended to be pure Python, with no special
dependencies besides Pillow, therefore ensuring compatibility with a wide range
of systems. If you don't have the need for such a strict dependency management,
you will certainly be better served by any several other image optimization
utilities that are based on some well known external binaries.

Some aditional features can be added which require the presence of other
third-party packages that are not written in pure Python, but those packages and
the features depending on them should be treated as optional.

Note for developers integrating this package:

For programmatic use in third-party applications, please prefer the high-level
API in optimize_images.api (optimize_single_image / optimize_as_batch).

© 2026 Victor Domingos & contributers (MIT License)
"""
import concurrent.futures
import os
import sys
from timeit import default_timer as timer

from optimize_images.data_structures import Task
from optimize_images.do_optimization import do_optimization

from optimize_images.exceptions import OIImagesNotFoundError, OIInvalidPathError, OIKeyboardInterrupt
from optimize_images.exceptions import OIKeyboardInterrupt
from optimize_images.file_utils import search_images
from optimize_images.platforms import adjust_for_platform, IconGenerator
from optimize_images.reporting import human, show_file_status, show_final_report
from optimize_images.argument_parser import get_args

# Use only public API types
from optimize_images.api import (
    optimize_as_batch_stream,
    watch_directory,
    PublicBatchOptions,
)

def main():
    args = get_args()
    try:
        optimize_batch(*args)
    except (OIImagesNotFoundError, OIInvalidPathError, OIKeyboardInterrupt) as ex:
        print(ex.message)

def optimize_batch(src_path, watch_dir, recursive, quality, remove_transparency,
                   reduce_colors, max_colors, max_w, max_h, keep_exif, convert_all,
                   conv_big, force_del, bg_color, grayscale, ignore_size_comparison,
                   fast_mode, jobs, output_config, convert_to='jpeg',
                   webp_quality=80, webp_lossless=False, webp_method=6):
    appstart = timer()
    line_width, our_pool_executor, workers = adjust_for_platform()

    if jobs != 0:
        workers = jobs

    found_files = 0
    optimized_files = 0
    skipped_files = 0
    total_src_size = 0
    total_bytes_saved = 0

    # Build PublicBatchOptions for the public API
    options = PublicBatchOptions(
        src_path=src_path,
        recursive=recursive,
        quality=quality,
        remove_transparency=remove_transparency,
        reduce_colors=reduce_colors,
        max_colors=max_colors,
        max_w=max_w,
        max_h=max_h,
        keep_exif=keep_exif,
        convert_all=convert_all,
        conv_big=conv_big,
        force_del=force_del,
        bg_color=bg_color,
        grayscale=grayscale,
        ignore_size_comparison=ignore_size_comparison,
        fast_mode=fast_mode,
        jobs=jobs,
        convert_to=convert_to,
        webp_quality=webp_quality,
        webp_lossless=webp_lossless,
        webp_method=webp_method,
    )

    if watch_dir:
        # Use public API watcher with CLI rendering callback
        import threading
        stop_event = threading.Event()

        def on_result(public_result):
            nonlocal found_files, optimized_files, skipped_files, total_src_size, total_bytes_saved
            found_files += 1
            total_src_size += public_result.orig_size
            if public_result.was_optimized:
                optimized_files += 1
                total_bytes_saved += public_result.orig_size - public_result.final_size
            else:
                skipped_files += 1

            if output_config.quiet_mode or output_config.show_only_summary:
                return

            if output_config.show_overall_progress:
                cur_time_passed = round(timer() - appstart)
                message = f"[{cur_time_passed:.1f}s] {IconGenerator().optimized} {optimized_files} {IconGenerator().skipped} {skipped_files}, saved {human(total_bytes_saved)}"
                print(message, end='\r')
            else:
                show_file_status(public_result, line_width, IconGenerator())

        try:
            watch_directory(options, on_result=on_result, stop_event=stop_event)
        except KeyboardInterrupt:
            msg = "\b \n\n  == Operation was interrupted by the user. ==\n"
            raise OIKeyboardInterrupt(msg)
        return

    icons = None
    if not output_config.quiet_mode and not output_config.show_only_summary:
        icons = IconGenerator()

    # Print introductory header (only for non-quiet, non-summary, non-progress modes)
    if not output_config.quiet_mode and not output_config.show_only_summary and not output_config.show_overall_progress:
        icons.print_legend()

        print("\nRecursively searching and optimizing image files in:")
        # Respect line width if provided
        src_line = options.src_path
        if isinstance(line_width, int) and line_width > 0:
            src_line = src_line[:line_width]
        print(src_line + "\n\n")

    try:
        for result in optimize_as_batch_stream(options):
            found_files += 1
            total_src_size += result.orig_size
            if result.was_optimized:
                optimized_files += 1
                total_bytes_saved += result.orig_size - result.final_size
            else:
                skipped_files += 1

            if output_config.quiet_mode or output_config.show_only_summary:
                continue

            if output_config.show_overall_progress:
                cur_time_passed = round(timer() - appstart)
                message = f"[{cur_time_passed:.1f}s] {icons.optimized if icons else ''} {optimized_files} {icons.skipped if icons else ''} {skipped_files}, saved {human(total_bytes_saved)}"
                print(message, end='\r')
            else:
                show_file_status(result, line_width, icons if icons else IconGenerator())
    except KeyboardInterrupt:
        msg = "\b \n\n  == Operation was interrupted by the user. ==\n"
        raise OIKeyboardInterrupt(msg)

    if found_files:
        time_passed = timer() - appstart
        show_final_report(found_files, optimized_files, total_src_size,
                          total_bytes_saved, time_passed, output_config)
    else:
        msg = "\nNo supported image files were found in the specified directory."
        raise OIImagesNotFoundError(msg)

if __name__ == "__main__":
    main()
