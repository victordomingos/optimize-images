# encoding: utf-8
"""Optional JPEG quantization tables for Pillow's encoder."""

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

# Registry: name → table (64 ints).
JPEG_TABLES = {'mozjpeg3': MOZJPEG_TABLE_3}

# Allowed table names (order determines iteration / CLI help).
JPEG_TABLE_NAMES = ('standard', 'mozjpeg3')


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
    subsampling ``'4:2:0'``.
    """
    kwargs: dict = {'quality': quality}

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
