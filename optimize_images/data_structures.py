import concurrent.futures

from typing import NamedTuple, Tuple, NewType

from PIL import Image


ImageType = NewType('ImageType', Image)
PPoolExType = NewType('PPoolExType', concurrent.futures.ProcessPoolExecutor)
TPoolExType = NewType('PPoolExType', concurrent.futures.ThreadPoolExecutor)


class Task(NamedTuple):
    src_path: str
    quality: int
    reduce_colors: bool
    max_colors: int
    max_w: int
    max_h: int
    keep_exif: bool
    conv_big: bool
    force_del: bool
    bg_color: Tuple[int, int, int]


class TaskResult(NamedTuple):
    img: str
    orig_format: str
    result_format: str
    orig_mode: str
    result_mode: str
    orig_colors: int
    final_colors: int
    orig_size: int
    final_size: int
    was_optimized: bool
    was_downsized: bool
    had_exif: bool
    has_exif: bool

