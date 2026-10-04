#!/usr/bin/env python3
"""Behavioural tests for CLI/API options that had no automated coverage.

Self-contained: every image is generated under pytest's ``tmp_path``.
None of these tests needs scikit-image.
"""
import io
import random
from importlib import metadata

import pytest
from PIL import Image

from optimize_images.api import PublicBatchOptions, optimize_as_batch, \
    optimize_image_data, optimize_single_image


def _photo(size=(320, 240), seed=1):
    """Gradients plus seeded noise: lossy encoders give clearly different
    sizes for different quality settings."""
    rng = random.Random(seed)
    width, height = size
    data = bytearray()
    for y in range(height):
        for x in range(width):
            noise = rng.randint(-20, 20)
            data += bytes((max(0, min(255, x * 255 // width + noise)),
                           max(0, min(255, y * 255 // height + noise)),
                           max(0, min(255, (x + y) * 127 // (width + height)
                                          + noise))))
    return Image.frombytes('RGB', size, bytes(data))


def _noise_png(path, size):
    """An RGB PNG with (almost) every pixel a different colour."""
    rng = random.Random(7)
    Image.frombytes('RGB', size, rng.randbytes(size[0] * size[1] * 3)) \
        .save(path, 'PNG')
    return path


def _encode(img, fmt, **save):
    buf = io.BytesIO()
    img.save(buf, fmt, **save)
    return buf.getvalue()


# --- -cb / conv_big: convert only big photographic PNGs -------------------

def test_conv_big_converts_big_photographic_png(tmp_path):
    # Thresholds (constants.py): area >= 800x600, > 2**16 colours, and a
    # JPEG preview bigger than 80 KB.
    src = _noise_png(tmp_path / "big.png", (900, 700))
    result = optimize_single_image(str(src), conv_big=True)
    assert result.was_optimized
    assert result.result_format == 'JPEG'
    assert (tmp_path / "big.jpg").exists()


def test_conv_big_leaves_small_png_as_png(tmp_path):
    src = _noise_png(tmp_path / "small.png", (200, 150))
    result = optimize_single_image(str(src), conv_big=True)
    assert result.result_format == 'PNG'
    assert not (tmp_path / "small.jpg").exists()


# --- force_del: remove the original after a successful conversion --------

def test_force_del_removes_original_after_conversion(tmp_path):
    src = tmp_path / "photo.png"
    _photo().save(src, 'PNG')
    result = optimize_single_image(str(src), convert_all=True, force_del=True)
    assert result.was_optimized
    assert (tmp_path / "photo.jpg").exists()
    assert not src.exists()


def test_force_del_keeps_original_when_conversion_is_rejected(tmp_path):
    # A tiny flat PNG converts to a bigger JPEG: the result is rejected, so
    # the original must survive and no converted file may be left behind.
    src = tmp_path / "flat.png"
    Image.new('RGB', (16, 16), (10, 20, 30)).save(src, 'PNG')
    before = src.read_bytes()
    result = optimize_single_image(str(src), convert_all=True, force_del=True)
    assert not result.was_optimized
    assert src.read_bytes() == before
    assert not (tmp_path / "flat.jpg").exists()


# --- recursive=False (-nr): only the top-level folder ---------------------

def test_non_recursive_batch_skips_subfolders(tmp_path):
    top = tmp_path / "top.jpg"
    nested_dir = tmp_path / "nested"
    nested_dir.mkdir()
    nested = nested_dir / "nested.jpg"
    for path in (top, nested):
        _photo().save(path, 'JPEG', quality=95)
    nested_before = nested.read_bytes()

    result = optimize_as_batch(PublicBatchOptions(src_path=str(tmp_path),
                                                  recursive=False, jobs=1))
    assert [r.img for r in result.results] == [str(top)]
    assert nested.read_bytes() == nested_before


# --- grayscale (-g) -------------------------------------------------------

@pytest.mark.parametrize("fmt", ['JPEG', 'PNG'])
def test_grayscale_output_is_single_channel(fmt):
    data = _encode(_photo(), fmt, **({'quality': 95} if fmt == 'JPEG' else {}))
    out, result = optimize_image_data(data, grayscale=True,
                                      ignore_size_comparison=True)
    assert result.was_optimized
    with Image.open(io.BytesIO(out)) as img:
        assert img.mode == 'L'
        assert img.format == fmt


def _rgba_photo(size=(96, 64)):
    """Colourful RGBA image: a fully transparent band, a half-transparent
    band and opaque pixels."""
    img = _photo(size).convert('RGBA')
    alpha = Image.new('L', size, 255)
    alpha.paste(0, (0, 0, size[0], size[1] // 4))
    alpha.paste(128, (0, size[1] // 4, size[0], size[1] // 2))
    img.putalpha(alpha)
    return img


def _palette_with_transparency(size=(96, 64), colors=64):
    """Colourful palette image whose index 0 is fully transparent."""
    img = _photo(size).quantize(colors)
    buf = io.BytesIO()
    img.save(buf, 'PNG', transparency=0)
    return buf.getvalue()


def _alpha(img):
    return img.convert('RGBA').getchannel('A').tobytes()


def _is_gray(img):
    rgb = img.convert('RGBA')
    r, g, b, _ = rgb.split()
    return r.tobytes() == g.tobytes() == b.tobytes()


def test_grayscale_rgba_keeps_transparency():
    # Plan 0.5: -g on RGBA goes through LA and back to RGBA.
    src = _rgba_photo()
    out, result = optimize_image_data(_encode(src, 'PNG'), grayscale=True,
                                      ignore_size_comparison=True)
    assert result.was_optimized
    with Image.open(io.BytesIO(out)) as img:
        assert _is_gray(img)
        assert _alpha(img) == _alpha(src)


def test_grayscale_palette_image_is_gray_and_keeps_transparency():
    # Plan 0.5: -g on a palette image turns every palette entry gray.
    data = _palette_with_transparency()
    with Image.open(io.BytesIO(data)) as src:
        src_alpha = _alpha(src)
        assert not _is_gray(src)
    out, result = optimize_image_data(data, grayscale=True,
                                      ignore_size_comparison=True)
    assert result.was_optimized
    with Image.open(io.BytesIO(out)) as img:
        assert _is_gray(img)
        assert _alpha(img) == src_alpha


@pytest.mark.parametrize("max_colors", [16, 64])
def test_reduce_colors_on_palette_image_respects_max_colors(max_colors):
    # Plan 0.8: -rc on an image that is already a palette image.
    data = _encode(_photo((96, 64)).quantize(200), 'PNG')
    out, result = optimize_image_data(data, reduce_colors=True,
                                      max_colors=max_colors,
                                      ignore_size_comparison=True)
    with Image.open(io.BytesIO(out)) as img:
        assert img.mode == 'P'
        assert len(img.getcolors()) <= max_colors
    assert result.final_colors <= max_colors


def _rc_source(source):
    """Palette (tRNS) or RGBA image with a small transparent area (~2% of the
    pixels, as in a logo or icon); "rgba_bands" adds large transparent and
    half-transparent bands."""
    if source == "rgba_bands":
        return _encode(_rgba_photo(), 'PNG')
    data = _palette_with_transparency()
    if source == "rgba":
        with Image.open(io.BytesIO(data)) as img:
            data = _encode(img.convert('RGBA'), 'PNG')
    return data


def _reduce(data, max_colors=16):
    out, result = optimize_image_data(data, reduce_colors=True,
                                      max_colors=max_colors,
                                      ignore_size_comparison=True)
    return out, result


@pytest.mark.parametrize("source", ["palette", "rgba"])
def test_reduce_colors_keeps_transparent_pixels(source):
    data = _rc_source(source)
    with Image.open(io.BytesIO(data)) as src:
        transparent = [i for i, a in enumerate(_alpha(src)) if a == 0]
    assert transparent
    out, _ = _reduce(data)
    with Image.open(io.BytesIO(out)) as img:
        alpha = _alpha(img)
    assert all(alpha[i] == 0 for i in transparent)


@pytest.mark.parametrize("source", ["palette", "rgba", "rgba_bands"])
def test_reduce_colors_keeps_exactly_the_invisible_pixels(source):
    # Fully transparent pixels stay fully transparent, and no visible pixel
    # (opaque or half-transparent) becomes invisible.
    data = _rc_source(source)
    with Image.open(io.BytesIO(data)) as src:
        before = [a == 0 for a in _alpha(src)]
    out, _ = _reduce(data)
    with Image.open(io.BytesIO(out)) as img:
        after = [a == 0 for a in _alpha(img)]
    assert after == before


@pytest.mark.parametrize("source", ["palette", "rgba"])
def test_reduce_colors_then_grayscale_keeps_the_invisible_pixels(source):
    # -g runs after -rc and rewrites the palette: the transparency set by
    # -rc must survive it (and the palette rebuild that follows).
    data = _rc_source(source)
    with Image.open(io.BytesIO(data)) as src:
        before = [a == 0 for a in _alpha(src)]
    out, _ = optimize_image_data(data, reduce_colors=True, max_colors=16,
                                 grayscale=True, ignore_size_comparison=True)
    with Image.open(io.BytesIO(out)) as img:
        assert _is_gray(img)
        assert [a == 0 for a in _alpha(img)] == before


def test_reduce_colors_keeps_partial_transparency():
    # Half-transparent pixels may have their alpha quantized, but they must
    # not all become opaque, and opaque pixels must stay opaque.
    src = _rgba_photo()
    before = _alpha(src)
    out, _ = _reduce(_encode(src, 'PNG'))
    with Image.open(io.BytesIO(out)) as img:
        after = _alpha(img)
    partial = [i for i, a in enumerate(before) if 0 < a < 255]
    still_partial = sum(1 for i in partial if 0 < after[i] < 255)
    assert still_partial >= len(partial) // 2
    assert all(after[i] == 255 for i, a in enumerate(before) if a == 255)


@pytest.mark.parametrize("source", ["palette", "rgba", "rgba_bands"])
def test_reduce_colors_with_transparency_keeps_the_picture(source):
    # The visible pixels must still look like the source: they use most of
    # the allowed colours, and the average colour error stays small.
    data = _rc_source(source)
    with Image.open(io.BytesIO(data)) as src:
        before = src.convert('RGBA').tobytes()
    out, _ = _reduce(data, max_colors=16)
    with Image.open(io.BytesIO(out)) as img:
        after = img.convert('RGBA').tobytes()
    visible = [i for i in range(0, len(before), 4) if before[i + 3] > 0]
    colours = {after[i:i + 3] for i in visible}
    assert len(colours) >= 8
    error = sum(abs(before[i + c] - after[i + c])
                for i in visible for c in range(3)) / (3 * len(visible))
    assert error < 20


@pytest.mark.parametrize("source", ["palette", "rgba", "rgba_bands"])
@pytest.mark.parametrize("max_colors", [2, 16, 64])
def test_reduce_colors_with_transparency_respects_max_colors(source,
                                                             max_colors):
    # The fully transparent entry counts towards -mc.
    out, result = _reduce(_rc_source(source), max_colors)
    with Image.open(io.BytesIO(out)) as img:
        assert img.mode == 'P'
        assert len(img.getcolors()) <= max_colors
    assert result.final_colors <= max_colors


def test_reduce_colors_keeps_partial_alpha_without_transparent_pixels():
    # RGBA with half-transparent pixels but none fully transparent: the
    # alpha must not be squared (the old composite turned 128 into 64).
    src = _rgba_photo()
    src.putalpha(src.getchannel('A').point(lambda a: max(a, 1)))
    out, _ = _reduce(_encode(src, 'PNG'), max_colors=64)
    with Image.open(io.BytesIO(out)) as img:
        alpha = _alpha(img)
    half = [alpha[i] for i, a in enumerate(_alpha(src)) if a == 128]
    assert abs(sum(half) / len(half) - 128) < 16


def test_reduce_colors_without_transparency_adds_none():
    # An opaque image must not gain a transparent palette entry.
    data = _encode(_photo((96, 64)), 'PNG')
    out, _ = _reduce(data)
    with Image.open(io.BytesIO(out)) as img:
        assert 'transparency' not in img.info
        assert set(_alpha(img)) == {255}


# --- -q / quality (plan 3.2) ----------------------------------------------

def test_quality_option_changes_jpeg_size():
    data = _encode(_photo((640, 480)), 'JPEG', quality=98)
    low, _ = optimize_image_data(data, quality=50,
                                 ignore_size_comparison=True)
    high, _ = optimize_image_data(data, quality=95,
                                  ignore_size_comparison=True)
    assert len(low) < len(high)


def test_quality_option_applies_in_fast_mode():
    data = _encode(_photo((640, 480)), 'JPEG', quality=98)
    low, _ = optimize_image_data(data, quality=50, fast_mode=True,
                                 ignore_size_comparison=True)
    high, _ = optimize_image_data(data, quality=95, fast_mode=True,
                                  ignore_size_comparison=True)
    assert len(low) < len(high)


@pytest.fixture
def dynamic_quality_calls(monkeypatch):
    from optimize_images import img_optimize_jpg
    calls = []
    original = img_optimize_jpg.jpeg_dynamic_quality

    def counting(*args, **kwargs):
        calls.append(1)
        return original(*args, **kwargs)

    monkeypatch.setattr(img_optimize_jpg, "jpeg_dynamic_quality", counting)
    return calls


def test_quality_default_is_none_in_public_api():
    import inspect
    from optimize_images.api import convert_image_data
    assert PublicBatchOptions(src_path='.').quality is None
    for func in (optimize_single_image, optimize_image_data,
                 convert_image_data):
        assert inspect.signature(func).parameters['quality'].default is None


def test_explicit_quality_is_used_without_fast_mode(dynamic_quality_calls):
    data = _encode(_photo(), 'JPEG', quality=98)
    fixed, _ = optimize_image_data(data, quality=60,
                                   ignore_size_comparison=True)
    assert not dynamic_quality_calls
    fast, _ = optimize_image_data(data, quality=60, fast_mode=True,
                                  ignore_size_comparison=True)
    assert fixed == fast


def test_default_quality_stays_dynamic(dynamic_quality_calls):
    data = _encode(_photo(), 'JPEG', quality=98)
    optimize_image_data(data, ignore_size_comparison=True)
    assert len(dynamic_quality_calls) == 1


def test_fast_mode_without_quality_uses_80():
    data = _encode(_photo(), 'JPEG', quality=98)
    default, _ = optimize_image_data(data, fast_mode=True,
                                     ignore_size_comparison=True)
    explicit, _ = optimize_image_data(data, quality=80, fast_mode=True,
                                      ignore_size_comparison=True)
    assert default == explicit


def test_conversion_to_jpeg_without_quality_uses_80():
    from optimize_images.api import convert_image_data
    data = _encode(_photo(), 'PNG')
    default, _ = convert_image_data(data, to='jpeg',
                                    ignore_size_comparison=True)
    explicit, _ = convert_image_data(data, to='jpeg', quality=80,
                                     ignore_size_comparison=True)
    assert default == explicit


def _cli_quality(tmp_path, monkeypatch, *extra):
    # Checked on the parsed arguments: a subprocess (or a process pool)
    # cannot be monkeypatched to observe the quality actually used.
    from optimize_images.argument_parser import get_args
    monkeypatch.setattr('sys.argv', ['optimize-images', *extra, str(tmp_path)])
    return get_args()[3]


def test_cli_without_quality_passes_none(tmp_path, monkeypatch):
    # Without -q the CLI must hand "not given" (None) to the batch, so JPEG
    # files keep the automatic quality.
    assert _cli_quality(tmp_path, monkeypatch) is None


def test_cli_passes_given_quality(tmp_path, monkeypatch):
    assert _cli_quality(tmp_path, monkeypatch, '-q', '65') == 65


def test_cli_rejects_quality_zero(tmp_path):
    from helpers import run_cli
    (tmp_path / 'photo.jpg').write_bytes(_encode(_photo(), 'JPEG', quality=95))
    proc = run_cli('-q', '0', str(tmp_path))
    assert "between 1 and 100" in proc.stderr + proc.stdout


# --- packaging ------------------------------------------------------------

def test_console_script_entry_point():
    # The tests run the CLI as "python -m optimize_images"; this checks that
    # the declared "optimize-images" command (setup.py console_scripts, as
    # seen by importlib.metadata) still points to the same entry function.
    try:
        dist = metadata.distribution('optimize-images')
    except metadata.PackageNotFoundError:
        pytest.skip("optimize-images is not installed in this venv")
    scripts = {ep.name: ep.value for ep in dist.entry_points
               if ep.group == 'console_scripts'}
    assert scripts.get('optimize-images') == 'optimize_images.__main__:main'
