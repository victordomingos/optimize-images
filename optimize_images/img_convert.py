# encoding: utf-8
"""Shared image-conversion helper.

Used by the per-format optimizers when the user asks to convert images to a
different output format. It honors the same common options as in-place
optimization (resize, grayscale, transparency, keep EXIF) and, crucially, the
size comparison: the converted file is written only when it is actually smaller
than the original, unless the user disabled the comparison.
"""
import os
from io import BytesIO
from typing import Optional

from PIL import Image, ImageFile
from optimize_images.data_structures import Task, TaskResult, OptimizedImage
from optimize_images.formats import FORMATS
from optimize_images.constants import DEFAULT_QUALITY
from optimize_images.img_aux_processing import (downsize_img, make_grayscale,
                                                remove_transparency,
                                                save_compressed,
                                                ssim_needs_computing)
from optimize_images.img_icc import get_suitable_icc
from optimize_images.img_ssim import compute_ssim


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


def _target_save_kwargs(target: str, task: Task) -> dict:
    """Best-effort encoding parameters for each supported output format."""
    info = FORMATS[target]
    kwargs = {'format': info.pil}
    if target == 'jpeg':
        kwargs.update(quality=task.quality if task.quality is not None else DEFAULT_QUALITY,
                      optimize=True, progressive=True)
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

    save_kwargs = _target_save_kwargs(target, task)
    if info.supports_exif and task.keep_exif and had_exif and exif:
        save_kwargs['exif'] = exif

    # Attach (or explicitly not attach) the ICC profile.
    icc = get_suitable_icc(src_profile, img.mode, info.pil)
    save_kwargs['icc_profile'] = icc

    tmp_buffer = BytesIO()
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
