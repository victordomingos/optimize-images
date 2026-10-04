# encoding: utf-8
import os
from io import BytesIO
from typing import Optional, Tuple

from PIL import Image

from .constants import DEFAULT_BG_COLOR
from .reporting import show_img_exception


class Palette:
    def __init__(self):
        self.palette = []

    def add(self, red, green, blue):
        # map rgb tuple to colour index
        rgb = red, green, blue
        try:
            return self.palette.index(rgb)
        except ValueError as vex:
            i = len(self.palette)
            if i >= 256:
                raise RuntimeError("all palette entries are used") from vex
            self.palette.append(rgb)
            return i

    def get_palette(self):
        # return flattened palette
        palette = []
        for red, green, blue in self.palette:
            palette = palette + [red, green, blue]
        return palette


def remove_transparency(
        img: Image.Image,
        bg_color: Tuple[int, int, int] = DEFAULT_BG_COLOR) -> Image.Image:
    """Remove alpha transparency from PNG images

    Expects a PIL.Image object and returns an object of the same type with the
    changes applied.

    Special thanks to Yuji Tomita and Takahashi Shuuji
    (https://stackoverflow.com/a/33507138)
    """
    if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
        orig_image = img.convert('RGBA')
        background = Image.new('RGBA', orig_image.size, bg_color)
        img = Image.alpha_composite(background, orig_image)
        return img.convert("RGB")
    else:
        return img


def downsize_img(img: Image.Image,
                 max_width: int,
                 max_height: int) -> Tuple[Image.Image, bool]:
    """ Reduce the size of an image to the indicated maximum dimensions

    This function takes a PIL.Image object and integer values for the maximum
    allowed width and height (a zero value means no maximum constraint),
    calculates the size that meets those constraints and resizes the image. The
    resize is done in place, changing the original object. Returns a boolean
    indicating if the image was changed.
    """
    width, height = img.size
    # Assume 0 as current size
    if not max_width:
        max_width = width
    if not max_height:
        max_height = height

    if (max_width, max_height) == (width, height):  # If no changes, do nothing
        return img, False

    img.thumbnail((max_width, max_height), resample=Image.LANCZOS)
    return img, True


def do_reduce_colors(img: Image.Image,
                     max_colors: int) -> Tuple[Image.Image, int, int]:
    """ Reduce the number of colors of an Image object

    It takes a PIL image object and tries to reduce the total number of colors,
    converting it to an indexed color (mode P) image. If the input image is in
    mode 1, it cannot be further reduced, so it's returned back with no
    changes.

    For images with fully transparent pixels (alpha == 0), one palette entry
    is reserved for full transparency (which counts toward -mc).  The
    algorithm quantizes visible pixels as RGBA (preserving partial alpha for
    half-transparent pixels) and stores the per-entry alphas as bytes in
    ``img.info[\"transparency\"]``, so that subsequent transforms
    (grayscale, palette rebuild) can honour them.

    :param img: a PIL image in color (modes P, RGBA, RGB, CMYK, YCbCr, LAB or HSV)
    :param max_colors: an integer indicating the maximum number of colors allowed.
    :return: a PIL image in mode P (or mode 1, as stated above), an integer
             indicating the original number of colors (0 if source is not a
             mode P or mode 1 image) and an integer stating the resulting
             number of colors.
    """
    orig_mode = img.mode

    if orig_mode == "1":
        return img, 2, 2

    colors = img.getcolors()
    if colors:
        orig_colors = len(colors)
    else:
        orig_colors = 0

    # Intermediate conversion steps when needed
    if orig_mode in ["CMYK", "YCbCr", "LAB", "HSV"]:
        img = img.convert("RGB")
    elif orig_mode == "LA":
        img = img.convert("RGBA")

    # Actual colour reduction (RGBA is quantized as-is so its alpha
    # channel is preserved — an earlier composite would have multiplied
    # alpha by itself, e.g. 128→64, which we avoid by quantizing the
    # RGBA image directly).  For CMYK/YCbCr/LAB/HSV we convert to RGB;
    # for RGB/L/RGBA/P we set the palette.
    if orig_mode in ["CMYK", "YCbCr", "LAB", "HSV"]:
        palette = Image.ADAPTIVE
    elif orig_mode in ["RGB", "L"]:
        palette = Image.ADAPTIVE
    elif orig_mode == "RGBA":
        palette = Image.ADAPTIVE
    elif orig_mode == "LA":
        palette = Image.ADAPTIVE
    elif orig_mode == "P":
        palette = img.getpalette()
        img = img.convert("RGBA")

    # --- transparent-aware path (only when source RGBA, LA or P) ---------
    if orig_mode in ("RGBA", "LA", "P"):
        # The image was converted to RGBA (from LA or P) and quantized
        # as RGBA so its per-pixel alpha is preserved.  Check whether the
        # image has any fully transparent pixel (alpha == 0).
        alpha = img.getchannel('A')  # mode L
        if alpha.getextrema()[0] == 0:
            return _reduce_colors_keeping_transparency(
                img, alpha, max_colors, orig_colors
            )
        # No fully transparent pixels: standard opaque path (byte-for-byte).
        img = img.convert("P", palette=palette, colors=max_colors)
        return img, orig_colors, len(img.getcolors())

    img = img.convert("P", palette=palette, colors=max_colors)
    return img, orig_colors, len(img.getcolors())


