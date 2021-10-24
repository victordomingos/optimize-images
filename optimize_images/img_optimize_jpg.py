# encoding: utf-8
import os
from io import BytesIO

import piexif
from PIL import Image, ImageFile

from .data_structures import Task, TaskResult
from .img_aux_processing import downsize_img, save_compressed
from .img_aux_processing import make_grayscale
from .img_dynamic_quality import jpeg_dynamic_quality


def optimize_jpg(task: Task) -> TaskResult:
    """ Try to reduce file size of a JPG image.

    Expects a Task object containing all the parameters for the image processing.

    If file reduction is successful, this function will replace the original
    file with the optimized version and return some report data (file path,
    image format, image color mode, original file size, resulting file size,
    and resulting status of the optimization.

    :param task: A Task object containing all the parameters for the image processing.
    :return: A TaskResult object containing information for single file report.
    """
    img: Image.Image = Image.open(task.src_path)
    orig_format = img.format
    orig_mode = img.mode

    orig_size = os.path.getsize(task.src_path)
    orig_colors, final_colors = 0, 0

    result_format = "JPEG"
    try:
        had_exif = True if piexif.load(task.src_path)['Exif'] else False
    except piexif.InvalidImageDataError:  # Not a supported format
        had_exif = False
    except ValueError:  # No exif info
        had_exif = False
    # TODO: Check if we can provide a more specific treatment of piexif exceptions.
    except Exception:
        had_exif = False

    if task.max_w or task.max_h:
        img, was_downsized = downsize_img(img, task.max_w, task.max_h)
    else:
        was_downsized = False

    if task.grayscale:
        img = make_grayscale(img)

    # only use progressive if file size is bigger
    use_progressive_jpg = orig_size > 10000

    if task.fast_mode:
        quality = task.quality
    else:
        quality, _ = jpeg_dynamic_quality(img)

    tmp_buffer = BytesIO()  # In-memory buffer
    try:
        img.save(
            tmp_buffer,
            quality=quality,
            optimize=True,
            progressive=use_progressive_jpg,
            format=result_format)
    except IOError:
        ImageFile.MAXBLOCK = img.size[0] * img.size[1]
        img.save(
            tmp_buffer,
            quality=quality,
            optimize=True,
            progressive=use_progressive_jpg,
            format=result_format)

    if task.keep_exif and had_exif:
        try:
            piexif.transplant(os.path.expanduser(task.src_path), tmp_buffer)
            has_exif = True
        except ValueError:
            has_exif = False
        # TODO: Check if we can provide a more specific treatment
        #       of piexif exceptions.
        except Exception:
            has_exif = False
    else:
        has_exif = False

    img_mode = img.mode
    img.close()
    compare_sizes = not task.no_size_comparison
    was_optimized, final_size = save_compressed(task.src_path,
                                                tmp_buffer,
                                                compare_sizes)

    return TaskResult(task.src_path, orig_format, result_format, orig_mode,
                      img_mode, orig_colors, final_colors, orig_size,
                      final_size, was_optimized, was_downsized, had_exif,
                      has_exif, task.output_config)
