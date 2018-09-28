"""
Adapted from:
https://engineeringblog.yelp.com/2017/06/making-photos-smaller.html
"""
from io import BytesIO
from math import log
from optimize_images.constants import DEFAULT_QUALITY
import numpy as np


try:
    from PIL import Image
except ImportError:
    msg = 'This application requires Pillow to be installed. Please, install it first.'
    raise ImportError(msg)


def compare_images(img1: str, img2: str):
    """Compute percentage of difference between 2 JPEG images of same size
    (using the sum of absolute differences). Alternatively, compare two bitmaps
    as defined in basic bitmap storage. Useful for comparing two JPEG images
    saved with a different compression ratios.

    Adapted from:
    http://rosettacode.org/wiki/Percentage_difference_between_images#Python

    :param img1: an Image object
    :param img2: an Image object
    :return: A float with the percentage of difference, or None if images are
    not directly comparable.
    """

    # Don't compare if images are of different modes or different sizes.
    if (img1.mode != img2.mode) \
            or (img1.size != img2.size) \
            or (img1.getbands() != img2.getbands()):
        return None

    pairs = zip(img1.getdata(), img2.getdata())
    if len(img1.getbands()) == 1:
        # for gray-scale jpegs
        dif = sum(abs(p1 - p2) for p1, p2 in pairs)
    else:
        dif = sum(abs(c1 - c2) for p1, p2 in pairs for c1, c2 in zip(p1, p2))

    ncomponents = img1.size[0] * img1.size[1] * 3
    return (dif / 255.0 * 100) / ncomponents  # Difference (percentage)


def compare_images_np(img1: str, img2: str):
    """Compute percentage of difference between 2 JPEG images of same size
    (using the sum of absolute differences). Alternatively, compare two bitmaps
    as defined in basic bitmap storage. Useful for comparing two JPEG images
    saved with a different compression ratios.

    Adapted from:
     - http://rosettacode.org/wiki/Percentage_difference_between_images#Python
     - https://stackoverflow.com/a/1927689

    :param img1: an Image object
    :param img2: an Image object
    :return: A float with the percentage of difference, or None if images are
    not directly comparable.
    """

    # Don't compare if images are of different modes or different sizes.
    if (img1.mode != img2.mode) \
            or (img1.size != img2.size) \
            or (img1.getbands() != img2.getbands()):
        return None

    dif = 0
    for band_index, band in enumerate(img1.getbands()):
        m1 = np.array([p[band_index] for p in img1.getdata()]).reshape(*img1.size)
        m2 = np.array([p[band_index] for p in img2.getdata()]).reshape(*img2.size)
        dif += np.sum(np.abs(m1-m2))

    ncomponents = img1.size[0] * img1.size[1] * 3
    return (dif / 255.0 * 100) / ncomponents  # Difference (percentage)


def get_diff_at_quality(photo, quality):
    """Return a difference score for this JPEG image saved at the specified quality

    A SSIM score would be much better, but currently there is no pure Python
    implementation available.
    """
    diff_photo = BytesIO()
    # optimize is omitted here as it doesn't affect
    # quality but requires additional memory and cpu
    photo.save(diff_photo, format="JPEG", quality=quality, progressive=True)
    diff_photo.seek(0)
    #diff_score = compare_images(photo, Image.open(diff_photo))
    diff_score = compare_images_np(photo, Image.open(diff_photo))

    """
    if diff_score != diff_score_np:
        print("Oh boy!", diff_score, type(diff_score), diff_score_np, type(diff_score_np))
        exit()
    else:
        print("Yeah!", diff_score, type(diff_score), diff_score_np, type(diff_score_np))
    """

    if diff_score < 0:
        return -1 + diff_score / 100
    else:
        return 1 - diff_score / 100


def _diff_iteration_count(lo, hi):
    """Return the depth of the binary search tree for this range"""
    if lo >= hi:
        return 0
    else:
        return int(log(hi - lo, 2)) + 1


def jpeg_dynamic_quality(original_photo, use_dynamic_quality=True):
    """Return an integer representing the quality that this JPEG image should be
    saved at to attain the quality threshold specified for this photo class.

    Args:
        original_photo - a prepared PIL JPEG image (only JPEG is supported)
    """
    diff_goal = 0.992
    hi = DEFAULT_QUALITY
    lo = hi - 5

    # working on a smaller size image doesn't give worse results but is faster
    # changing this value requires updating the calculated thresholds
    photo = original_photo.resize((400, 400))


    if not use_dynamic_quality:
        default_diff = get_diff_at_quality(photo, hi)
        return hi, default_diff

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
        # print(f"CURR:{curr_diff}   NORM:{normalized_diff}     RATIO:{diff_ratio}  HI:{hi} LO:{lo}")

    if selected_quality:
        # print(f"Selected quality: {selected_quality}     Selected diff:", selected_diff) #debug
        return selected_quality, selected_diff
    else:
        default_diff = get_diff_at_quality(photo, hi)
        # print(f"Using HI:{hi}     Default diff:", default_diff) #debug
        return hi, default_diff
