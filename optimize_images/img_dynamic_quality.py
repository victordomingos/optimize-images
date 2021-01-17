"""
Adapted from:
https://engineeringblog.yelp.com/2017/06/making-photos-smaller.html
"""
from functools import lru_cache
from io import BytesIO
from typing import Optional, Tuple

from PIL import Image
from PIL import ImageChops, ImageStat
from math import log

from .constants import DEFAULT_QUALITY


def compare_images(img1: Image.Image, img2: Image.Image) -> Optional[float]:
    """Calculate the difference between two images of the same size
    by comparing channel values at the pixel level.
    `delete_diff_file`: removes the diff image after ratio found
    `diff_img_file`: filename to store diff image

    Adapted from Nicolas Hahn:
    https://github.com/nicolashahn/diffimg/blob/master/diffimg/__init__.py
    """

    # Don't compare if images are of different modes or different sizes.
    if (img1.mode != img2.mode) \
            or (img1.size != img2.size) \
            or (img1.getbands() != img2.getbands()):
        return None

    # Generate diff image in memory.
    diff_img = ImageChops.difference(img1, img2)
    # Calculate difference as a ratio.
    stat = ImageStat.Stat(diff_img)
    diff_ratio = sum(stat.mean) / (len(stat.mean) * 255)

    return diff_ratio * 100


def get_diff_at_quality(photo, quality: int) -> float:
    """Return a difference score for this JPEG image saved at the specified quality

    A SSIM score would be much better, but currently there is no pure Python
    implementation available.
    """
    diff_photo = BytesIO()
    # optimize is omitted here as it doesn't affect
    # quality but requires additional memory and cpu
    photo.save(diff_photo, format="JPEG", quality=quality, progressive=True)
    diff_photo.seek(0)
    diff_score = compare_images(photo, Image.open(diff_photo))

    # print("================> DIFF1 == DIFF2? ", diff_score==diff_score2)

    if diff_score < 0:
        return -1 + diff_score / 100
    else:
        return 1 - diff_score / 100


@lru_cache(maxsize=None)
def _diff_iteration_count(low: int, high: int) -> int:
    """Return the depth of the binary search tree for this range"""
    if low >= high:
        return 0
    else:
        return int(log(high - low, 2)) + 1


def jpeg_dynamic_quality(original_photo: Image.Image,
                         use_dynamic_quality: bool = True) -> Tuple[int, float]:
    """Return an integer representing the quality that this JPEG image should be
    saved at to attain the quality threshold specified for this photo class.

    Args:
        original_photo - a prepared PIL JPEG image (only JPEG is supported)
    """
    diff_goal = 0.992
    high = DEFAULT_QUALITY
    low = high - 5

    # working on a smaller size image doesn't give worse results but is faster
    # changing this value requires updating the calculated thresholds
    photo = original_photo.resize((400, 400))

    if not use_dynamic_quality:
        default_diff = get_diff_at_quality(photo, high)
        return high, default_diff

    # 95 is the highest useful value for JPEG. Higher values cause different behavior
    # Used to establish the image's intrinsic ssim without encoder artifacts
    normalized_diff = get_diff_at_quality(photo, 95)

    selected_quality = selected_diff = None

    # loop bisection. ssim/diff function increases monotonically so this will converge
    for _ in range(_diff_iteration_count(low, high)):
        curr_quality = (low + high) // 2
        curr_diff = get_diff_at_quality(photo, curr_quality)
        diff_ratio = curr_diff / normalized_diff

        if diff_ratio >= diff_goal:
            # continue to check whether a lower quality level also exceeds the goal
            selected_quality = curr_quality
            selected_diff = curr_diff
            high = curr_quality
        else:
            low = curr_quality

    if selected_quality:
        return selected_quality, selected_diff
    else:
        default_diff = get_diff_at_quality(photo, high)
        return high, default_diff
