# encoding: utf-8
import os
from io import BytesIO

from PIL import Image, ImageFile

from .data_structures import Task, TaskResult, OptimizedImage
from .img_aux_processing import downsize_img, save_compressed
from .img_aux_processing import ssim_needs_computing
from .img_aux_processing import make_grayscale
from .img_dynamic_quality import jpeg_dynamic_quality
from .img_ssim import compute_ssim


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
    orig_size = os.path.getsize(task.src_path)
    with Image.open(task.src_path) as img:
        opt = transform_jpg(img, task, orig_size)

    compare_sizes = not task.no_size_comparison
    was_optimized, final_size = save_compressed(
        task.src_path,
        opt.buffer,
        compare_sizes,
        ssim=opt.ssim,
        ssim_min=task.ssim_min
    )

    return TaskResult(
        task.src_path, opt.orig_format, opt.result_format, opt.orig_mode,
        opt.result_mode, opt.orig_colors, opt.final_colors, orig_size,
        final_size, was_optimized, opt.was_downsized, opt.had_exif,
        opt.has_exif, task.output_config, opt.ssim
    )


def transform_jpg(img: Image.Image, task: Task,
                  orig_size: int) -> OptimizedImage:
    """Optimize an already-open JPEG image in memory.

    Pure: performs the requested transforms and encodes the result into an
    in-memory buffer, without touching the filesystem. Shared by the
    file-based optimizer and the in-memory API.
    """
    orig_format = img.format or 'JPEG'
    orig_mode = img.mode
    result_format = "JPEG"

    # Detect EXIF presence using Pillow
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

    if task.grayscale:
        img = make_grayscale(img)

    # only use progressive if file size is bigger
    use_progressive_jpg = orig_size > 10000

    if task.fast_mode:
        quality = task.quality
    else:
        quality, _ = jpeg_dynamic_quality(img)

    tmp_buffer = BytesIO()  # In-memory buffer

    # If keeping EXIF and the source had EXIF, pass it through on save.
    save_kwargs = {
        'quality': quality,
        'optimize': True,
        'progressive': use_progressive_jpg,
        'format': result_format
    }

    if task.keep_exif and had_exif and exif:
        save_kwargs['exif'] = exif

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
