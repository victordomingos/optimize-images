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

from PIL import ImageFile
from optimize_images.data_structures import Task, TaskResult
from optimize_images.formats import FORMATS
from optimize_images.img_aux_processing import (downsize_img, make_grayscale,
                                                remove_transparency,
                                                save_compressed)


def _target_save_kwargs(target: str, task: Task) -> dict:
    """Best-effort encoding parameters for each supported output format."""
    info = FORMATS[target]
    kwargs = {'format': info.pil}
    if target == 'jpeg':
        kwargs.update(quality=task.quality, optimize=True, progressive=True)
    elif target == 'png':
        kwargs.update(optimize=True)
    elif target == 'webp':
        kwargs.update(quality=task.webp_quality, method=task.webp_method,
                      lossless=task.webp_lossless)
    elif target == 'avif':
        kwargs.update(quality=task.quality)
    elif target == 'jpeg2000':
        kwargs.update(quality_mode='rates', quality_layers=[20])
    return kwargs


def convert_image(task: Task, img, orig_format: str, orig_mode: str,
                  orig_size: int, had_exif: bool = False, exif=None) -> TaskResult:
    """Convert an already-open image to ``task.convert_to``.

    Multi-frame sources (animation/multipage) are skipped and kept as-is. The
    converted file is saved next to the original with the target extension; it
    replaces the original only if ``force_del`` is set.
    """
    target = (task.convert_to or 'jpeg').strip().lower()
    if target == 'jpg':
        target = 'jpeg'
    info = FORMATS[target]

    # Skip multi-frame sources to avoid silently flattening animations.
    if getattr(img, 'n_frames', 1) > 1:
        img_mode = img.mode
        img.close()
        return TaskResult(task.src_path, orig_format, orig_format, orig_mode,
                          img_mode, 0, 0, orig_size, orig_size, False, False,
                          had_exif, had_exif, task.output_config)

    folder, base = os.path.split(task.src_path)
    if folder == '':
        folder = os.getcwd()
    name = os.path.splitext(base)[0]
    output_path = os.path.join(folder, name + '.' + info.extensions[0])

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

    save_kwargs = _target_save_kwargs(target, task)
    if info.supports_exif and task.keep_exif and had_exif and exif:
        save_kwargs['exif'] = exif

    tmp_buffer = BytesIO()
    try:
        img.save(tmp_buffer, **save_kwargs)
    except IOError:
        ImageFile.MAXBLOCK = img.size[0] * img.size[1]
        img.save(tmp_buffer, **save_kwargs)

    has_exif = bool(save_kwargs.get('exif'))
    img_mode = img.mode
    img.close()

    # Same rule as in-place optimization: keep only if smaller, unless the
    # user disabled the comparison.
    compare_sizes = not task.no_size_comparison
    was_optimized, final_size = save_compressed(task.src_path,
                                                tmp_buffer,
                                                force_delete=task.force_del,
                                                compare_sizes=compare_sizes,
                                                output_path=output_path)

    return TaskResult(task.src_path, orig_format, info.pil, orig_mode,
                      img_mode, 0, 0, orig_size, final_size, was_optimized,
                      was_downsized, had_exif, has_exif, task.output_config)
