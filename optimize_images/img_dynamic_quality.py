"""
Adapted from:
https://engineeringblog.yelp.com/2017/06/making-photos-smaller.html
"""
from io import BytesIO
from PIL import Image
from math import log

#from optimize_images.img_comparison import compare_images


def get_diff_at_quality(photo, quality):
    """Return the ssim for this JPEG image saved at the specified quality"""
    diff_photo = BytesIO()
    # optimize is omitted here as it doesn't affect
    # quality but requires additional memory and cpu
    photo.save(diff_photo, format="JPEG", quality=quality, progressive=True)
    diff_photo.seek(0)
    diff_score = compare_images(photo, Image.open(diff_photo))
    return diff_score


def _diff_iteration_count(lo, hi):
    """Return the depth of the binary search tree for this range"""
    if lo >= hi:
        return 0
    else:
        return int(log(hi - lo, 2)) + 1


def jpeg_dynamic_quality(original_photo):
    """Return an integer representing the quality that this JPEG image should be
    saved at to attain the quality threshold specified for this photo class.

    Args:
        original_photo - a prepared PIL JPEG image (only JPEG is supported)
    """
    diff_goal = 0.95
    hi = 85
    lo = 80

    # working on a smaller size image doesn't give worse results but is faster
    # changing this value requires updating the calculated thresholds
    photo = original_photo.resize((400, 400))

    if not _should_use_dynamic_quality():
        default_ssim = get_diff_at_quality(photo, hi)
        return hi, default_ssim

    # 95 is the highest useful value for JPEG. Higher values cause different behavior
    # Used to establish the image's intrinsic ssim without encoder artifacts
    normalized_diff = get_diff_at_quality(photo, 95)
    selected_quality = selected_diff = None

    # loop bisection. ssim function increases monotonically so this will converge
    for i in range(_diff_iteration_count(lo, hi)):
        curr_quality = (lo + hi) // 2
        curr_diff = get_diff_at_quality(photo, curr_quality)
        diff_ratio = curr_diff / normalized_diff

        if diff_ratio >= diff_goal:
            # continue to check whether a lower quality level also exceeds the goal
            selected_quality = curr_quality
            selected_diff = curr_diff
            hi = curr_quality
        else:
            lo = curr_quality

    if selected_quality:
        return selected_quality, selected_diff
    else:
        default_diff = get_diff_at_quality(photo, hi)
        return hi, default_diff
