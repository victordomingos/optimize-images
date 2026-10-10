# encoding: utf-8
"""Optional JPEG quantization tables for Pillow's encoder."""
from functools import lru_cache
from typing import Mapping, Optional, Sequence

# From mozjpeg jcparam.c (table index 3).  Copyright (c) Mozilla and
# contributors.  IJG License / BSD-3-Clause (see mozjpeg LICENSE.md).
# This is the quality-50 base table.
# Attributed in jcparam.c to a proposal on the ImageMagick forum,
# usually credited to Nicolas Robidoux.
MOZJPEG_TABLE_3 = (
    16, 16, 16, 18, 25, 37, 56, 85,
    16, 17, 20, 27, 34, 40, 53, 75,
    16, 20, 24, 31, 43, 62, 91, 135,
    18, 27, 31, 40, 53, 74, 106, 156,
    25, 34, 43, 53, 69, 94, 131, 189,
    37, 40, 62, 74, 94, 124, 169, 238,
    56, 53, 91, 106, 131, 169, 226, 311,
    85, 75, 135, 156, 189, 238, 311, 418,
)

# The standard tables (JPEG spec Annex K, the libjpeg default, used by
# Pillow), quality-50 base, natural order.
STANDARD_LUMA = (
    16, 11, 10, 16, 24, 40, 51, 61,
    12, 12, 14, 19, 26, 58, 60, 55,
    14, 13, 16, 24, 40, 57, 69, 56,
    14, 17, 22, 29, 51, 87, 80, 62,
    18, 22, 37, 56, 68, 109, 103, 77,
    24, 35, 55, 64, 81, 104, 113, 92,
    49, 64, 78, 87, 103, 121, 120, 101,
    72, 92, 95, 98, 112, 100, 103, 99,
)
STANDARD_CHROMA = (
    17, 18, 24, 47, 99, 99, 99, 99,
    18, 21, 26, 66, 99, 99, 99, 99,
    24, 26, 56, 99, 99, 99, 99, 99,
    47, 66, 99, 99, 99, 99, 99, 99,
    99, 99, 99, 99, 99, 99, 99, 99,
    99, 99, 99, 99, 99, 99, 99, 99,
    99, 99, 99, 99, 99, 99, 99, 99,
    99, 99, 99, 99, 99, 99, 99, 99,
)

# Registry: name → table (64 ints).
JPEG_TABLES = {'mozjpeg3': MOZJPEG_TABLE_3}

# Allowed table names (order determines iteration / CLI help).
JPEG_TABLE_NAMES = ('auto', 'standard', 'mozjpeg3')

# 'auto' keeps the standard tables when the source JPEG already uses them at
# a quality from the lowest quality that may be used up to this many steps
# above the highest one: re-encoding with the same tables at about the same
# quality is almost lossless, while switching tables re-quantizes the image.
# Measured with SSIMULACRA 2 (benchmarks/results/mozjpeg-qtables): sources at
# q75-85 lose 2.6-7.4 points with mozjpeg3 under automatic quality (75-80);
# below or above that window mozjpeg3 is as good or better, and smaller.
AUTO_STANDARD_MARGIN = 5


def _scaled(base: Sequence[int], quality: int) -> tuple:
    """libjpeg's jpeg_quality_scaling + jpeg_add_quant_table (baseline)."""
    scale = 5000 // quality if quality < 50 else 200 - quality * 2
    return tuple(min(max((value * scale + 50) // 100, 1), 255) for value in base)


@lru_cache(maxsize=None)
def _standard_tables(quality: int) -> tuple:
    return _scaled(STANDARD_LUMA, quality), _scaled(STANDARD_CHROMA, quality)


def standard_tables_quality(quantization: Optional[Mapping[int, Sequence[int]]]) -> Optional[int]:
    """Return the quality whose standard tables match *quantization*.

    *quantization* is Pillow's ``JpegImageFile.quantization`` (table id →
    64 values, natural order). Returns ``None`` when the source has no
    tables or uses other tables (cameras, Adobe, mozjpeg, ...).
    """
    if not quantization or not set(quantization) <= {0, 1}:
        return None
    tables = {k: tuple(v) for k, v in quantization.items()}
    for quality in range(1, 101):
        luma, chroma = _standard_tables(quality)
        if tables.get(0) == luma and tables.get(1, chroma) == chroma:
            return quality
    return None


def resolve_jpeg_tables(jpeg_tables: str,
                        source_quantization: Optional[Mapping[int, Sequence[int]]],
                        min_quality: int, max_quality: int,
                        resized: bool = False) -> str:
    """Turn 'auto' into a concrete table name for one image.

    'auto' gives 'standard' when the source JPEG uses the standard tables at
    a quality from *min_quality* to *max_quality* + AUTO_STANDARD_MARGIN and
    was not resized; otherwise 'mozjpeg3'. Other names are returned as given.
    """
    if jpeg_tables != 'auto':
        return jpeg_tables
    if not resized:
        source_quality = standard_tables_quality(source_quantization)
        if (source_quality is not None
                and min_quality <= source_quality <= max_quality + AUTO_STANDARD_MARGIN):
            return 'standard'
    return 'mozjpeg3'


def retry_with_standard(requested: str, used: str, ssim: Optional[float],
                        ssim_min: Optional[float]) -> bool:
    """Whether an 'auto' result encoded with mozjpeg3 should be redone
    with the standard tables because it failed the SSIM gate.

    SSIM scores the mozjpeg table slightly lower than the standard one for
    a perceptually similar result, so without this retry a strict
    --ssim-min would keep the whole original where the standard tables
    pass. With the retry, 'auto' is never worse than 'standard' under the
    gate.
    """
    return (requested == 'auto' and used == 'mozjpeg3'
            and ssim_min is not None and ssim is not None and ssim < ssim_min)


# ── API ─────────────────────────────────────────────────────────────────────

def validate_jpeg_tables(jpeg_tables: str) -> None:
    """Raise ``ValueError`` if *jpeg_tables* is not a recognised name."""
    if jpeg_tables not in JPEG_TABLE_NAMES:
        raise ValueError(
            f"Unknown JPEG table: {jpeg_tables!r}. "
            f"Allowed names: {JPEG_TABLE_NAMES}")


def jpeg_quality_kwargs(mode: str, quality: int,
                        jpeg_tables: str = 'standard') -> dict:
    """Build ``save_kwargs`` for ``PIL.Image.save()`` for JPEG.

    ``jpeg_tables='standard'`` returns only ``{'quality': quality}``.
    Named tables install quantization table(s) and, for RGB/YCbCr,
    subsampling ``'4:2:0'``. 'auto' must be resolved first
    (``resolve_jpeg_tables``).
    """
    kwargs: dict = {'quality': quality}

    if jpeg_tables == 'auto':
        raise ValueError("'auto' JPEG tables must be resolved before encoding")

    if jpeg_tables == 'standard':
        return kwargs

    table = JPEG_TABLES.get(jpeg_tables)
    if table is None:
        raise ValueError(
            f"Unknown JPEG table: {jpeg_tables!r}. "
            f"Allowed names: {JPEG_TABLE_NAMES}")

    if mode == 'L':
        kwargs['qtables'] = [table]
    elif mode in ('RGB', 'YCbCr'):
        kwargs['qtables'] = [table, table]
        kwargs['subsampling'] = '4:2:0'

    return kwargs
