# encoding: utf-8

import os

import piexif
from PIL import Image

from optimize_images.data_structures import Task, TaskResult
from optimize_images.img_optimize_jpg import optimize_jpg
from optimize_images.img_optimize_png import optimize_png


def do_optimization(task: Task) -> TaskResult:
    """ Try to reduce file size of an image.

    Expects a Task object containing all the parameters for the image xprocessing.

    The actual processing is done by the corresponding function,
    according to the detected image format.

    :param task: A Task object containing all the parameters for the image processing.
    :return: A TaskResult object containing information for single file report.
    """
    # TODO: Catch exceptions that may occur here.
    try:
        img: Image.Image
        with Image.open(task.src_path) as img:
            img_format: str = img.format.upper()
            mode: str = img.mode

        if img_format == 'PNG':
            return optimize_png(task)
        if img_format in ('JPEG', 'MPO'):
            return optimize_jpg(task)

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

    # TODO: improve method of image format detection (what should happen if the
    #       file extension does not match the image content's format? Maybe we
    #       should skip unsupported formats?)

    # Reporting about unsupported formats:
    try:
        had_exif = True if piexif.load(task.src_path)['Exif'] else False
    except piexif.InvalidImageDataError:  # Not a supported format
        had_exif = False
    except ValueError:  # No exif info
        had_exif = False

    return TaskResult(img=task.src_path,
                      orig_format=img_format,
                      result_format=img_format,
                      orig_mode=mode,
                      result_mode=mode,
                      orig_colors=0,
                      final_colors=0,
                      orig_size=os.path.getsize(task.src_path),
                      final_size=0,
                      was_optimized=False,
                      was_downsized=False,
                      had_exif=had_exif,
                      has_exif=had_exif,
                      output_config=task.output_config)
