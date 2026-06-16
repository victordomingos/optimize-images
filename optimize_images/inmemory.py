# encoding: utf-8
"""In-memory image optimization and conversion (bytes in, bytes out).

For callers that hold images as binary data rather than files - content
management systems, object storage, databases - and cannot provide a file
path. It reuses the very same per-format transforms as the file-based
optimizer and converter, so behavior (resizing, transparency, EXIF handling,
dynamic quality, target encoding options and the size-comparison rule) is
identical; only the source and the destination are an in-memory buffer instead
of the filesystem.

``optimize_image_data`` keeps the original format. ``convert_image_data``
changes it to another format (e.g. PNG to WebP); since there is no output file,
it returns the converted bytes and the resulting format in the result.
"""
from io import BytesIO
from typing import Tuple

from PIL import Image
from optimize_images.data_structures import Task, TaskResult
from optimize_images.formats import normalize_target
from optimize_images.img_aux_processing import is_worth_keeping
from optimize_images.img_convert import transform_convert
from optimize_images.img_optimize_jpg import transform_jpg
from optimize_images.img_optimize_png import transform_png
from optimize_images.img_optimize_webp import transform_webp

_SUPPORTED = {'JPEG', 'MPO', 'PNG', 'WEBP'}

# Canonical target name for a Pillow source format, to detect a conversion
# whose target equals the source (a no-op that should optimize in place).
_PIL_TO_CANON = {'PNG': 'png', 'JPEG': 'jpeg', 'MPO': 'jpeg', 'WEBP': 'webp'}


def _build_task(name: str, quality: int, remove_transparency: bool,
                reduce_colors: bool, max_colors: int, max_w: int, max_h: int,
                keep_exif: bool, bg_color: Tuple[int, int, int],
                grayscale: bool, ignore_size_comparison: bool,
                fast_mode: bool, webp_quality: int, webp_lossless: bool,
                webp_method: int) -> Task:
    return Task(
        src_path=name,
        quality=quality,
        remove_transparency=remove_transparency,
        reduce_colors=reduce_colors,
        max_colors=max_colors,
        max_w=max_w,
        max_h=max_h,
        keep_exif=keep_exif,
        convert_all=False,
        conv_big=False,
        force_del=False,
        bg_color=bg_color,
        grayscale=grayscale,
        no_size_comparison=ignore_size_comparison,
        fast_mode=fast_mode,
        output_config=None,
        convert_to='jpeg',
        webp_quality=webp_quality,
        webp_lossless=webp_lossless,
        webp_method=webp_method,
    )


def _skipped(name: str, fmt: str, mode: str, orig_size: int) -> TaskResult:
    return TaskResult(name, fmt, fmt, mode, mode, 0, 0, orig_size, orig_size,
                      False, False, False, False, None)


def optimize_image_data(
        data: bytes,
        *,
        name: str = '',
        quality: int = 80,
        remove_transparency: bool = False,
        reduce_colors: bool = False,
        max_colors: int = 256,
        max_w: int = 0,
        max_h: int = 0,
        keep_exif: bool = False,
        bg_color: Tuple[int, int, int] = (255, 255, 255),
        grayscale: bool = False,
        ignore_size_comparison: bool = False,
        fast_mode: bool = False,
        webp_quality: int = 80,
        webp_lossless: bool = False,
        webp_method: int = 6,
) -> Tuple[bytes, TaskResult]:
    """Optimize an image given as bytes and return ``(optimized_bytes, result)``.

    The original format is kept. ``optimized_bytes`` is the smaller image, or
    the original ``data`` unchanged when optimizing did not help (and the size
    comparison was not disabled). ``name`` is only a label for the result.
    Raises ``OSError`` if ``data`` is not a readable image.
    """
    orig_size = len(data)
    task = _build_task(name, quality, remove_transparency, reduce_colors,
                       max_colors, max_w, max_h, keep_exif, bg_color,
                       grayscale, ignore_size_comparison, fast_mode,
                       webp_quality, webp_lossless, webp_method)

    with Image.open(BytesIO(data)) as img:
        fmt = (img.format or '').upper()
        mode = img.mode
        if fmt not in _SUPPORTED:
            return data, _skipped(name, fmt, mode, orig_size)

        if fmt in ('JPEG', 'MPO'):
            opt = transform_jpg(img, task, orig_size)
        elif fmt == 'PNG':
            opt = transform_png(img, task)
        else:  # WEBP
            opt = transform_webp(img, task)
            if opt is None:  # animated WebP: leave untouched
                return data, _skipped(name, fmt, mode, orig_size)

    final_size = opt.buffer.getbuffer().nbytes
    compare_sizes = not ignore_size_comparison
    if is_worth_keeping(final_size, orig_size, compare_sizes):
        out_bytes = opt.buffer.getvalue()
        was_optimized = True
    else:
        out_bytes = data
        final_size = orig_size
        was_optimized = False

    result = TaskResult(name, opt.orig_format, opt.result_format,
                        opt.orig_mode, opt.result_mode, opt.orig_colors,
                        opt.final_colors, orig_size, final_size, was_optimized,
                        opt.was_downsized, opt.had_exif, opt.has_exif, None)
    return out_bytes, result


