# encoding: utf-8

try:
    from PIL import Image
except ImportError:
    print('\n    This application requires Pillow to be installed. Please, install it first.\n')
    exit()
#
# try:
#     from PIL import UnidentifiedImageError
# except ImportError:
#     print('\n    This application requires Pillow to be installed. Please, install it first.aaa\n')
#     exit()

import os
import piexif

from optimize_images.data_structures import Task, TaskResult
from optimize_images.img_optimize_jpg import optimize_jpg
from optimize_images.img_optimize_png import optimize_png


def do_optimization(t: Task) -> TaskResult:
    """ Try to reduce file size of an image.

    Expects a Task object containing all the parameters for the image processing.

    The actual processing is done by the corresponding function,
    according to the detected image format.

    :param t: A Task object containing all the parameters for the image processing.
    :return: A TaskResult object containing information for single file report.
    """
    # TODO: Catch exceptions that may occur here.
    try:
        img = Image.open(t.src_path)

        # TODO: improve method of image format detection (what should happen if the
        #       file extension does not match the image content's format? Maybe we
        #       should skip unsupported formats?)
        if img.format.upper() == 'PNG':
            return optimize_png(t)
        elif img.format.upper() in ('JPEG', 'MPO'):
            return optimize_jpg(t)
        else:
            try:
                had_exif = True if piexif.load(t.src_path)['Exif'] else False
            except piexif.InvalidImageDataError:  # Not a supported format
                had_exif = False
            except ValueError:  # No exif info
                had_exif = False
            return TaskResult(img=t.src_path,
                              orig_format=img.format.upper(),
                              result_format=img.format.upper(),
                              orig_mode=img.mode,
                              result_mode=img.mode,
                              orig_colors=0,
                              final_colors=0,
                              orig_size=os.path.getsize(t.src_path),
                              final_size=0,
                              was_optimized=False,
                              was_downsized=False,
                              had_exif=had_exif,
                              has_exif=had_exif)

    except IOError:
        try:
            had_exif = True if piexif.load(t.src_path)['Exif'] else False
        except piexif.InvalidImageDataError:  # Not a supported format
            had_exif = False
        except ValueError:  # No exif info
            had_exif = False
        return TaskResult(img=t.src_path,
                          orig_format="",
                          result_format="",
                          orig_mode="",
                          result_mode="",
                          orig_colors=0,
                          final_colors=0,
                          orig_size=os.path.getsize(t.src_path),
                          final_size=0,
                          was_optimized=False,
                          was_downsized=False,
                          had_exif=had_exif,
                          has_exif=had_exif)
