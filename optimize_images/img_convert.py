# encoding: utf-8
"""Shared image-conversion helper.

Used by the per-format optimizers when the user asks to convert images to a
different output format. It honors the same common options as in-place
optimization (resize, grayscale, transparency, keep EXIF) and, crucially, the
size comparison: the converted file is written only when it is actually smaller
than the original, unless the user disabled the comparison.
"""
import os
from typing import Optional

from PIL import Image
from optimize_images.data_structures import Task, TaskResult, OptimizedImage
from optimize_images.formats import FORMATS
from optimize_images.jpeg_qtables import (jpeg_quality_kwargs, resolve_jpeg_tables,
                                          retry_with_standard)
from optimize_images.constants import DEFAULT_QUALITY
from optimize_images.img_aux_processing import (downsize_img, encode_and_score,
                                                make_grayscale,
                                                remove_transparency,
                                                save_compressed)
from optimize_images.img_icc import get_suitable_icc


def _to_8bit_grayscale(img: Image.Image) -> Image.Image:
    """Scale a 16-bit (or 32-bit 'I') grayscale image down to 8-bit 'L'.

    A direct conversion clips every sample above 255 to white; scaling divides
    each sample by 256 (so 0..65535 becomes 0..255). The image is first
    converted to the 32-bit 'I' mode, where every source mode ('I;16',
    'I;16B', 'I;16L', 'I') behaves the same, and the division is expressed as
    the linear scale 1/256, which Pillow evaluates in C (a // expression is
    not usable: Image.point probes the function with a scale/offset sentinel).
    """
    scaled = img.convert('I').point(lambda value: value / 256)
    return scaled.convert('L')


def _normalize_target(task: Task) -> str:
    target = (task.convert_to or 'jpeg').strip().lower()
    return 'jpeg' if target == 'jpg' else target


def _target_save_kwargs(target: str, task: Task,
                        image_mode: str, jpeg_tables: str = 'standard') -> dict:
    """Best-effort encoding parameters for each supported output format.

    *jpeg_tables* is the concrete table name for a JPEG target ('auto'
    already resolved).
    """
    info = FORMATS[target]
    kwargs = {'format': info.pil}
    if target == 'jpeg':
        quality = task.quality if task.quality is not None else DEFAULT_QUALITY
        kwargs.update(optimize=True, progressive=True)
        kwargs.update(jpeg_quality_kwargs(image_mode, quality, jpeg_tables))
    elif target == 'png':
        kwargs.update(optimize=True)
    elif target == 'webp':
        kwargs.update(quality=task.webp_quality, method=task.webp_method,
                      lossless=task.webp_lossless)
    elif target == 'avif':
        kwargs.update(quality=task.quality if task.quality is not None else DEFAULT_QUALITY)
    elif target == 'jpeg2000':
        kwargs.update(quality_mode='rates', quality_layers=[20])
    return kwargs


