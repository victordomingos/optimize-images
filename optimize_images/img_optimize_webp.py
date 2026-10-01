# encoding: utf-8
import os
from io import BytesIO

from PIL import Image, ImageFile
from optimize_images.data_structures import Task, TaskResult, OptimizedImage
from optimize_images.img_aux_processing import downsize_img, make_grayscale
from optimize_images.img_aux_processing import remove_transparency, save_compressed
from optimize_images.img_aux_processing import ssim_needs_computing
from optimize_images.img_ssim import compute_ssim


def optimize_webp(task: Task) -> TaskResult:
    """ Try to reduce file size of a WebP image.

        Expects a Task object containing all the parameters for the image
        processing.

        If file reduction is successful, this function will replace the original
        file with the optimized version and return some report data (file path,
        image format, image color mode, original file size, resulting file size,
        and resulting status of the optimization).

        WebP supports transparency natively, so the alpha channel is preserved
        unless the user explicitly asks to remove it.

        :param task: A Task object containing all the parameters for the image processing.
        :return: A TaskResult object containing information for single file report.
        """
    orig_size = os.path.getsize(task.src_path)
    with Image.open(task.src_path) as img:
        orig_format = img.format
        orig_mode = img.mode
        opt = transform_webp(img, task, orig_size)
        if opt is None:  # animated WebP: leave as-is
            return TaskResult(task.src_path, orig_format, "WEBP", orig_mode,
                              orig_mode, 0, 0, orig_size, orig_size, False,
                              False, False, False, task.output_config, None)

    compare_sizes = not task.no_size_comparison
    was_optimized, final_size = save_compressed(task.src_path,
                                                opt.buffer,
                                                compare_sizes=compare_sizes,
                                                ssim=opt.ssim,
                                                ssim_min=task.ssim_min)

    return TaskResult(task.src_path, opt.orig_format, opt.result_format,
                      opt.orig_mode, opt.result_mode, opt.orig_colors,
                      opt.final_colors, orig_size, final_size, was_optimized,
                      opt.was_downsized, opt.had_exif, opt.has_exif,
                      task.output_config, opt.ssim)


def transform_webp(img: Image.Image, task: Task,
                   orig_size: int):
    """Optimize an already-open WebP image in memory (no filesystem access).

    Returns an OptimizedImage, or None for animated WebP, which is left
    untouched to avoid flattening it to a single frame. Shared by the
    file-based optimizer and the in-memory API. ``orig_size`` is the source
    file size, used for the size-gated SSIM skip (it must match the size the
    keep/reject decision compares against).
    """
    orig_format = img.format or 'WEBP'
    orig_mode = img.mode
    result_format = "WEBP"

    # Animated WebP files are left untouched.
    if getattr(img, "n_frames", 1) > 1:
        return None

    # Detect EXIF presence using Pillow (WebP can carry EXIF data).
    try:
        exif = img.getexif()
        had_exif = bool(exif and len(exif) > 0)
    except Exception:
        had_exif = False
        exif = None

    if task.max_w or task.max_h:
        img, was_downsized = downsize_img(img, task.max_w, task.max_h)
    else:
        was_downsized = False

    if task.remove_transparency:
        img = remove_transparency(img, task.bg_color)

    if task.grayscale:
        img = make_grayscale(img)

    save_kwargs = {
        'format': result_format,
        'quality': task.webp_quality,
        'method': task.webp_method,
        'lossless': task.webp_lossless,
    }

    if task.keep_exif and had_exif and exif:
        save_kwargs['exif'] = exif

    tmp_buffer = BytesIO()  # In-memory buffer
    try:
        img.save(tmp_buffer, **save_kwargs)
    except IOError:
        ImageFile.MAXBLOCK = img.size[0] * img.size[1]
        img.save(tmp_buffer, **save_kwargs)

    has_exif = bool(save_kwargs.get('exif'))

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
                          img.mode, 0, 0, was_downsized, had_exif, has_exif, ssim)
