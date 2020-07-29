# encoding: utf-8
import os
import shutil

try:
    from PIL import Image, ImageFile
except ImportError:
    msg = 'This application requires Pillow to be installed. Please, install it first.'
    raise ImportError(msg)

from optimize_images.data_structures import Task, TaskResult
from optimize_images.img_info import is_big_png_photo
from optimize_images.img_aux_processing import remove_transparency, make_grayscale
from optimize_images.img_aux_processing import do_reduce_colors, downsize_img, rebuild_palette
from optimize_images.reporting import show_img_exception


def optimize_png(t: Task) -> TaskResult:
    """ Try to reduce file size of a PNG image.

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

    had_exif = has_exif = False  # Currently no exif methods for PNG files
    if orig_mode == 'P':
        final_colors = orig_colors = len(img.getcolors())

    if t.convert_all or (t.conv_big and is_big_png_photo(t.src_path)):
        # convert to jpg format
        filename = os.path.splitext(os.path.basename(t.src_path))[0]
        conv_file_path = os.path.join(folder + "/" + filename + ".jpg")

        if t.max_w or t.max_h:
            img, was_downsized = downsize_img(img, t.max_w, t.max_h)
        else:
            was_downsized = False

        img = remove_transparency(img, t.bg_color)
        img = img.convert("RGB")

        if t.grayscale:
            img = make_grayscale(img)

        try:
            img.save(
                conv_file_path,
                quality=t.quality,
                optimize=True,
                progressive=True,
                format="JPEG")
        except IOError:
            ImageFile.MAXBLOCK = img.size[0] * img.size[1]
            img.save(
                conv_file_path,
                quality=t.quality,
                optimize=True,
                progressive=True,
                format="JPEG")

        # Only save the converted file if conversion did save any space
        final_size = os.path.getsize(conv_file_path)
        if t.no_size_comparison or (orig_size - final_size > 0):
            was_optimized = True
            if t.force_del:
                try:
                    os.remove(t.src_path)
                except OSError as e:
                    details = 'Error while replacing original PNG with the new JPEG version.'
                    show_img_exception(e, t.src_path, details)
        else:
            final_size = orig_size
            was_optimized = False
            try:
                os.remove(conv_file_path)
            except OSError as e:
                details = 'Error while removing temporary JPEG converted file.'
                show_img_exception(e, t.src_path, details)

        result_format = "JPEG"
        return TaskResult(t.src_path, orig_format, result_format,
                          orig_mode, img.mode, orig_colors, final_colors,
                          orig_size, final_size, was_optimized,
                          was_downsized, had_exif, has_exif)

    # if PNG and user didn't ask for PNG to JPEG conversion, do this instead.
    else:
        result_format = "PNG"
        if t.remove_transparency:
            img = remove_transparency(img, t.bg_color)

        if t.max_w or t.max_h:
            img, was_downsized = downsize_img(img, t.max_w, t.max_h)
        else:
            was_downsized = False

        if t.reduce_colors:
            img, orig_colors, final_colors = do_reduce_colors(
                img, t.max_colors)

        if t.grayscale:
            img = make_grayscale(img)

        if not t.fast_mode and img.mode == "P":
            img, final_colors = rebuild_palette(img)

        try:
            img.save(temp_file_path, optimize=True, format=result_format)
        except IOError:
            ImageFile.MAXBLOCK = img.size[0] * img.size[1]
            img.save(temp_file_path, optimize=True, format=result_format)

        final_size = os.path.getsize(temp_file_path)

        # Only replace the original file if compression did save any space
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