def _reduce_colors_keeping_transparency(
        rgba: Image.Image,
        alpha: Image.Image,
        max_colors: int,
        orig_colors: int
) -> Tuple[Image.Image, int, int]:
    """Reduce colours of a RGBA image while keeping transparency.

    Fully transparent pixels (alpha == 0) are preserved by reserving one
    palette entry for them (which counts toward -mc).  The algorithm:

    1. Mask: 255 where alpha == 0 (transparent → fill), else 0.
    2. Get the average visible colour by converting to RGB, resizing to
       1×1 with Image.BOX (averages all visible pixels).
    3. Paste (average + (255,)) into a copy of the image using the mask,
       so fully-transparent pixels become opaque copies of the average.
    4. Quantize the working image to max(1, max_colors - 1) colours;
       quantize on an RGBA image preserves per-pixel alpha in the RGBA
       palette, so half-transparent pixels keep their partial alpha.
    5. Extend the RGB palette by one entry (0, 0, 0) as the transparent
       colour, and remap all fully-transparent pixels to that index.
    6. Store the per-entry alphas as bytes in info["transparency"] so
       that subsequent transforms (grayscale, palette rebuild) can honour
       them.

    :param rgba: a PIL Image in mode RGBA (may have alpha 0, 128, 255).
    :param alpha: the alpha channel (mode L), already extracted.
    :param max_colors: the maximum number of colours (0 … 256).
    :param orig_colors: the original colour count (for the return value).
    :return: (quantized image in mode P, orig_colors, final colour count).
    """
    # a) invisible: 255 where alpha == 0 (transparent → paint), else 0.
    invisible = alpha.point(lambda a: 255 if a == 0 else 0)

    # b) Compute the average visible colour.  Convert to RGB (dropping
    #    alpha), resize to 1×1 with Image.BOX (averages), and create a
    #    full-size solid RGBA image with that colour.
    visible = rgba.copy()
    fill_rgb = rgba.convert("RGB").resize((1, 1), Image.BOX)
    fill_rgba = Image.new(
        "RGBA", rgba.size, fill_rgb.getpixel((0, 0))
    )
    visible.paste(fill_rgba, mask=invisible)

    # c) Quantize visible pixels to max(1, max_colors - 1) colours.
    #    Quantize on an RGBA image creates a 4-byte RGBA palette that
    #    preserves per-pixel alpha for every entry (half-transparent
    #    pixels keep their partial alpha).
    quantized = visible.quantize(
        max(1, max_colors - 1), method=Image.Quantize.FASTOCTREE
    )

    # d) Read its palette with getpalette(rawmode="RGBA"); n = number of
    #    entries; alphas = the 4th byte of each entry followed by one 0
    #    byte (the last index, reserved for full transparency).
    rgba_pal = list(quantized.getpalette(rawmode="RGBA"))
    n = len(rgba_pal) // 4  # max_colors - 1 (before adding the transparent entry)
    alphas = bytes(rgba_pal[i * 4 + 3] for i in range(n)) + bytes([0])

    # e) Extend the RGBA palette by one entry (0, 0, 0, 0) as the
    #    transparent colour, and remap all fully transparent pixels to
    #    that index.
    rgba_pal.extend([0, 0, 0, 0])  # last entry (index n, fully transparent)
    quantized.putpalette(rgba_pal, rawmode="RGBA")

    # f) quantized.paste(n, mask=invisible) - only the fully transparent
    #    pixels get entry n; no other remapping.
    quantized.paste(n, mask=invisible)

    # g) quantized.info["transparency"] = alphas (bytes) — one alpha
    #    value per palette index (n opaque/partial entries + 1 transparent
    #    entry at index n).  This works with both RGB and RGBA palettes,
    #    so -g and the palette rebuild honour it.
    quantized.info["transparency"] = alphas

    # h) return quantized, orig_colors, len(quantized.getcolors()).
    return quantized, orig_colors, len(quantized.getcolors())


