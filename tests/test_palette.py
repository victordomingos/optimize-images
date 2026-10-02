#!/usr/bin/env python3
"""rebuild_palette must be exact: a palette with only the colours the image
uses, and the image must look exactly the same (plan F2).

The rebuilt image is checked directly (not the saved PNG): Pillow 12.0/12.1
pad the palette when writing, so the PLTE length on disk is not a reliable
measure. Whether the smaller file is kept is the size check's job.
"""
import pytest
from PIL import Image

from optimize_images.img_aux_processing import rebuild_palette


def _palette_image(used, size=(64, 48), transparency=None):
    """A P image with a full 256-entry palette of which `used` are used."""
    img = Image.new('P', size)
    # Odd, off-grid channel values: none of them is in Pillow's fixed web
    # palette, so a re-quantizing rebuild cannot keep them by chance.
    img.putpalette([((i * 37 + c * 91) % 256) | 1 for i in range(256)
                    for c in range(3)])
    width, height = size
    img.frombytes(bytes(((x + y) % used) * (256 // used)
                        for y in range(height) for x in range(width)))
    if transparency is not None:
        img.info['transparency'] = transparency
    return img


CASES = {
    'few_colours': _palette_image(4),
    'some_colours': _palette_image(40),
    'tRNS_bytes': _palette_image(
        10, transparency=bytes([0, 128] + [255] * 254)),
    'tRNS_index': _palette_image(10, transparency=0),
    'all_256': _palette_image(256),
}

PARAMS = list(CASES)


def _rgba(img):
    return img.convert('RGBA').tobytes()


@pytest.mark.parametrize("name", PARAMS)
def test_rebuild_palette_keeps_every_pixel(name):
    src = CASES[name]
    out, _ = rebuild_palette(src.copy())
    assert out.mode == 'P'
    assert _rgba(out) == _rgba(src)


@pytest.mark.parametrize("name", PARAMS)
def test_rebuild_palette_keeps_only_used_colours(name):
    src = CASES[name]
    used = len(src.getcolors(256))
    out, reported = rebuild_palette(src.copy())
    assert len(out.getpalette()) // 3 == used
    assert reported == used


# --- Edge cases found in review (2026-10-02) -------------------------------

def _off_grid(used=12):
    img = _palette_image(used, size=(32, 32))
    return img


def _rgba_palette_image():
    """A P image whose palette itself carries alpha (palette mode RGBA), as
    produced by quantizing an RGBA image (e.g. -rc on a transparent PNG)."""
    rgba = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
    rgba.paste((200, 40, 30, 255), (0, 8, 32, 24))
    rgba.paste((20, 90, 200, 128), (8, 0, 24, 32))
    img = rgba.quantize(8)
    assert img.palette.mode == 'RGBA'
    return img


EDGE_CASES = {
    # A PNG tRNS chunk usually lists alpha only for the first entries.
    'tRNS_bytes_shorter_than_palette': lambda: _with_trns(
        _off_grid(), bytes([0, 128, 64])),
    # The transparent index may point to an entry no pixel uses.
    'tRNS_index_unused': lambda: _with_trns(_off_grid(), 200),
    'palette_with_alpha': _rgba_palette_image,
}


def _with_trns(img, transparency):
    img.info['transparency'] = transparency
    return img


@pytest.mark.parametrize("name", EDGE_CASES)
def test_rebuild_palette_edge_cases_keep_every_pixel(name):
    src = EDGE_CASES[name]()
    out, reported = rebuild_palette(src.copy())
    assert out.mode == 'P'
    assert _rgba(out) == _rgba(src)
    assert reported == len(src.getcolors(256))


def test_optimize_png_with_short_trns_chunk():
    import io
    from optimize_images.api import optimize_image_data
    img = _off_grid()
    buf = io.BytesIO()
    img.save(buf, 'PNG', transparency=bytes([0, 128, 64]))
    data = buf.getvalue()
    out, _ = optimize_image_data(data, ignore_size_comparison=True)
    with Image.open(io.BytesIO(data)) as before, \
            Image.open(io.BytesIO(out)) as after:
        assert _rgba(after) == _rgba(before)


def test_reduce_colors_keeps_transparency():
    import io
    from optimize_images.api import optimize_image_data
    rgba = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    rgba.paste((200, 40, 30, 255), (0, 20, 64, 44))
    buf = io.BytesIO()
    rgba.save(buf, 'PNG')
    out, _ = optimize_image_data(buf.getvalue(), reduce_colors=True,
                                 max_colors=16, ignore_size_comparison=True)
    with Image.open(io.BytesIO(out)) as img:
        assert img.convert('RGBA').getpixel((0, 0))[3] == 0


# --- Compact PLTE + tRNS in the saved PNG (plan 6.4, option c) -------------
# PNG stores a palette as colours (PLTE) plus, optionally, one alpha per entry
# (tRNS) that may stop after the last non-opaque entry. Writing it that way
# gives the smallest file on every Pillow version; Pillow 12.0/12.1 write 3
# extra PLTE entries for palettes kept in RGBA form.

def _chunk_sizes(data):
    import struct
    sizes, pos = {}, 8
    while pos < len(data):
        length, kind = struct.unpack(">I4s", data[pos:pos + 8])
        sizes[kind.decode("latin-1")] = length
        pos += 12 + length
    return sizes


def _transparent_png(colours=10):
    import io
    rgba = Image.new("RGBA", (60, 40), (0, 0, 0, 0))
    for i in range(colours - 1):
        alpha = 255 if i % 3 else 128
        rgba.paste(((i * 53) % 256 | 1, (i * 97) % 256 | 1, 200, alpha),
                   (i * 6, 10, i * 6 + 6, 30))
    buf = io.BytesIO()
    rgba.save(buf, "PNG")
    return buf.getvalue()


def test_reduce_colors_writes_compact_plte_and_trns():
    import io
    from optimize_images.api import optimize_image_data
    out, _ = optimize_image_data(_transparent_png(), reduce_colors=True,
                                 max_colors=10, ignore_size_comparison=True)
    with Image.open(io.BytesIO(out)) as img:
        assert img.mode == "P"
        used = len(img.getcolors(256))
        alphas = img.convert("RGBA").getchannel("A")
        non_opaque = len({c for _, c in img.getcolors(256)
                          if img.getpalette("RGBA")[4 * c + 3] < 255})
    sizes = _chunk_sizes(out)
    assert sizes["PLTE"] // 3 == used
    # Non-opaque entries first, so tRNS stops right after them.
    assert sizes.get("tRNS", 0) == non_opaque
    assert alphas.getextrema()[0] < 255


def test_reduce_colors_keeps_pixels_and_alpha_in_saved_png():
    # -rc changes colours by design; the palette rebuild after it must not.
    # fast_mode skips the rebuild, so it gives the reference pixels.
    import io
    from optimize_images.api import optimize_image_data
    data = _transparent_png()
    out, _ = optimize_image_data(data, reduce_colors=True, max_colors=10,
                                 ignore_size_comparison=True)
    ref, _ = optimize_image_data(data, reduce_colors=True, max_colors=10,
                                 fast_mode=True, ignore_size_comparison=True)
    with Image.open(io.BytesIO(ref)) as expected, \
            Image.open(io.BytesIO(out)) as img:
        assert _rgba(img) == _rgba(expected)


def test_compact_palette_raises_no_pillow_warning():
    import io
    import warnings
    from optimize_images.api import optimize_image_data
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        optimize_image_data(_transparent_png(), reduce_colors=True,
                            max_colors=10, ignore_size_comparison=True,
                            show_ssim=True)
