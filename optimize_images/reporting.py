# encoding: utf-8
import threading

from optimize_images.data_structures import OutputConfiguration, TaskResult
from optimize_images.platforms import IconGenerator

from typing import Any

_human_cache: dict = {}
_human_cache_lock = threading.Lock()


def human(number: int, suffix='B') -> str:
    """Return a human readable memory size in a string.

    Initially written by Fred Cirera, modified and shared by Sridhar Ratnakumar
    (https://stackoverflow.com/a/1094933/6167478), edited by Victor Domingos.
    """
    key = (number, suffix)
    try:
        return _human_cache[key]
    except KeyError:
        pass

    result = number
    unit_result = ''
    for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
        if abs(result) < 1024.0:
            unit_result = f"{result:3.1f} {unit}{suffix}"
            break
        result = result / 1024.0
    else:
        unit_result = f"{result:.1f}{'Yi'}{suffix}"

    with _human_cache_lock:
        _human_cache[key] = unit_result
    return unit_result


def _fmt_format(fmt: str) -> str:
    """Normalize format names for compact display."""
    if not fmt:
        return ""
    return "JPG" if fmt.upper() == "JPEG" else fmt.upper()


def _fmt_mode(mode: str, colors: int) -> str:
    """Render image mode; for palette 'P' use P{colors} if colors > 0."""
    if not mode:
        return ""
    m = mode.upper()
    if m == "P" and isinstance(colors, int) and colors > 0:
        return f"P{colors}"
    return m


def show_file_status(result: Any, line_width: int, icons: IconGenerator) -> None:
    """
    Two-line output for optimized files; one-line output for skipped files.
    Compatible with PublicTaskResult and TaskResult.
    """
    img = getattr(result, "img", "")
    was_optimized = getattr(result, "was_optimized", False)
    was_downsized = getattr(result, "was_downsized", False)
    orig_size = getattr(result, "orig_size", 0)
    final_size = getattr(result, "final_size", 0)
    orig_format = _fmt_format(getattr(result, "orig_format", ""))
    result_format = _fmt_format(getattr(result, "result_format", ""))
    orig_mode = _fmt_mode(
        getattr(result, "orig_mode", ""), getattr(result, "orig_colors", 0)
    )
    result_mode = _fmt_mode(
        getattr(result, "result_mode", ""), getattr(result, "final_colors", 0)
    )
    had_exif = bool(
        getattr(result, "had_exif", False) or getattr(result, "has_exif", False)
    )

    # First line (build fixed prefix + variable path)
    prefix = (
        f"{icons.optimized}  [OPTIMIZED] "
        if was_optimized
        else f"{icons.skipped}  [SKIPPED] "
    )

    path = img

    def clamp(s: str) -> str:
        return (
            s[:line_width]
            if isinstance(line_width, int) and line_width > 0
            else s
        )

    def clamp_path_end(prefix_text: str, path_text: str) -> str:
        """Truncate only the path from the left so the tail remains visible."""
        if not (isinstance(line_width, int) and line_width > 0):
            return prefix_text + path_text
        available = line_width - len(prefix_text)
        if available <= 0:
            return (
                prefix_text[: max(0, line_width - 1)] + "…"
                if line_width > 0
                else prefix_text
            )
        if len(path_text) <= available:
            return prefix_text + path_text
        keep = max(0, available - 1)  # reserve 1 for ellipsis
        return prefix_text + ("…" + path_text[-keep:] if keep > 0 else "…")

    # Print the first line with correct truncation rules
    print(clamp_path_end(prefix, path))

    # Only optimized files print the second line with details
    if was_optimized:
        saved_bytes = max(0, orig_size - final_size)
        percent = (saved_bytes / orig_size * 100.0) if orig_size else 0.0

        orig_h = human(orig_size)
        final_h = human(final_size)

        left = (
            f"{orig_format}/{orig_mode}: {orig_h}"
            if orig_format or orig_mode
            else f"{orig_h}"
        )
        right = (
            f"{result_format}/{result_mode}: {final_h}"
            if result_format or result_mode
            else f"{final_h}"
        )

        prefix2 = f"    {icons.info}  " if had_exif else "     "
        downsized_text = icons.downsized if was_downsized else ""

        line2 = (
            f"{prefix2}{left}  {icons.arrow}  {downsized_text}"
            f"{right} {icons.size_is_smaller} {percent:.1f}%"
        )

        print(clamp(line2))


def show_final_report(found_files: int,
                      optimized_files: int,
                      src_size: int,
                      bytes_saved: int,
                      time_passed: float,
                      output_config: OutputConfiguration):
    """
    Show a final report with the time spent and filesize savings

    :param found_files: number of found image files
    :param optimized_files: number of image files that were processed
    :param src_size: original sum of file sizes
    :param bytes_saved: savings in file sizes (sum)
    :param time_passed: specify -1 in order to hide this (watch directory)
    """

    if output_config.quiet_mode:
        return

    fps = found_files / time_passed

    if bytes_saved:
        average = bytes_saved / optimized_files
        percent = bytes_saved / src_size * 100
    else:
        average = 0
        percent = 0

    # No leading or trailing extra blank lines around the dashed separator
    report = f"{40 * '-'}\n"
    if time_passed == -1:
        report += f"\n   Processed {found_files} files ({human(src_size)})."
    else:
        fps = found_files / time_passed if time_passed > 0 else 0.0
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
