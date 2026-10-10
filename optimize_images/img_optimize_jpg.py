# encoding: utf-8
import os

from PIL import Image

from .data_structures import Task, TaskResult, OptimizedImage
from .img_aux_processing import downsize_img, save_compressed
from .jpeg_qtables import jpeg_quality_kwargs, resolve_jpeg_tables, retry_with_standard
from .img_aux_processing import encode_and_score
from .img_aux_processing import make_grayscale
from .img_dynamic_quality import jpeg_dynamic_quality, DYNAMIC_QUALITY_MIN
from .img_icc import get_suitable_icc
from .constants import DEFAULT_QUALITY


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

    # Read the source profile before any transforms (which create new
    # images without img.info).  The profile is matched against the
    # output mode, not the source mode.
    src_profile = img.info.get('icc_profile')
    # Same for the quantization tables, used by jpeg_tables='auto'.
    src_quantization = getattr(img, 'quantization', None)

    if task.max_w or task.max_h:
        img, was_downsized = downsize_img(img, task.max_w, task.max_h)
    else:
        was_downsized = False

    if task.grayscale:
        img = make_grayscale(img)

    # only use progressive if file size is bigger
    use_progressive_jpg = orig_size > 10000

    fixed_quality = task.fast_mode or task.quality is not None
    if fixed_quality:
        quality = task.quality if task.quality is not None else DEFAULT_QUALITY
        jpeg_tables = resolve_jpeg_tables(task.jpeg_tables, src_quantization,
                                          quality, quality, was_downsized)
    else:
        jpeg_tables = resolve_jpeg_tables(task.jpeg_tables, src_quantization,
                                          DYNAMIC_QUALITY_MIN, DEFAULT_QUALITY,
                                          was_downsized)
        quality, _ = jpeg_dynamic_quality(img, jpeg_tables=jpeg_tables)

    # If keeping EXIF and the source had EXIF, pass it through on save.
    save_kwargs: dict = {
        'optimize': True,
        'progressive': use_progressive_jpg,
        'format': result_format,
    }

    if task.keep_exif and had_exif and exif:
        save_kwargs['exif'] = exif

    # Attach (or explicitly not attach) the ICC profile.
    icc = get_suitable_icc(src_profile, img.mode, result_format)
    save_kwargs['icc_profile'] = icc

    tmp_buffer, ssim = encode_and_score(
        img, {**save_kwargs, **jpeg_quality_kwargs(img.mode, quality, jpeg_tables)},
        task, orig_size)

    if retry_with_standard(task.jpeg_tables, jpeg_tables, ssim, task.ssim_min):
        if not fixed_quality:
            quality, _ = jpeg_dynamic_quality(img, jpeg_tables='standard')
        tmp_buffer, ssim = encode_and_score(
            img, {**save_kwargs, **jpeg_quality_kwargs(img.mode, quality, 'standard')},
            task, orig_size)

    has_exif = bool(save_kwargs.get('exif'))

    return OptimizedImage(tmp_buffer, orig_format, result_format, orig_mode,
                          img.mode, 0, 0, was_downsized, had_exif, has_exif, ssim)