def transform_convert(task: Task, img, orig_format: str, orig_mode: str,
                      had_exif: bool = False,
                      exif=None,
                      *,
                      orig_size: int) -> Optional[OptimizedImage]:
    """Convert an already-open image to ``task.convert_to``, in memory.

    Pure: applies the common options (resize, transparency/alpha, grayscale,
    keep EXIF when the target supports it) and encodes to an in-memory buffer,
    without touching the filesystem and without closing ``img``. Returns None
    for multi-frame sources (animation/multipage), which are left as-is to
    avoid silently flattening them. 16-bit grayscale sources ('I;16',
    'I;16B', 'I;16L' and 'I') are scaled to 8-bit first, and CMYK sources are
    converted to RGB when the target cannot encode CMYK. Shared by the
    file-based converter and the in-memory API. ``orig_size`` is the source
    file size, used for the size-gated SSIM skip (it must match the size the
    keep/reject decision compares against).
    """
    target = _normalize_target(task)
    info = FORMATS[target]

    if getattr(img, 'n_frames', 1) > 1:
        return None

    # Read the source profile before any transforms (which create new
    # images without img.info).  The profile is matched against the
    # output mode, not the source mode.
    src_profile = img.info.get('icc_profile')
    # Same for the quantization tables, used by jpeg_tables='auto'.
    src_quantization = getattr(img, 'quantization', None)

    # 16-bit (and 32-bit 'I') grayscale must be scaled to 8 bits (v // 256);
    # a direct conversion would clip every sample above 255 to white. Done
    # before every other step so the resize, the transforms, the encoding and
    # the SSIM reference all operate on the same correct image.
    if img.mode in ('I;16', 'I;16B', 'I;16L', 'I'):
        img = _to_8bit_grayscale(img)

    if task.max_w or task.max_h:
        img, was_downsized = downsize_img(img, task.max_w, task.max_h)
    else:
        was_downsized = False

    if not info.supports_alpha:
        img = remove_transparency(img, task.bg_color).convert('RGB')
    elif task.remove_transparency:
        img = remove_transparency(img, task.bg_color)

    if task.grayscale:
        img = make_grayscale(img)

    # CMYK cannot be written as most formats (PNG and WebP raise OSError):
    # convert to RGB when the target is not JPEG, which does support CMYK.
    if img.mode == 'CMYK' and target != 'jpeg':
        img = img.convert('RGB')

    jpeg_tables = 'standard'
    if target == 'jpeg':
        quality = task.quality if task.quality is not None else DEFAULT_QUALITY
        jpeg_tables = resolve_jpeg_tables(task.jpeg_tables, src_quantization,
                                          quality, quality, was_downsized)

    extra_kwargs = {}
    if info.supports_exif and task.keep_exif and had_exif and exif:
        extra_kwargs['exif'] = exif

    # Attach (or explicitly not attach) the ICC profile.
    extra_kwargs['icc_profile'] = get_suitable_icc(src_profile, img.mode, info.pil)

    tmp_buffer, ssim = encode_and_score(
        img, {**_target_save_kwargs(target, task, img.mode, jpeg_tables), **extra_kwargs},
        task, orig_size)

    if retry_with_standard(task.jpeg_tables, jpeg_tables, ssim, task.ssim_min):
        tmp_buffer, ssim = encode_and_score(
            img, {**_target_save_kwargs(target, task, img.mode, 'standard'), **extra_kwargs},
            task, orig_size)

    has_exif = bool(extra_kwargs.get('exif'))

    return OptimizedImage(tmp_buffer, orig_format, info.pil, orig_mode,
                          img.mode, 0, 0, was_downsized, had_exif, has_exif, ssim)


def convert_image(task: Task, img, orig_format: str, orig_mode: str,
                  orig_size: int, had_exif: bool = False, exif=None) -> TaskResult:
    """Convert an already-open image to ``task.convert_to``.

    Multi-frame sources (animation/multipage) are skipped and kept as-is. The
    converted file is saved next to the original with the target extension; it
    replaces the original only if ``force_del`` is set.
    """
    opt = transform_convert(task, img, orig_format, orig_mode, had_exif, exif,
                            orig_size=orig_size)

    # Skip multi-frame sources to avoid silently flattening animations.
    if opt is None:
        img_mode = img.mode
        img.close()
        return TaskResult(task.src_path, orig_format, orig_format, orig_mode,
                          img_mode, 0, 0, orig_size, orig_size, False, False,
                          had_exif, had_exif, task.output_config, None)

    target = _normalize_target(task)
    info = FORMATS[target]
    folder, base = os.path.split(task.src_path)
    if folder == '':
        folder = os.getcwd()
    name = os.path.splitext(base)[0]
    output_path = os.path.join(folder, name + '.' + info.extensions[0])

    img.close()

    # Same rule as in-place optimization: keep only if smaller, unless the
    # user disabled the comparison.
    compare_sizes = not task.no_size_comparison
    was_optimized, final_size = save_compressed(task.src_path,
                                                opt.buffer,
                                                force_delete=task.force_del,
                                                compare_sizes=compare_sizes,
                                                output_path=output_path,
                                                ssim=opt.ssim,
                                                ssim_min=task.ssim_min)

    return TaskResult(task.src_path, orig_format, opt.result_format, orig_mode,
                      opt.result_mode, 0, 0, orig_size, final_size,
                      was_optimized, opt.was_downsized, had_exif, opt.has_exif,
                      task.output_config, opt.ssim)
