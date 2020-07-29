# encoding: utf-8
import os
import shutil

import piexif

try:
    from PIL import Image, ImageFile
except ImportError:
    msg = 'This application requires Pillow to be installed. Please, install it first.'
    raise ImportError(msg)

from optimize_images.data_structures import Task, TaskResult
from optimize_images.img_aux_processing import make_grayscale
from optimize_images.img_aux_processing import downsize_img
from optimize_images.img_dynamic_quality import jpeg_dynamic_quality
from optimize_images.reporting import show_img_exception


def optimize_jpg(t: Task) -> TaskResult:
    """ Try to reduce file size of a JPG image.

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

    if folder == '':
        folder = os.getcwd()

    temp_file_path = os.path.join(folder + "/~temp~" + filename)
    orig_size = os.path.getsize(t.src_path)
    orig_colors, final_colors = 0, 0

    result_format = "JPEG"
    try:
        had_exif = True if piexif.load(t.src_path)['Exif'] else False
    except piexif.InvalidImageDataError:  # Not a supported format
        had_exif = False
    except ValueError:  # No exif info
        had_exif = False
    # TODO: Check if we can provide a more specific treatment of piexif exceptions.
    except Exception:
        had_exif = False

    if t.max_w or t.max_h:
        img, was_downsized = downsize_img(img, t.max_w, t.max_h)
    else:
        was_downsized = False

    if t.grayscale:
        img = make_grayscale(img)

    # only use progressive if file size is bigger
    use_progressive_jpg = orig_size > 10000

    if t.fast_mode:
        quality = t.quality
    else:
        quality, jpgdiff = jpeg_dynamic_quality(img)

    try:
        img.save(
            temp_file_path,
            quality=quality,
            optimize=True,
            progressive=use_progressive_jpg,
            format=result_format)
    except IOError:
        ImageFile.MAXBLOCK = img.size[0] * img.size[1]
        img.save(
            temp_file_path,
            quality=quality,
            optimize=True,
            progressive=use_progressive_jpg,
            format=result_format)

    if t.keep_exif and had_exif:
        try:
            piexif.transplant(
                os.path.expanduser(t.src_path), temp_file_path)
            has_exif = True
        except ValueError:
            has_exif = False
        # TODO: Check if we can provide a more specific treatment of piexif exceptions.
        except Exception:
            had_exif = False
    else:
        has_exif = False

    # Only replace the original file if compression did save any space
    final_size = os.path.getsize(temp_file_path)
    if t.no_size_comparison or (orig_size - final_size > 0):
        shutil.move(temp_file_path, os.path.expanduser(t.src_path))
        was_optimized = True
    else:
        final_size = orig_size
        was_optimized = False
        try:
            os.remove(temp_file_path)
        except OSError as e:
            details = 'Error while removing temporary file.'
            show_img_exception(e, t.src_path, details)

    return TaskResult(t.src_path, orig_format, result_format, orig_mode,
                      img.mode, orig_colors, final_colors, orig_size,
                      final_size, was_optimized, was_downsized, had_exif,
                      has_exif)
