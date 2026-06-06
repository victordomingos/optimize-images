# encoding: utf-8

from PIL import features


def _webp_supported() -> bool:
    """True only if the installed Pillow can actually decode/encode WebP.

    Pillow built without libwebp recognizes the format but cannot open it,
    so we must not advertise WebP support that does not exist.
    """
    try:
        return bool(features.check("webp"))
    except Exception:
        return False


WEBP_SUPPORTED = _webp_supported()

# ============================[ General settings ]============================
# The list of input formats reflects the codecs actually present in the Pillow
# build in use (see optimize_images.formats), so discovery and the --supported
# listing never advertise something that cannot be handled.
from optimize_images.formats import available_input_formats  # noqa: E402

SUPPORTED_FORMATS = available_input_formats()
DEFAULT_QUALITY = 80
DEFAULT_WEBP_QUALITY = 80
DEFAULT_WEBP_METHOD = 6
DEFAULT_BG_COLOR = (255, 255, 255)
MIN_BIG_IMG_SIZE = 80_000
MIN_BIG_IMG_AREA = 800 * 600

# ====================[ iOS/Pythonista specific settings ]====================
IPAD_FONT_SIZE = 15
IPHONE_FONT_SIZE = 10
IOS_WORKERS = 2
IOS_FONT = "Menlo"
