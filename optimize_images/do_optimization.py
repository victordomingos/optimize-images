# encoding: utf-8

import os

from PIL import Image
from optimize_images.data_structures import Task, TaskResult
from optimize_images.img_convert import convert_image
from optimize_images.img_info import is_big_png_photo
from optimize_images.img_optimize_jpg import optimize_jpg
from optimize_images.img_optimize_png import optimize_png
from optimize_images.img_optimize_webp import optimize_webp

# Maps a Pillow source format to our canonical format name, so we can tell
# when a requested conversion would target the same format it already is.
_PIL_TO_CANON = {'PNG': 'png', 'JPEG': 'jpeg', 'MPO': 'jpeg', 'WEBP': 'webp'}


def _conversion_target(task: Task, img_format: str):
    """Decide whether this image should be converted, and to which format.

    Scope follows the existing options: -ca converts every source format,
    while -cb stays specific to big photographic PNGs. Returns the canonical
    target name, or None to optimize the image in its original format.
    """
    target = (task.convert_to or 'jpeg').strip().lower()
    if target == 'jpg':
        target = 'jpeg'

    if task.convert_all:
        in_scope = True
    elif task.conv_big and img_format == 'PNG' \
            and is_big_png_photo(task.src_path):
        in_scope = True
    else:
        in_scope = False

    if not in_scope:
        return None
    # Converting to the same format is a no-op; optimize in place instead.
    if _PIL_TO_CANON.get(img_format) == target:
        return None
    return target


def do_optimization(task: Task) -> TaskResult:
    """ Try to reduce file size of an image.

    Expects a Task object containing all the parameters for the image
    processing. When a conversion is requested (and applicable), the shared
    converter is used regardless of the source format; otherwise the image is
    optimized in place by the matching per-format optimizer.

    :param task: A Task object with all the parameters for the processing.
    :return: A TaskResult object containing information for single file report.
    """
    try:
        img = Image.open(task.src_path)
        img_format: str = (img.format or '').upper()
        orig_mode: str = img.mode
        orig_size: int = os.path.getsize(task.src_path)

        target = _conversion_target(task, img_format)
        if target is not None:
            try:
                exif = img.getexif()
                had_exif = bool(exif and len(exif) > 0)
            except Exception:
                exif, had_exif = None, False
            return convert_image(task, img, img_format, orig_mode,
                                 orig_size, had_exif, exif)

        img.close()
        if img_format == 'PNG':
            return optimize_png(task)
        if img_format in ('JPEG', 'MPO'):
            return optimize_jpg(task)
        if img_format == 'WEBP':
            return optimize_webp(task)

    except OSError:
        return TaskResult(img=task.src_path,
                          orig_format='',
                          result_format='',
                          orig_mode='',
                          result_mode='',
                          orig_colors=0,
                          final_colors=0,
                          orig_size=os.path.getsize(task.src_path),
                          final_size=0,
                          was_optimized=False,
                          was_downsized=False,
                          had_exif=False,
                          has_exif=False,
                          output_config=task.output_config)

    # Readable but unsupported format: report it as skipped.
    try:
        with Image.open(task.src_path) as img2:
            exif = img2.getexif()
            had_exif = bool(exif and len(exif) > 0)
    except (OSError, ValueError):
        had_exif = False

    return TaskResult(img=task.src_path,
                      orig_format=img_format,
                      result_format=img_format,
                      orig_mode=orig_mode,
                      result_mode=orig_mode,
                      orig_colors=0,
                      final_colors=0,
                      orig_size=orig_size,
                      final_size=0,
                      was_optimized=False,
                      was_downsized=False,
                      had_exif=had_exif,
                      has_exif=had_exif,
                      output_config=task.output_config)
