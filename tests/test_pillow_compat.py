#!/usr/bin/env python3
"""Pillow compatibility guards.

The project supports every Pillow release from the minimum in setup.py
(12.0.0) to the newest, and should keep working when the next major release
removes what is deprecated today. Two complementary checks:

* at run time, pytest.ini turns every DeprecationWarning into an error, so a
  deprecated call on a tested path fails the suite;
* here, a static scan finds Pillow APIs that are deprecated, already removed,
  or too new for the minimum version, also on paths the tests never execute.

Source: https://pillow.readthedocs.io/en/stable/deprecations.html
(checked 2026-10-02 for Pillow 12.3.0). Update the list when Pillow
deprecates something new, and drop entries that only guard the minimum
version when that minimum is raised. A line can opt out with the comment
``# pillow-compat: ok`` plus a reason.
"""
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCANNED = ["optimize_images", "tests", "benchmarks", "scripts"]
OPT_OUT = "pillow-compat: ok"

# (regex, why it is not allowed, what to use instead)
FORBIDDEN = [
    (r"\.getdata\(",
     "Image.getdata() is deprecated since Pillow 12.1 (removal planned)",
     "tobytes(), getcolors(), point() or getchannel()"),
    (r"\.get_flattened_data\(",
     "get_flattened_data() only exists since Pillow 12.1; the minimum "
     "supported version is 12.0",
     "tobytes(), getcolors(), point() or getchannel()"),
    (r"\.get_child_images\(",
     "Image.get_child_images() is removed in Pillow 13",
     "ImageFile.ImageFile.get_child_images()"),
    (r"\._show\(", "Image._show is removed in Pillow 13", "show()"),
    (r"\.product_(name|info)\b",
     "ImageCmsProfile.product_name/product_info are removed in Pillow 13",
     "ImageCms.getProfileDescription() and similar"),
    (r"\bisImageType\(", "Image.isImageType() was removed in Pillow 12",
     "isinstance(im, Image.Image)"),
    (r"ImageMath\.eval\(", "ImageMath.eval() was removed in Pillow 12",
     "ImageMath.lambda_eval()"),
    (r"IFD\.Makernote\b", "ExifTags.IFD.Makernote is deprecated",
     "ExifTags.IFD.MakerNote"),
    (r"\braise_oserror\b", "ImageFile.raise_oserror was removed in Pillow 12",
     "nothing (decoders raise by themselves)"),
    (r"huffman_(ac|dc)\b",
     "JpegImageFile.huffman_ac/dc were removed in Pillow 12", "nothing"),
    (r"""features\.check\(\s*['"](transp_webp|webp_mux|webp_anim)['"]""",
     "these WebP feature checks were removed in Pillow 12",
     'features.check("webp")'),
    (r"USE_CFFI_ACCESS|PyAccess", "PyAccess was removed in Pillow 11",
     "the C API (img.load())"),
]


def _python_files():
    for folder in SCANNED:
        yield from sorted((REPO_ROOT / folder).rglob("*.py"))


def _violations(pattern):
    regex = re.compile(pattern)
    for path in _python_files():
        if path == Path(__file__).resolve():
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        for number, line in enumerate(lines, 1):
            code = line.split("#", 1)[0]
            if regex.search(code) and OPT_OUT not in line:
                yield f"{path.relative_to(REPO_ROOT)}:{number}: {line.strip()}"


@pytest.mark.parametrize("pattern, why, instead", FORBIDDEN,
                         ids=[p for p, _, _ in FORBIDDEN])
def test_no_forbidden_pillow_api(pattern, why, instead):
    found = list(_violations(pattern))
    assert not found, (f"{why}; use {instead} instead:\n  "
                       + "\n  ".join(found))


def test_scan_covers_the_package():
    # Guard against the scan silently matching nothing (e.g. moved folders).
    files = [p.relative_to(REPO_ROOT).as_posix() for p in _python_files()]
    assert "optimize_images/img_aux_processing.py" in files
    assert "tests/test_cli.py" in files
