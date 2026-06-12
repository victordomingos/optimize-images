# encoding: utf-8
import os
import platform
import re
import sys
from argparse import ArgumentParser
from importlib.metadata import version, PackageNotFoundError

from optimize_images import __version__
from optimize_images.constants import DEFAULT_QUALITY, DEFAULT_WEBP_QUALITY, \
    DEFAULT_WEBP_METHOD, SUPPORTED_FORMATS
from optimize_images.data_structures import OutputConfiguration
from optimize_images.formats import available_output_formats
from optimize_images.metadata import inspect_image
from optimize_images.exif_format import format_exif


def get_version_info() -> str:
    """Returns a string with the current application version and environment info."""

    pillow_version = _get_package_version(
        "Pillow",
        fallback="not found"
    )
    watchdog_version = _get_package_version(
        "watchdog",
        fallback="missing (package needed for watching folders for changes)"
    )
    python_version = (
        f"Python {platform.python_version()}"
        f"{' (free-threaded)' if _is_free_threaded() else ''}"
        f" ({sys.executable})"
    )

    return (
        f"\nOptimize Images {__version__}"
        f"\n\nRunning environment:"
        f"\n  - Location: {sys.argv[0]}"
        f"\n  - Pillow {pillow_version}"
        f"\n  - {python_version}"
        f"\n\nOptional packages:"
        f"\n  - Watchdog {watchdog_version}\n\n"
    )


def _is_free_threaded() -> bool:
    """Returns True if running on a free-threaded (GIL-disabled) Python build."""
    if hasattr(sys, "_is_gil_enabled"):
        return not sys._is_gil_enabled()
    return False


def _get_package_version(package: str, fallback: str = "unknown") -> str:
    """Returns the installed version of a package, or the fallback string."""
    try:
        return version(package)
    except PackageNotFoundError:
        return fallback


def get_formats() -> str:
    """ Get a string that displays a list of supported formats. """
    formats = ', '.join(SUPPORTED_FORMATS).strip().upper()
    msg = "These are the image formats currently supported (please " \
          "note that any files without one of these file extensions " \
          "will be ignored):"
    return f"\n{msg} {formats}\n\n"


def _tagged(formats: str, text: str) -> str:
    """Prefix an option's help text with the image formats it affects.

    The bracketed tag (e.g. "[JPEG, WebP]" or "[ALL]") lets users see at a
    glance which formats each option applies to, now that the options are
    grouped by function rather than by format.
    """
    return f"[{formats}] {text}"


def _handle_info(args, parser) -> None:
    """Print metadata for a single image and exit.

    Info mode is exclusive: only the image path may accompany it, so any other
    option is rejected.
    """
    allowed = {'-i', '--info'}
    extras = [a for a in sys.argv[1:] if a.startswith('-') and a not in allowed]
    if extras:
        parser.exit(status=2, message="\nThe --info option must be used on its "
                    "own, with only the path of the image to inspect.\n\n")
    if not args.path:
        parser.exit(status=2,
                    message="\nPlease specify the path of the image to "
                            "inspect.\n\n")

    path = os.path.expanduser(args.path)
    try:
        meta = inspect_image(path)
    except FileNotFoundError:
        parser.exit(status=2, message=f"\nFile not found: {path}\n\n")
    except (OSError, ValueError) as ex:
        parser.exit(status=2, message=f"\nCould not read image: {ex}\n\n")
    print(_format_metadata(meta))
    parser.exit(status=0)


def _format_metadata(meta) -> str:
    lines = [f"\nImage: {meta.path}"]

    def row(label, value):
        lines.append(f"  {label + ':':<14}{value}")

    row("Format", meta.image_format or "unknown")
    row("Mode", meta.mode)
    row("Dimensions", f"{meta.width} x {meta.height} px")
    if meta.palette_colors is not None:
        row("Palette", f"{meta.palette_colors} colors")
    row("Alpha", "yes" if meta.has_alpha else "no")
    if meta.is_progressive is not None:
        row("Progressive", "yes" if meta.is_progressive else "no")
    if meta.is_interlaced is not None:
        row("Interlaced", "yes" if meta.is_interlaced else "no")
    if meta.n_frames > 1:
        row("Frames", f"{meta.n_frames} (animated)")
    if meta.dpi is not None:
        row("DPI", f"{meta.dpi[0]:g} x {meta.dpi[1]:g}")
    row("ICC profile", meta.icc_profile_description
        or ("yes" if meta.has_icc_profile else "no"))

    lines.append("")
    formatted = format_exif(meta.exif)
    if formatted:
        titles = {'image': 'Image', 'camera': 'Camera', 'gps': 'GPS'}
        for section, tags in formatted.items():
            lines.append(f"EXIF / {titles.get(section, section.title())}:")
            for name, value in tags.items():
                lines.append(f"  {name + ':':<22}{value}")
            lines.append("")
    else:
        lines.append("EXIF: (none)")
        lines.append("")
    return "\n".join(lines)


