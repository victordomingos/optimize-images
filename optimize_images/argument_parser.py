# encoding: utf-8
import os
import re
from argparse import ArgumentParser

from optimize_images.constants import DEFAULT_QUALITY, SUPPORTED_FORMATS


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

    parser.add_argument('-v', '--version', action='version',
                        version=__import__('optimize_images').__version__)

    sf_help = 'Display the list of image formats currently supported.'
    parser.add_argument('-s', '--supported', dest="supported_formats",
                        action='store_true', help=sf_help)

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

    general_msg = 'These options will be applied individually to each ' \
                  'image being processed, independently of its format.'
    general_group = parser.add_argument_group(
        'General image settings'.upper(), description=general_msg)

    mw_help = 'The maximum width (in pixels).'
    general_group.add_argument('-mw', dest="max_width",
                               type=int, default=0, help=mw_help)

    mh_help = "The maximum height (in pixels). Any image that has a dimension " \
              "exceeding a specified value will be downsized as the first " \
              "optimization step. The resizing will not take effect if, " \
              "after the whole optimization process, the resulting file " \
              "size isn't any smaller than the original."
    general_group.add_argument('-mh', dest="max_height",
                               type=int, default=0, help=mh_help)

    general_group.add_argument('-g', '--grayscale', action='store_true',
                               help="Convert to grayscale.")

    nc_help = "Don't compare the original and resulting file sizes, and save " \
              "the new image anyway (useful, for instance, if you prefer to " \
              "have all images with the same color, size, or quality settings)."
    general_group.add_argument('-nc', '--no-comparison', action='store_true',
                               help=nc_help)

    fm_help = 'Skip some actions (e.g., the final palete rebuild for indexed ' \
              'PNG images or variable JPEG quality setting) in order to ' \
              'finish faster.'
    general_group.add_argument('-fm', '--fast-mode', action='store_true', help=fm_help)

    jpg_msg = 'The following options apply only to JPEG image files.'
    jpg_group = parser.add_argument_group(
        'JPEG specific options'.upper(), description=jpg_msg)

    q_help = 'Specify a fixed quality setting for JPEG files (an integer ' \
             'value, between 1 and 100).'
    jpg_group.add_argument('-q', dest='quality',
                           type=int, help=q_help)

    jpg_group.add_argument(
        '-ke',
        '--keep-exif',
        action='store_true',
        help="Keep image EXIF data (by default, it's discarded).")

    png_msg = 'The following options apply only to PNG image files.'
    png_group = parser.add_argument_group(
        'PNG specific options'.upper(), description=png_msg)

    rc_help = "Reduce colors using an adaptive color palette. This option " \
              "can have a big impact both on file size and image quality."
    png_group.add_argument('-rc', "--reduce-colors", dest="reduce_colors",
                           action='store_true', help=rc_help)

    mc_help = "The maximum number of colors when reducing colors (-rc) " \
              "(an integer between 0 and 255). Defaults to 255."
    png_group.add_argument('-mc', dest="max_colors",
                           type=int, default=256, help=mc_help)

    rt_help = "Remove transparency (by default, white background)."
    png_group.add_argument('-rt',
                           dest="remove_transparency", action='store_true',
                           help=rt_help)

    bg_help = "The background color to apply when removing transparency or " \
              "converting to JPEG. Specify 3 integer values (Red, Green and " \
              "Blue), between 0 and 255, separated by spaces. E.g.: " \
              "'255 0 0' for red)."
    png_group.add_argument(
        '-bg', dest="val", type=int, nargs=3, help=bg_help)

    hbg_help = "The background color in hexadecimal (HTML style) to use " \
               "when removing transparency or converting to JPEG. E.g.: '00FF00' " \
               "for green color."
    png_group.add_argument('-hbg', dest="hex_color", type=str, help=hbg_help)

    cb_help = "Convert to JPEG any big PNG images that have " \
              "a large number of colors. It uses an algorithm " \
              "to determine whether it is a good idea and automatically decide " \
              "about it. By default, the original PNG " \
              "files will remain untouched and will be kept alongside the " \
              "optimized JPG images in their original folders (existing JPEGs " \
              "will be replaced)."
    png_group.add_argument(
        '-cb', "--convert-big", action='store_true', help=cb_help)

    ca_help = "Convert to JPEG all PNG images found. By default, " \
              "the original PNG " \
              "files will remain untouched and will be kept alongside the " \
              "optimized JPG images in their original folders (existing JPEGs " \
              "will be replaced)."
    png_group.add_argument(
        '-ca', "--convert-all", action='store_true', help=ca_help)

    fd_help = "Delete the original file when converting to JPG."
    png_group.add_argument(
        '-fd', "--force-delete", action='store_true', help=fd_help)

    parser._positionals.title = parser._positionals.title.upper()
    parser._optionals.title = parser._optionals.title.upper()

    args = parser.parse_args()
    recursive = not args.no_recursion
    quality = args.quality
    watch_dir = args.watch_directory

    if args.supported_formats:
        formats = ', '.join(SUPPORTED_FORMATS).strip().upper()
        msg = "These are the image formats currently supported (please " \
              "note that any files without one of these file extensions " \
              "will be ignored):"
        msg = f"\n{msg} {formats}\n\n"
        parser.exit(status=0, message=msg)

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

    return watch_dir, src_path, recursive, quality, args.remove_transparency, \
           args.reduce_colors, args.max_colors, args.max_width, args.max_height, \
           args.keep_exif, args.convert_all, args.convert_big, args.force_delete, \
           bg_color, args.grayscale, args.no_comparison, args.fast_mode, \
           args.jobs
