#!/usr/bin/env python3
"""Public API contract checks.

These guard properties of the public API that callers depend on and that should
hold across releases: the conversion-related parameters stay keyword-only with
defaults (so older positional calls never break), converting defaults to JPEG,
an unknown target is rejected clearly, and the public result keeps exposing its
documented fields. The checks are tolerant of *additive* evolution (new
parameters, new result fields) and only fail on changes that would actually
break existing callers (a parameter becoming positional, a field disappearing,
the default conversion or error contract changing).

Self-contained: generates its own image under pytest's ``tmp_path``. Runs with
the rest of the suite via ``pytest tests/``.
"""
import inspect

import pytest
from PIL import Image

from optimize_images.api import optimize_single_image, PublicTaskResult
from optimize_images.data_structures import Task

# Parameters that must remain keyword-only-with-default so that positional
# calls written for older versions keep working.
ADDITIVE_KEYWORD_PARAMS = ["convert_to", "webp_quality", "webp_lossless",
                           "webp_method"]

# Fields the public result must keep exposing. Extra fields are fine (additive);
# a missing field is a breaking change.
REQUIRED_RESULT_FIELDS = {
    "img", "orig_format", "result_format", "orig_mode", "result_mode",
    "orig_colors", "final_colors", "orig_size", "final_size", "was_optimized",
    "was_downsized", "had_exif", "has_exif",
}


def _result_fields(obj):
    fields = getattr(obj, "__dataclass_fields__", None)
    if fields is not None:
        return set(fields)
    return set(getattr(obj, "_fields", ()))


@pytest.mark.parametrize("name", ADDITIVE_KEYWORD_PARAMS)
def test_conversion_param_is_keyword_only_with_default(name):
    par = inspect.signature(optimize_single_image).parameters[name]
    assert par.kind is inspect.Parameter.KEYWORD_ONLY
    assert par.default is not inspect.Parameter.empty


def test_conversion_defaults_to_jpeg(tmp_path):
    png = tmp_path / 'x.png'
    Image.new('RGBA', (200, 200), (10, 20, 30, 128)).save(png)
    result = optimize_single_image(str(png), quality=80, convert_all=True)
    assert result.result_format == 'JPEG'


def test_invalid_convert_to_raises_valueerror(tmp_path):
    png = tmp_path / 'x.png'
    Image.new('RGBA', (200, 200), (10, 20, 30, 128)).save(png)
    with pytest.raises(ValueError):
        optimize_single_image(str(png), convert_all=True, convert_to='gif')


def test_public_result_exposes_required_fields():
    # Subset check: tolerant of new fields, fails if any documented field is
    # removed or renamed.
    assert REQUIRED_RESULT_FIELDS <= _result_fields(PublicTaskResult)


def test_task_builds_with_defaults_for_conversion_fields():
    # The conversion-related fields must have defaults, so building a Task
    # without them keeps working as the structure grows. We assert the
    # behaviour (defaults exist and apply), not a fixed field count.
    defaults = Task._field_defaults
    for name in ADDITIVE_KEYWORD_PARAMS:
        assert name in defaults, f"{name} should have a default"
    assert defaults["convert_to"] == "jpeg"

    minimal = Task("p", 80, False, False, 256, 0, 0, False, False, False,
                   False, (255, 255, 255), False, False, False, None)
    assert minimal.convert_to == "jpeg"


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main(["-v", "--color=yes", __file__]))