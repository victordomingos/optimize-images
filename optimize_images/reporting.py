# encoding: utf-8
from functools import lru_cache

from optimize_images.data_structures import TaskResult
from optimize_images.platforms import IconGenerator


@lru_cache(maxsize=None)
def human(number: int, suffix='B') -> str:
    """Return a human readable memory size in a string.

    Initially written by Fred Cirera, modified and shared by Sridhar Ratnakumar
    (https://stackoverflow.com/a/1094933/6167478), edited by Victor Domingos.
    """
    for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
        if abs(number) < 1024.0:
            return f"{number:3.1f} {unit}{suffix}"
        number = number / 1024.0
    return f"{number:.1f}{'Yi'}{suffix}"


def show_file_status(r: TaskResult, line_width: int, icons: IconGenerator):
    if r.was_optimized:
        short_img = r.img[-(line_width - 17):].ljust(line_width - 17)
        percent = 100 - (r.final_size / r.orig_size * 100)
        h_orig = human(r.orig_size)
        h_final = human(r.final_size)

        orig_format = r.orig_format.replace('JPEG', 'JPG')
        result_format = r.result_format.replace('JPEG', 'JPG')

        if r.orig_mode == "P":
            o_colors = f"{r.orig_colors}"
        else:
            o_colors = ""

        if r.result_mode == "P":
            colors = f"{r.final_colors}"
        else:
            colors = ""

        exif_str1 = icons.info if r.had_exif else ''
        exif_str2 = icons.info if r.has_exif else ''
        downstr = icons.downsized if r.was_downsized else ''
        line1 = f'\n{icons.optimized}  [OPTIMIZED] {short_img}\n'
        line2 = f'    {exif_str1} {orig_format}/{r.orig_mode}{o_colors}: {h_orig}' \
                f'  ->  {downstr}{exif_str2}{result_format}/{r.result_mode}{colors}: ' \
                f'{h_final} {icons.size_is_smaller} {percent:.1f}%'
        img_status = line1 + line2
    else:
        short_img = r.img[-(line_width - 15):].ljust(line_width - 15)
        img_status = f'\n{icons.skipped}  [SKIPPED] {short_img}'

    print(img_status, end='')


def show_final_report(found_files: int,
                      optimized_files: int,
                      src_size: int,
                      bytes_saved: int,
                      time_passed: float):
    """
    Show a final report with the time spent and filesize savings

    :param found_files: number of found image files
    :param optimized_files: number of image files that were processed
    :param src_size: original sum of file sizes
    :param bytes_saved: savings in file sizes (sum)
    :param time_passed: specify -1 in order to hide this (watch directory)
    """
    fps = found_files / time_passed

    if bytes_saved:
        average = bytes_saved / optimized_files
        percent = bytes_saved / src_size * 100
    else:
        average = 0
        percent = 0

    report = f"\n{40 * '-'}\n"
    if time_passed == -1:
        report += f"\n   Processed {found_files} files ({human(src_size)})."
    else:
        report += f"\n   Processed {found_files} files ({human(src_size)}) in " \
                  f"{time_passed:.1f}s ({fps:.1f} f/s)."

    report += f"\n   Optimized {optimized_files} files." \
              f"\n   Average savings: {human(average)} per optimized file" \
              f"\n   Total space saved: {human(bytes_saved)} / {percent:.1f}%\n"
    print(report)


def show_img_exception(exception: Exception, image_path: str, details: str = '') -> None:
    print("\nAn error has occurred while trying to optimize this file:")
    print(image_path)

    if details:
        print(f'\n{details}')

    print("\nThe following info may help to understand what has gone wrong here:\n")
    print(exception)
