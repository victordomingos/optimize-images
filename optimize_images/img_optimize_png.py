# encoding: utf-8
import os
from io import BytesIO

from PIL import Image, ImageFile
from optimize_images.data_structures import Task, TaskResult
from optimize_images.img_aux_processing import do_reduce_colors, downsize_img, rebuild_palette
from optimize_images.img_aux_processing import remove_transparency, make_grayscale, save_compressed


def optimize_png(task: Task) -> TaskResult:
    """ Try to reduce file size of a PNG image.

        Expects a Task object containing all the parameters for the image processing.

        If file reduction is successful, this function will replace the original
        file with the optimized version and return some report data (file path,
        image format, image color mode, original file size, resulting file size,
        and resulting status of the optimization.

        Conversion to a different output format (e.g. PNG to JPEG/WebP) is
        decided upstream in do_optimization and handled by the shared converter;
        this function only optimizes the image keeping it as a PNG.

        :param task: A Task object containing all the parameters for the image processing.
        :return: A TaskResult object containing information for single file report.
        """

    img: Image.Image = Image.open(task.src_path)
    orig_format = img.format
    orig_mode = img.mode

    folder, filename = os.path.split(task.src_path)

    if folder == '':
        folder = os.getcwd()

    orig_size = os.path.getsize(task.src_path)
    orig_colors, final_colors = 0, 0

    had_exif = has_exif = False  # Currently no exif methods for PNG files
    if orig_mode == 'P':
        final_colors = orig_colors = len(img.getcolors())

    result_format = "PNG"
    if task.remove_transparency:
        img = remove_transparency(img, task.bg_color)

    if task.max_w or task.max_h:
        img, was_downsized = downsize_img(img, task.max_w, task.max_h)
    else:
        was_downsized = False

    if task.reduce_colors:
        img, orig_colors, final_colors = do_reduce_colors(
            img, task.max_colors)

    if task.grayscale:
        img = make_grayscale(img)

    if not task.fast_mode and img.mode == "P":
        img, final_colors = rebuild_palette(img)

    tmp_buffer = BytesIO()  # In-memory buffer
    try:
        img.save(tmp_buffer, optimize=True, format=result_format)
    except IOError:
        ImageFile.MAXBLOCK = img.size[0] * img.size[1]
        img.save(tmp_buffer, optimize=True, format=result_format)

    img_mode = img.mode
    img.close()
    compare_sizes = not task.no_size_comparison
    was_optimized, final_size = save_compressed(task.src_path,
                                                tmp_buffer,
                                                force_delete=task.force_del,
                                                compare_sizes=compare_sizes)

    return TaskResult(task.src_path, orig_format, result_format, orig_mode,
                      img_mode, orig_colors, final_colors, orig_size,
                      final_size, was_optimized, was_downsized, had_exif,
                      has_exif, task.output_config)
