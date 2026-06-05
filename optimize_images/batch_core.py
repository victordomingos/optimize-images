# encoding: utf-8
"""
Internal batch orchestration helpers shared by CLI and API.
This module is internal-only and may change without notice.
"""
import os
from typing import Iterable

from optimize_images.data_structures import Task, BatchOptions
from optimize_images.file_utils import search_images


def build_tasks(options: BatchOptions) -> Iterable[Task]:
    if not options.src_path:
        return []
    if os.path.isdir(options.src_path):
        return (
            Task(img_path, options.quality, options.remove_transparency,
                 options.reduce_colors, options.max_colors, options.max_w,
                 options.max_h, options.keep_exif, options.convert_all,
                 options.conv_big, options.force_del, options.bg_color,
                 options.grayscale, options.ignore_size_comparison,
                 options.fast_mode, options.output_config,
                 options.convert_to, options.webp_quality,
                 options.webp_lossless, options.webp_method)
            for img_path in search_images(options.src_path, recursive=options.recursive)
        )
    elif os.path.isfile(options.src_path) and '~temp~' not in options.src_path:
        return [
            Task(options.src_path, options.quality, options.remove_transparency,
                 options.reduce_colors, options.max_colors, options.max_w,
                 options.max_h, options.keep_exif, options.convert_all,
                 options.conv_big, options.force_del, options.bg_color,
                 options.grayscale, options.ignore_size_comparison,
                 options.fast_mode, options.output_config,
                 options.convert_to, options.webp_quality,
                 options.webp_lossless, options.webp_method)
        ]
    return []
