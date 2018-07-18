from PIL import Image, ImageChops


def compare_images(image1: str, image2: str):
    """Compute percentage of difference between 2 JPEG images of same size.
    Alternatively, compare two bitmaps as defined in basic bitmap storage.
    Useful for comparing two JPEG images saved with a different compression
    ratios.

    Adapted from:
    http://rosettacode.org/wiki/Percentage_difference_between_images#Python

    :param image1: a string with the path of a JPG image file
    :param image2: a string with the path of a JPG image file
    :return: A float with the percentage of differene, or None if images are
    not directly comparable.
    """
    img1 = Image.open(image1)
    img2 = Image.open(image2)

    # Don't compare if images are of different modes or different sizes.
    if (img1.mode != img2.mode) or (img1.size != img2.size):
        return None

    pairs = zip(img1.getdata(), img2.getdata())
    if len(img1.getbands()) == 1:
        # for gray-scale jpegs
        dif = sum(abs(p1 - p2) for p1, p2 in pairs)
    else:
        dif = sum(abs(c1 - c2) for p1, p2 in pairs for c1, c2 in zip(p1, p2))

    ncomponents = img1.size[0] * img1.size[1] * 3
    return (dif / 255.0 * 100) / ncomponents  # Difference (percentage)