def make_grayscale(img: Image.Image) -> Image.Image:
    """ Convert an Image to grayscale

    :param img: a PIL image in color (modes P, RGBA, RGB, CMYK, YCbCr, LAB or HSV)
    :return: a PIL image object in modes P, L or RGBA, if converted, or the
             original Image object in case no conversion is done.
    """
    orig_mode = img.mode

    if orig_mode in ["RGB", "CMYK", "YCbCr", "LAB", "HSV"]:
        return img.convert("L")
    elif orig_mode == "RGBA":
        return img.convert("LA").convert("RGBA")
    elif orig_mode == "P":
        # Using ITU-R 601-2 luma transform:  L = R * 299/1000 + G * 587/1000 + B * 114/1000
        pal = img.getpalette()
        for i in range(len(pal) // 3):
            # Using ITU-R 601-2 luma transform
            gray = (pal[3 * i] * 299 + pal[3 * i + 1] * 587 + pal[3 * i + 2] * 114)
            gray = gray // 1000
            pal[3 * i: 3 * i + 3] = [gray, gray, gray]
        img.putpalette(pal)
        return img
    else:
        return img


def rebuild_palette(img: Image.Image) -> Tuple[Image.Image, int]:
    """Rebuild the palette of a mode "P" image.

    Removes unused palette entries, orders every non-opaque (alpha < 255)
    entry before the opaque ones, stores the palette as plain RGB and
    writes the alphas into ``img.info["transparency"]`` as a bytes object
    (one byte per non-opaque entry).  Pixel indices are remapped so the
    image looks identical.  Works on a copy so the caller's original is
    untouched.

    :param img: a mode "P" image
    :return: a tuple composed by a mode "P" image object and an integer
             with the resulting number of colours used in the image
    """
    img = img.copy()

    colors_list = img.getcolors(256)
    if colors_list is None:
        return img, 0  # more than 256 colours: nothing to reduce.

    # Collect the used palette indices (sorted for determinism).
    old_indices = sorted(c[1] for c in colors_list)
    n = len(old_indices)

    # ------------------------------------------------------------------
    # Figure out (R, G, B, A) for every used palette index, regardless
    # of how Pillow stored the alpha on this image (RGBA palette, bytes
    # in info["transparency"], or a single int index).
    # ------------------------------------------------------------------
    palette_mode = img.palette.mode if img.palette else None  # 'RGB' or 'RGBA'
    bytes_per_entry = 4 if palette_mode == 'RGBA' else 3
    full_palette = img.getpalette(rawmode=palette_mode)

    # Map old palette index → (r, g, b, a).
    index_rgba: dict[int, tuple[int, int, int, int]] = {}
    for old_idx in old_indices:
        start = old_idx * bytes_per_entry
        r = full_palette[start]
        g = full_palette[start + 1]
        b = full_palette[start + 2]
        a = full_palette[start + 3] if palette_mode == 'RGBA' else 255
        index_rgba[old_idx] = (r, g, b, a)

    # Override alphas from ``img.info["transparency"]`` when the palette
    # itself does not carry alpha (or carries incomplete alpha).
    if "transparency" in img.info:
        trns = img.info["transparency"]
        if isinstance(trns, bytes):
            for old_idx in old_indices:
                if old_idx < len(trns):
                    r, g, b, _ = index_rgba[old_idx]
                    index_rgba[old_idx] = (r, g, b, trns[old_idx])
        elif isinstance(trns, int) and trns in index_rgba:
            r, g, b, _ = index_rgba[trns]
            index_rgba[trns] = (r, g, b, 0)

    # ------------------------------------------------------------------
    # Reorder: non-opaque entries first, then opaque ones.
    # ------------------------------------------------------------------
    indexed = list(enumerate(old_indices))  # (local position, old_idx)
    indexed.sort(key=lambda pair: (
        index_rgba[old_indices[pair[0]]][3] == 255,  # False < True: non-opaque first
        pair[0],  # keep original sorted order within each group
    ))

    # Build old index → new position in the reordered list.
    old_to_new = {
        old_indices[indexed[i][0]]: i for i in range(n)
    }

    # Build the new RGB palette and collect non-opaque alphas.
    new_rgb: list[int] = []
    non_opaque_alphas: list[int] = []
    for new_pos in range(n):
        old_idx = old_indices[indexed[new_pos][0]]
        r, g, b, a = index_rgba[old_idx]
        new_rgb.extend((r, g, b))
        if a < 255:
            non_opaque_alphas.append(a)

    # Store palette as plain RGB and non-opaque alphas as tRNS bytes.
    img.putpalette(new_rgb, rawmode="RGB")
    if non_opaque_alphas:
        img.info["transparency"] = bytes(non_opaque_alphas)
    elif "transparency" in img.info:
        del img.info["transparency"]

    # Remap pixel indices: point() applies the 256-entry lookup in C.
    lut = [old_to_new.get(i, i) for i in range(256)]
    img = img.point(lut)

    return img, n


def is_at_least_1pct_smaller(final_size: int, orig_size: int) -> bool:
    """Whether the result is at least ~1% smaller than the original.

    Single home of the 1% size rule: it decides the size part of
    is_worth_keeping and the SSIM-skip decision in the transforms, so the
    two cannot drift apart.
    """
    return orig_size > 0 and final_size / orig_size < .99


def is_worth_keeping(final_size: int, orig_size: int,
                     compare_sizes: bool,
                     ssim: Optional[float] = None,
                     ssim_min: Optional[float] = None) -> bool:
    """Whether an optimized result should replace the original.

    The rule (shared by the file-based optimizers and the in-memory API): a
    minimum SSIM threshold is an independent quality gate - reject when it is
    set and the result's score is below it (or missing) - and otherwise keep
    it if the size comparison is disabled, or if it is at least ~1% smaller.
    """
    if ssim_min is not None and (ssim is None or ssim < ssim_min):
        return False
    return (not compare_sizes) or is_at_least_1pct_smaller(final_size,
                                                           orig_size)


def ssim_needs_computing(ssim_min: Optional[float], show_ssim: bool,
                         compare_sizes: bool, final_size: int,
                         orig_size: int) -> bool:
    """Whether the (expensive) SSIM must be computed for an encoded result.

    The score is computed whenever it is requested (a minimum threshold
    and/or --show-ssim), except one safe case: with a minimum threshold set
    but no --show-ssim, the score exists only to gate the keep/reject
    decision - and that decision is already a rejection when the size
    comparison is enabled and the result is not at least ~1% smaller. There
    the score is skipped and stays None, which the gate treats as a
    rejection (it fails closed), so the decision is unchanged; with
    --show-ssim, or when the size comparison is disabled, the score is
    always computed.
    """
    if ssim_min is None and not show_ssim:
        return False
    return not (ssim_min is not None and not show_ssim and compare_sizes
                and not is_at_least_1pct_smaller(final_size, orig_size))


def save_compressed(src_path: str,
                    tmp_buffer: BytesIO,
                    compare_sizes: bool,
                    force_delete: bool = False,
                    output_path: str = '',
                    ssim: Optional[float] = None,
                    ssim_min: Optional[float] = None) -> Tuple[bool, int]:
    """ Check if there were any savings and save or discard temporary file.

        If the user used the option to ignore the file comparison, go ahead
        and replace the original file anyway. A minimum SSIM threshold, when
        given, acts as an independent quality gate on top of the size rule.
    """
    final_size = tmp_buffer.getbuffer().nbytes
    orig_size: int = os.path.getsize(src_path)

    target_path = output_path if output_path else src_path

    if is_worth_keeping(final_size, orig_size, compare_sizes,
                        ssim=ssim, ssim_min=ssim_min):
        tmp_buffer.seek(0)
        with open(target_path, 'wb') as file:
            file.write(tmp_buffer.getbuffer())

        was_optimized = True
        if force_delete:
            try:
                os.remove(src_path)
            except OSError as osex:
                details = 'Error while removing original file.'
                show_img_exception(osex, src_path, details)
    else:
        # Keep original file
        final_size = orig_size
        was_optimized = False

    return was_optimized, final_size