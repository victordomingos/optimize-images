# encoding: utf-8
import os
import shutil

import piexif

from PIL import Image, ImageFile

from optimize_images.data_structures import Task, TaskResult
from optimize_images.img_info import is_big_png_photo
from optimize_images.img_aux_processing import remove_transparency
from optimize_images.img_aux_processing import do_reduce_colors, downsize_img


def do_optimization(t: Task) -> TaskResult:
    """ Try to reduce file size of an image.

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
    # print(f'{t.src_path} - {orig_format}/{orig_mode} - {img.size[0]}x{img.size[1]}')  # DEBUG

    folder, filename = os.path.split(t.src_path)
    temp_file_path = os.path.join(folder + "/~temp~" + filename)
    orig_size = os.path.getsize(t.src_path)
    orig_colors, final_colors = 0, 0

    if orig_format.upper() == 'PNG':
        had_exif = has_exif = False  # Currently no exif methods for PNG files
        if orig_mode == 'P':
            orig_colors = len(img.getpalette()) // 3
            final_colors = orig_colors

        if t.conv_big and is_big_png_photo(t.src_path):
            # convert to jpg format
            filename = os.path.splitext(os.path.basename(t.src_path))[0]
            conv_file_path = os.path.join(folder + "/" + filename + ".jpg")

            if t.max_w or t.max_h:
                img, was_downsized = downsize_img(img, t.max_w, t.max_h)
            else:
                was_downsized = False

            img = remove_transparency(img, t.bg_color)
            img = img.convert("RGB")

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
            if orig_size - final_size > 0:
                was_optimized = True
                if t.force_del:
                    try:
                        os.remove(t.src_path)
                    except OSError as e:
                        print(
                            "\nError while replacing original PNG with the new JPEG version.\n{e}\n"
                        )
            else:
                final_size = orig_size
                was_optimized = False
                try:
                    os.remove(conv_file_path)
                except OSError as e:
                    print(
                        "\nError while removing temporary JPEG converted file.\n{e}\n"
                    )

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

            try:
                img.save(temp_file_path, optimize=True, format=result_format)
            except IOError:
                ImageFile.MAXBLOCK = img.size[0] * img.size[1]
                img.save(temp_file_path, optimize=True, format=result_format)

    # Doing regular JPEG processing here.
    else:
        result_format = "JPEG"
        try:
            had_exif = True if piexif.load(t.src_path)['Exif'] else False
        except piexif.InvalidImageDataError:  # Not a supported format
            had_exif = False
        except ValueError:  # No exif info
            had_exif = False

        if t.max_w or t.max_h:
            img, was_downsized = downsize_img(img, t.max_w, t.max_h)
        else:
            was_downsized = False

        # only use progressive if file size is bigger
        use_progressive_jpg = orig_size > 10000
        try:
            img.save(
                temp_file_path,
                optimize=True,
                progressive=use_progressive_jpg,
                format=result_format)
        except IOError:
            ImageFile.MAXBLOCK = img.size[0] * img.size[1]
            img.save(
                temp_file_path,
                optimize=True,
                progressive=use_progressive_jpg,
                format=result_format)

        if t.keep_exif and had_exif:
            try:
                piexif.transplant(
                    os.path.expanduser(t.src_path), temp_file_path)
                has_exif = True
            except:
                has_exif = False
        else:
            has_exif = False

    final_size = os.path.getsize(temp_file_path)

    # Only replace the original file if compression did save any space
    if orig_size - final_size > 0:
        shutil.move(temp_file_path, os.path.expanduser(t.src_path))
        was_optimized = True
    else:
        final_size = orig_size
        was_optimized = False
        try:
            os.remove(temp_file_path)
        except OSError as e:
            print("\nError while removing temporary file.\n{e}\n")

    return TaskResult(t.src_path, orig_format, result_format, orig_mode,
                      img.mode, orig_colors, final_colors, orig_size,
                      final_size, was_optimized, was_downsized, had_exif,
                      has_exif)
