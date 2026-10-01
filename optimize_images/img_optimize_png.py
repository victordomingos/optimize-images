# encoding: utf-8
import os
from io import BytesIO
from typing import Optional

from PIL import Image, ImageFile
from optimize_images.data_structures import Task, TaskResult, OptimizedImage
from optimize_images.img_aux_processing import do_reduce_colors, downsize_img, rebuild_palette
from optimize_images.img_aux_processing import remove_transparency, make_grayscale, save_compressed
from optimize_images.img_aux_processing import ssim_needs_computing
from optimize_images.img_ssim import compute_ssim


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

        Animated PNG files are left as-is, like animated WebP: they are
        reported as not optimized.

        :param task: A Task object containing all the parameters for the image processing.
        :return: A TaskResult object containing information for single file report.
        """
    orig_size = os.path.getsize(task.src_path)
    with Image.open(task.src_path) as img:
        orig_format = img.format or 'PNG'
        orig_mode = img.mode
        opt = transform_png(img, task, orig_size)
        if opt is None:  # animated PNG: leave as-is
            return TaskResult(task.src_path, orig_format, "PNG", orig_mode,
                              orig_mode, 0, 0, orig_size, orig_size, False,
                              False, False, False, task.output_config, None)

    compare_sizes = not task.no_size_comparison
    was_optimized, final_size = save_compressed(task.src_path,
                                                opt.buffer,
                                                force_delete=task.force_del,
                                                compare_sizes=compare_sizes,
                                                ssim=opt.ssim,
                                                ssim_min=task.ssim_min)

    return TaskResult(task.src_path, opt.orig_format, opt.result_format,
                      opt.orig_mode, opt.result_mode, opt.orig_colors,
                      opt.final_colors, orig_size, final_size, was_optimized,
                      opt.was_downsized, opt.had_exif, opt.has_exif,
                      task.output_config, opt.ssim)


def transform_png(img: Image.Image, task: Task,
                  orig_size: int) -> Optional[OptimizedImage]:
    """Optimize an already-open PNG image in memory (no filesystem access).

    Returns an OptimizedImage, or None for animated PNG, which is left
    untouched to avoid flattening it to a single frame. Shared by the
    file-based optimizer and the in-memory API. Conversion to a
    different output format is handled upstream by the shared converter; this
    keeps the image as a PNG. ``orig_size`` is the source file size, used for
    the size-gated SSIM skip (it must match the size the keep/reject decision
    compares against).
    """
    orig_format = img.format or 'PNG'
    orig_mode = img.mode

    # Animated PNG files are left untouched (an in-place re-encode would keep
    # only the first frame). MPO (multi-page) JPEGs are a different case and
    # are handled as JPEG, not here.
    if getattr(img, "n_frames", 1) > 1:
        return None

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

    # Compute SSIM if requested. The reference is the image after the
    # transforms above but before the lossy encoding, so the score isolates
    # the pure encoding loss (img is passed as-is: save() and the SSIM
    # computation do not mutate it). The score is expensive, so it is
    # skipped when the result is already rejected by the size check and the
    # score has no other use (ssim_needs_computing); in that case it stays
    # None, and the gate fails closed, so the decision is unchanged.
    ssim = None
    if ssim_needs_computing(task.ssim_min, task.show_ssim,
                            not task.no_size_comparison,
                            tmp_buffer.getbuffer().nbytes, orig_size):
        with Image.open(tmp_buffer) as opt_img:
            ssim = compute_ssim(img, opt_img, bg_color=task.bg_color)

    return OptimizedImage(tmp_buffer, orig_format, result_format, orig_mode,
                          img.mode, orig_colors, final_colors, was_downsized,
                          had_exif, has_exif, ssim)