def convert_image_data(
        data: bytes,
        *,
        to: str = 'jpeg',
        name: str = '',
        quality: int = 80,
        remove_transparency: bool = False,
        max_w: int = 0,
        max_h: int = 0,
        keep_exif: bool = False,
        bg_color: Tuple[int, int, int] = (255, 255, 255),
        grayscale: bool = False,
        ignore_size_comparison: bool = False,
        webp_quality: int = 80,
        webp_lossless: bool = False,
        webp_method: int = 6,
) -> Tuple[bytes, TaskResult]:
    """Convert an in-memory image to another format: bytes in, bytes out.

    ``to`` is the target format (e.g. 'jpeg', 'png', 'webp', 'avif',
    'jpeg2000'); it is validated against the codecs available in the running
    Pillow build. Returns ``(out_bytes, result)``; check ``result.result_format``
    to know the format of ``out_bytes`` and store it accordingly.

    When converting would not shrink the image (and the size comparison is not
    disabled), the original bytes are returned unchanged, with the original
    format reported in the result. Converting to the source's own format is a
    no-op and falls back to in-place optimization. Multi-frame sources
    (animation/multipage) are returned unchanged. Raises ``ValueError`` for an
    unknown or unavailable target, and ``OSError`` if ``data`` is unreadable.
    """
    target = normalize_target(to)  # raises ValueError if unavailable
    orig_size = len(data)

    with Image.open(BytesIO(data)) as img:
        src_format = (img.format or '').upper()
        mode = img.mode

        # Converting to the source's own format is a no-op: optimize in place.
        if _PIL_TO_CANON.get(src_format) == target:
            return optimize_image_data(
                data, name=name, quality=quality,
                remove_transparency=remove_transparency, max_w=max_w,
                max_h=max_h, keep_exif=keep_exif, bg_color=bg_color,
                grayscale=grayscale,
                ignore_size_comparison=ignore_size_comparison,
                webp_quality=webp_quality, webp_lossless=webp_lossless,
                webp_method=webp_method)

        task = _build_task(name, quality, remove_transparency, False, 256,
                           max_w, max_h, keep_exif, bg_color, grayscale,
                           ignore_size_comparison, False, webp_quality,
                           webp_lossless, webp_method)
        task = task._replace(convert_to=target, convert_all=True)

        try:
            exif = img.getexif()
            had_exif = bool(exif and len(exif) > 0)
        except Exception:
            exif, had_exif = None, False

        opt = transform_convert(task, img, src_format, mode, had_exif, exif)
        if opt is None:  # multi-frame: leave untouched
            return data, _skipped(name, src_format, mode, orig_size)

    final_size = opt.buffer.getbuffer().nbytes
    compare_sizes = not ignore_size_comparison
    if is_worth_keeping(final_size, orig_size, compare_sizes):
        out_bytes = opt.buffer.getvalue()
        result = TaskResult(name, opt.orig_format, opt.result_format, mode,
                            opt.result_mode, 0, 0, orig_size, final_size, True,
                            opt.was_downsized, had_exif, opt.has_exif, None)
    else:
        # Not worth it: keep the original bytes (and the original format).
        out_bytes = data
        result = TaskResult(name, src_format, src_format, mode, mode, 0, 0,
                            orig_size, orig_size, False, opt.was_downsized,
                            had_exif, had_exif, None)
    return out_bytes, result