def get_args():
    desc = 'A command-line utility written in pure Python to reduce the file ' \
           'size of images. You must explicitly pass it a path to the image ' \
           'file or to the directory containing the image files to be ' \
           'processed.'
    epilog = "PLEASE NOTE: The operation is done DESTRUCTIVELY, " \
             "by replacing the original files with the processed ones. You " \
             "definitely should duplicate the original file or folder before " \
             "using this utility, in order to be able to recover any damaged " \
             "images that don't have the desired quality. When doing format " \
             "conversion, if a JPEG with the same name already exists, it " \
             "be replaced by the JPEG file resulting from that conversion."
    parser = ArgumentParser(description=desc, epilog=epilog)

    path_help = 'The path to the image file or to the folder containing the ' \
                'images to be optimized. By default, it will try to process ' \
                'any images found in all of its subdirectories.'
    parser.add_argument('path', nargs="?", type=str, help=path_help)

    parser.add_argument('-v', '--version', action='store_true',
                        help="Check the version of this app and its environment.")

    sf_help = 'Display the list of image formats currently supported.'
    parser.add_argument('-s', '--supported', dest="supported_formats",
                        action='store_true', help=sf_help)

    info_help = 'Show metadata for a single image (format, mode, dimensions, ' \
                'alpha, palette, progressive/interlaced, frames, DPI, ICC ' \
                'profile and EXIF) and exit. Must be used on its own, with ' \
                'only the image path; it cannot be combined with any other ' \
                'option.'
    parser.add_argument('-i', '--info', action='store_true', help=info_help)

    parser.add_argument('-nr', '--no-recursion', action='store_true',
                        help="Don't recurse through subdirectories.")

    parser.add_argument('-wd', '--watch-directory', action='store_true',
                        help='Watch a directory continuously for new files and '
                             'optimize any file as soon as it is created (file '
                             'paths are saved in a temporary list, so that each '
                             'file should just be processed once per session).')

    jobs_help = 'The max. number of simultaneous jobs to run at a given time. ' \
                'The default value (0), for most platforms, will generate a ' \
                'total of N + 1 processes, where N is the number of CPUs or ' \
                'cores in the system.'

    parser.add_argument('-jobs', dest="jobs",
                        type=int, default=0, help=jobs_help)

    only_summary_help = 'Show only the summary'
    parser.add_argument('--only-summary', action='store_true', help=only_summary_help)

    only_progress_help = 'Show only the current progress'
    parser.add_argument('--only-progress', action='store_true', help=only_progress_help)

    quiet_help = 'Quiet mode, output nothing'
    parser.add_argument('--quiet', action='store_true', help=quiet_help)

    proc_msg = 'Image processing options, grouped by function. The bracketed ' \
               'tag on each option shows which image formats it affects ' \
               '([ALL] means JPEG, PNG and WebP).'
    general_group = parser.add_argument_group(
        'Resizing and general options'.upper(), description=proc_msg)

    mw_help = 'The maximum width (in pixels).'
    general_group.add_argument('-mw', dest="max_width",
                               type=int, default=0,
                               help=_tagged('ALL', mw_help))

    mh_help = "The maximum height (in pixels). Any image that has a dimension " \
              "exceeding a specified value will be downsized as the first " \
              "optimization step. The resizing will not take effect if, " \
              "after the whole optimization process, the resulting file " \
              "size isn't any smaller than the original."
    general_group.add_argument('-mh', dest="max_height",
                               type=int, default=0,
                               help=_tagged('ALL', mh_help))

    general_group.add_argument('-g', '--grayscale', action='store_true',
                               help=_tagged('ALL', "Convert to grayscale."))

    nc_help = "Don't compare the original and resulting file sizes, and save " \
              "the new image anyway (useful, for instance, if you prefer to " \
              "have all images with the same color, size, or quality settings)."
    general_group.add_argument('-nc', '--no-comparison', action='store_true',
                               help=_tagged('ALL', nc_help))

    fm_help = 'Skip some actions (e.g., the final palette rebuild for indexed ' \
              'PNG images, or the variable JPEG quality setting) in order to ' \
              'finish faster.'
    general_group.add_argument('-fm', '--fast-mode', action='store_true',
                               help=_tagged('JPEG, PNG', fm_help))

    enc_group = parser.add_argument_group(
        'Quality and encoding options'.upper())

    q_help = 'Specify a fixed quality setting for JPEG files (an integer ' \
             'value, between 1 and 100).'
    enc_group.add_argument('-q', dest='quality',
                           type=int, help=_tagged('JPEG', q_help))

    wq_help = 'Quality setting for WebP files (an integer between 1 and 100). ' \
              'Defaults to 80. In lossless mode it controls the compression ' \
              'effort instead.'
    enc_group.add_argument('-wq', dest='webp_quality',
                           type=int, default=None,
                           help=_tagged('WebP', wq_help))

    wl_help = 'Encode WebP images in lossless mode.'
    enc_group.add_argument('-wl', '--webp-lossless', action='store_true',
                           help=_tagged('WebP', wl_help))

    wm_help = 'WebP compression method/effort (an integer between 0 and 6, ' \
              'where 6 is the slowest but usually gives the best ' \
              'compression). Defaults to 6.'
    enc_group.add_argument('-wm', dest='webp_method',
                           type=int, default=DEFAULT_WEBP_METHOD,
                           help=_tagged('WebP', wm_help))

    color_group = parser.add_argument_group(
        'Color, transparency and metadata options'.upper())

    rc_help = "Reduce colors using an adaptive color palette. This option " \
              "can have a big impact both on file size and image quality."
    color_group.add_argument('-rc', "--reduce-colors", dest="reduce_colors",
                             action='store_true',
                             help=_tagged('PNG', rc_help))

    mc_help = "The maximum number of colors when reducing colors (-rc) " \
              "(an integer between 0 and 255). Defaults to 255."
    color_group.add_argument('-mc', dest="max_colors",
                             type=int, default=256,
                             help=_tagged('PNG', mc_help))

    rt_help = "Remove transparency (replaced with a background color, white " \
              "by default). WebP keeps its alpha channel unless this is set."
    color_group.add_argument('-rt', dest="remove_transparency",
                             action='store_true',
                             help=_tagged('PNG, WebP', rt_help))

    bg_help = "The background color to apply when removing transparency or " \
              "converting to JPEG. Specify 3 integer values (Red, Green and " \
              "Blue), between 0 and 255, separated by spaces. E.g.: " \
              "'255 0 0' for red)."
    color_group.add_argument('-bg', dest="val", type=int, nargs=3,
                             help=_tagged('PNG, WebP', bg_help))

    hbg_help = "The background color in hexadecimal (HTML style) to use " \
               "when removing transparency or converting to JPEG. E.g.: " \
               "'00FF00' for green color."
    color_group.add_argument('-hbg', dest="hex_color", type=str,
                             help=_tagged('PNG, WebP', hbg_help))

    ke_help = "Keep image EXIF data (by default, it's discarded)."
    color_group.add_argument('-ke', '--keep-exif', action='store_true',
                             help=_tagged('JPEG, WebP', ke_help))

    conv_group = parser.add_argument_group(
        'Format conversion options'.upper())

    cb_help = "Convert big photographic PNG images (with a large number of " \
              "colors) to the output format set with --convert-to (JPEG by " \
              "default). An algorithm decides automatically whether the " \
              "conversion is worthwhile. Original files are kept alongside the " \
              "converted ones (unless -fd is used); existing files with the " \
              "target name will be replaced."
    conv_group.add_argument('-cb', "--convert-big", action='store_true',
                            help=_tagged('PNG', cb_help))

    ca_help = "Convert every image found, regardless of its source format, to " \
              "the output format set with --convert-to (JPEG by default). " \
              "Unless the size comparison is disabled (-nc), the converted " \
              "file is kept only when it turns out smaller. Original files are " \
              "kept alongside the converted ones (unless -fd is used)."
    conv_group.add_argument('-ca', "--convert-all", action='store_true',
                            help=_tagged('ALL', ca_help))

    ct_help = "Output format to convert to when -ca or -cb is used. The " \
              "available choices depend on the codecs compiled into the Pillow " \
              "build in use. Defaults to jpeg."
    conv_group.add_argument('-cf', '--convert-to', dest='convert_to',
                            choices=available_output_formats(),
                            default='jpeg',
                            help=_tagged('ALL', ct_help))

    fd_help = "Delete the original PNG file after a successful conversion."
    conv_group.add_argument('-fd', "--force-delete", action='store_true',
                            help=_tagged('PNG', fd_help))

    parser._positionals.title = parser._positionals.title.upper()
    parser._optionals.title = parser._optionals.title.upper()

    args = parser.parse_args()

    if args.info:
        _handle_info(args, parser)  # prints metadata and exits

    recursive = not args.no_recursion
    quality = args.quality
    watch_dir = args.watch_directory

    if args.version:
        parser.exit(status=0, message=get_version_info())

    if args.supported_formats:
        parser.exit(status=0, message=get_formats())

    if args.path:
        src_path = os.path.expanduser(args.path)
    else:
        msg = "\nPlease specify the path of the image or folder to process.\n\n"
        parser.exit(status=0, message=msg)

    if not quality:
        quality = DEFAULT_QUALITY
    elif quality > 100 or quality < 1:
        msg = "\nPlease specify an integer quality value between 1 and 100.\n\n"
        parser.exit(status=0, message=msg)

    if args.max_width < 0 or args.max_height < 0:
        msg = "\nPlease specify image dimensions as positive integers.\n\n"
        parser.exit(status=0, message=msg)

    if args.val and args.hex_color:
        msg = "\nBackground color should be entered only once.\n\n"
        parser.exit(status=0, message=msg)
    elif not args.val and not args.hex_color:
        # By default, apply a white background
        bg_color = (255, 255, 255)
    elif args.val:
        bg_color = tuple(args.val)
    else:
        # Check if hexadecimal is in the expected format
        if not re.search(r'(?:[0-9a-fA-F]{3}){1,2}$', args.hex_color):
            msg = "\nHexadecimal background color was not entered in the correct " \
                  "format. Please follow these examples:\n\nWhite: FFFFFF" \
                  "\nBlack: 000000\nPure Red: FF0000\n\n"
            parser.exit(status=0, message=msg)
        # convert hex to a tuple of integers (RGB)
        bg_color = tuple(
            int(args.hex_color[i:i + 2], 16) for i in (0, 2, 4))

    if min(bg_color) < 0 or max(bg_color) > 255:
        msg = "\nBackground color should be entered as a sequence of 3 " \
              "integer numbers between 0 and 255 (values for Red, Green and " \
              "Blue components) separated by spaces. For instance, for a " \
              "bright red you can use: '-bg 255 0 0' or '-hbg #FF0000'.\n\n"
        parser.exit(status=0, message=msg)

    webp_quality = args.webp_quality
    if webp_quality is None:
        webp_quality = DEFAULT_WEBP_QUALITY
    elif webp_quality > 100 or webp_quality < 1:
        msg = "\nPlease specify an integer WebP quality value between 1 and " \
              "100.\n\n"
        parser.exit(status=0, message=msg)

    if args.webp_method < 0 or args.webp_method > 6:
        msg = "\nPlease specify a WebP method (effort) between 0 and 6.\n\n"
        parser.exit(status=0, message=msg)

    # argparse already validates --convert-to against the formats available in
    # this Pillow build, so no extra codec check is needed here.
    convert_to = args.convert_to

    output_config = OutputConfiguration(args.only_summary, args.only_progress, args.quiet)
    return src_path, watch_dir, recursive, quality, args.remove_transparency, \
        args.reduce_colors, args.max_colors, args.max_width, args.max_height, \
        args.keep_exif, args.convert_all, args.convert_big, args.force_delete, \
        bg_color, args.grayscale, args.no_comparison, args.fast_mode, \
        args.jobs, output_config, convert_to, webp_quality, \
        args.webp_lossless, args.webp_method