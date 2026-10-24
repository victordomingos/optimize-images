"""
Public integration API for third-party applications.

This module exposes stable, UI-free entry points to the image optimization
logic of this package. Prefer using these functions over lower-level modules.
"""
import os
import sys
import tempfile
import threading
import time
import traceback
from concurrent.futures import as_completed
from dataclasses import dataclass
from optimize_images.batch_core import build_tasks as _build_tasks
from optimize_images.data_structures import TaskResult as _TaskResult, \
    Task as _Task, BatchOptions as _BatchOptions
from optimize_images.do_optimization import do_optimization
from optimize_images.exceptions import OIImagesNotFoundError, OIWatchStoppedError
from optimize_images.exif_format import format_exif
from optimize_images.img_convert import converted_path
from optimize_images.formats import (
    normalize_target as _normalize_convert_to,
    available_input_formats,
    available_output_formats,
    format_capabilities,
)
from optimize_images.img_ssim import (
    ensure_ssim_available,
    validate_ssim_min,
)
from optimize_images.jpeg_qtables import validate_jpeg_tables
from optimize_images.inmemory import convert_image_data as _convert_image_data
from optimize_images.inmemory import optimize_image_data as _optimize_image_data
from optimize_images.metadata import ImageMetadata, inspect_image
from optimize_images.platforms import (adjust_for_platform, create_executor,
                                      effective_worker_count, sigint_deferred)
from timeit import default_timer as timer
from typing import Iterator, List, Callable, Optional
from typing import Tuple

# Public API surface. Declaring __all__ documents what third-party code may
# import and marks the re-exported discovery helpers as exported, so linters
# do not report them as unused imports.
__all__ = [
    "PublicBatchOptions",
    "PublicTaskResult",
    "PublicBatchResult",
    "optimize_single_image",
    "optimize_image_data",
    "convert_image_data",
    "optimize_as_batch",
    "optimize_as_batch_stream",
    "watch_directory",
    "available_input_formats",
    "available_output_formats",
    "format_capabilities",
    "ImageMetadata",
    "inspect_image",
    "format_exif",
]


# -----------------------
# Public API data classes
# -----------------------

@dataclass(frozen=True)
class PublicBatchOptions:
    src_path: str
    recursive: bool = True
    quality: Optional[int] = None
    remove_transparency: bool = False
    reduce_colors: bool = False
    max_colors: int = 256
    max_w: int = 0
    max_h: int = 0
    keep_exif: bool = False
    convert_all: bool = False
    conv_big: bool = False
    force_del: bool = False
    bg_color: Tuple[int, int, int] = (255, 255, 255)
    grayscale: bool = False
    ignore_size_comparison: bool = False
    fast_mode: bool = False
    jobs: int = 0
    convert_to: str = 'jpeg'
    webp_quality: int = 80
    webp_lossless: bool = False
    webp_method: int = 6
    ssim_min: Optional[float] = None
    show_ssim: bool = False
    jpeg_tables: str = 'auto'


@dataclass(frozen=True)
class PublicTaskResult:
    img: str
    orig_format: str
    result_format: str
    orig_mode: str
    result_mode: str
    orig_colors: int
    final_colors: int
    orig_size: int
    final_size: int
    was_optimized: bool
    was_downsized: bool
    had_exif: bool
    has_exif: bool
    ssim: Optional[float] = None
    error: Optional[str] = None


@dataclass(frozen=True)
class PublicBatchResult:
    results: List[PublicTaskResult]
    found_files: int
    optimized_files: int
    skipped_files: int
    total_src_size: int
    total_bytes_saved: int
    elapsed_seconds: float


# -----------------------
# Internal conversion
# -----------------------

# Conversion-target validation and the format discovery helpers live in
# optimize_images.formats; _normalize_convert_to is imported from there and
# the discovery functions are re-exported as part of the public API.


def _to_internal_options(opts: PublicBatchOptions) -> _BatchOptions:
    return _BatchOptions(
        src_path=opts.src_path,
        recursive=opts.recursive,
        quality=opts.quality,
        remove_transparency=opts.remove_transparency,
        reduce_colors=opts.reduce_colors,
        max_colors=opts.max_colors,
        max_w=opts.max_w,
        max_h=opts.max_h,
        keep_exif=opts.keep_exif,
        convert_all=opts.convert_all,
        conv_big=opts.conv_big,
        force_del=opts.force_del,
        bg_color=opts.bg_color,
        grayscale=opts.grayscale,
        ignore_size_comparison=opts.ignore_size_comparison,
        fast_mode=opts.fast_mode,
        jobs=opts.jobs,
        output_config=None,
        convert_to=_normalize_convert_to(opts.convert_to),
        webp_quality=opts.webp_quality,
        webp_lossless=opts.webp_lossless,
        webp_method=opts.webp_method,
        ssim_min=opts.ssim_min,
        show_ssim=opts.show_ssim,
        jpeg_tables=opts.jpeg_tables,
    )


def _to_public_result(r: _TaskResult) -> PublicTaskResult:
    return PublicTaskResult(
        img=r.img,
        orig_format=r.orig_format,
        result_format=r.result_format,
        orig_mode=r.orig_mode,
        result_mode=r.result_mode,
        orig_colors=r.orig_colors,
        final_colors=r.final_colors,
        orig_size=r.orig_size,
        final_size=r.final_size,
        was_optimized=r.was_optimized,
        was_downsized=r.was_downsized,
        had_exif=r.had_exif,
        has_exif=r.has_exif,
        ssim=r.ssim,
        error=r.error,
    )


# -----------------------
# Public API functions
# -----------------------

def optimize_as_batch_stream(options: PublicBatchOptions) -> Iterator[PublicTaskResult]:
    validate_jpeg_tables(options.jpeg_tables)
    if options.ssim_min is not None:
        validate_ssim_min(options.ssim_min)
        ensure_ssim_available()
    internal = _to_internal_options(options)
    line_width, our_pool_executor, workers = adjust_for_platform()
    if internal.jobs != 0:
        workers = internal.jobs
    else:
        workers = effective_worker_count(workers,
                                         internal.ssim_min is not None
                                         or internal.show_ssim)
    tasks = _build_tasks(internal)
    with create_executor(our_pool_executor, workers) as executor:
        # Submit every task and yield each result as soon as it finishes
        # (completion order), so the report streams continuously instead of
        # stalling on a slow image that happens to be early in the list.
        try:
            with sigint_deferred():
                futures = [executor.submit(do_optimization, task) for task in tasks]
            for future in as_completed(futures):
                yield _to_public_result(future.result())
        except BaseException:
            # Ctrl-C, an error, or a caller that stops iterating (GeneratorExit):
            # drop the files not started yet; files in progress are finished.
            executor.shutdown(wait=True, cancel_futures=True)
            raise


def optimize_as_batch(options: PublicBatchOptions) -> PublicBatchResult:
    start = timer()
    found_files = 0
    optimized_files = 0
    skipped_files = 0
    total_src_size = 0
    total_bytes_saved = 0
    results: List[PublicTaskResult] = []

    for r in optimize_as_batch_stream(options):
        results.append(r)
        found_files += 1
        total_src_size += r.orig_size
        if r.was_optimized:
            optimized_files += 1
            total_bytes_saved += r.orig_size - r.final_size
        else:
            skipped_files += 1

    elapsed = timer() - start
    return PublicBatchResult(
        results=results,
        found_files=found_files,
        optimized_files=optimized_files,
        skipped_files=skipped_files,
        total_src_size=total_src_size,
        total_bytes_saved=total_bytes_saved,
        elapsed_seconds=elapsed,
    )


def optimize_single_image(
        src_path: str,
        *,
        quality: Optional[int] = None,
        remove_transparency: bool = False,
        reduce_colors: bool = False,
        max_colors: int = 256,
        max_w: int = 0,
        max_h: int = 0,
        keep_exif: bool = False,
        convert_all: bool = False,
        conv_big: bool = False,
        force_del: bool = False,
        bg_color: Tuple[int, int, int] = (255, 255, 255),
        grayscale: bool = False,
        ignore_size_comparison: bool = False,
        fast_mode: bool = False,
        convert_to: str = 'jpeg',
        webp_quality: int = 80,
        webp_lossless: bool = False,
        webp_method: int = 6,
        ssim_min: Optional[float] = None,
        show_ssim: bool = False,
        jpeg_tables: str = 'auto',
) -> PublicTaskResult:
    validate_jpeg_tables(jpeg_tables)
    if ssim_min is not None:
        validate_ssim_min(ssim_min)
        ensure_ssim_available()
    options = PublicBatchOptions(
        src_path=src_path,
        recursive=False,
        quality=quality,
        remove_transparency=remove_transparency,
        reduce_colors=reduce_colors,
        max_colors=max_colors,
        max_w=max_w,
        max_h=max_h,
        keep_exif=keep_exif,
        convert_all=convert_all,
        conv_big=conv_big,
        force_del=force_del,
        bg_color=bg_color,
        grayscale=grayscale,
        ignore_size_comparison=ignore_size_comparison,
        fast_mode=fast_mode,
        jobs=0,
        convert_to=convert_to,
        webp_quality=webp_quality,
        webp_lossless=webp_lossless,
        webp_method=webp_method,
        ssim_min=ssim_min,
        show_ssim=show_ssim,
        jpeg_tables=jpeg_tables,
    )
    internal = _to_internal_options(options)
    tasks = list(_build_tasks(internal))
    if not tasks:
        raise OIImagesNotFoundError("No image files were found. Provide a valid file path.")
    res = do_optimization(tasks[0])
    return _to_public_result(res)


def optimize_image_data(
        data: bytes,
        *,
        name: str = '',
        quality: Optional[int] = None,
        remove_transparency: bool = False,
        reduce_colors: bool = False,
        max_colors: int = 256,
        max_w: int = 0,
        max_h: int = 0,
        keep_exif: bool = False,
        bg_color: Tuple[int, int, int] = (255, 255, 255),
        grayscale: bool = False,
        ignore_size_comparison: bool = False,
        fast_mode: bool = False,
        webp_quality: int = 80,
        webp_lossless: bool = False,
        webp_method: int = 6,
        ssim_min: Optional[float] = None,
        show_ssim: bool = False,
        jpeg_tables: str = 'auto',
) -> Tuple[bytes, PublicTaskResult]:
    """Optimize an in-memory image: bytes in, bytes out.

    For callers that store images as binary data instead of files (CMS, object
    storage, databases). Keeps the original format and returns the optimized
    bytes together with a PublicTaskResult; when optimizing does not help (and
    the size comparison is not disabled) the original bytes are returned
    unchanged. ``name`` is only a label echoed back in the result.

    Raises OSError if ``data`` is not a readable image.
    """
    validate_jpeg_tables(jpeg_tables)
    if ssim_min is not None:
        validate_ssim_min(ssim_min)
        ensure_ssim_available()
    out_bytes, result = _optimize_image_data(
        data,
        name=name,
        quality=quality,
        remove_transparency=remove_transparency,
        reduce_colors=reduce_colors,
        max_colors=max_colors,
        max_w=max_w,
        max_h=max_h,
        keep_exif=keep_exif,
        bg_color=bg_color,
        grayscale=grayscale,
        ignore_size_comparison=ignore_size_comparison,
        fast_mode=fast_mode,
        webp_quality=webp_quality,
        webp_lossless=webp_lossless,
        webp_method=webp_method,
        ssim_min=ssim_min,
        show_ssim=show_ssim,
        jpeg_tables=jpeg_tables,
    )
    return out_bytes, _to_public_result(result)


def convert_image_data(
        data: bytes,
        *,
        to: str = 'jpeg',
        name: str = '',
        quality: Optional[int] = None,
        remove_transparency: bool = False,
        max_w: int = 0,
        max_h: int = 0,
        keep_exif: bool = False,
        bg_color: Tuple[int, int, int] = (255, 255, 255),
        grayscale: bool = False,
        ignore_size_comparison: bool = False,
        webp_quality: int = 80,
        webp_lossless: bool = False,
        webp_method: int = 6,
        ssim_min: Optional[float] = None,
        show_ssim: bool = False,
        jpeg_tables: str = 'auto',
) -> Tuple[bytes, PublicTaskResult]:
    """Convert an in-memory image to another format: bytes in, bytes out.

    The counterpart of optimize_image_data for callers that store images as
    binary data and want to change the format (e.g. PNG to WebP) without a file
    path. ``to`` is the target format ('jpeg', 'png', 'webp', and 'avif' or
    'jpeg2000' when the Pillow build supports them); it is validated against the
    codecs actually available. Returns the converted bytes and a
    PublicTaskResult - read ``result_format`` to know the format of the bytes
    and store them accordingly.

    When converting would not shrink the image (and the size comparison is not
    disabled), the original bytes and format are returned unchanged; converting
    to the source's own format optimizes it in place; multi-frame sources are
    returned unchanged. Raises ValueError for an unknown/unavailable target and
    OSError if ``data`` is not a readable image.
    """
    validate_jpeg_tables(jpeg_tables)
    if ssim_min is not None:
        validate_ssim_min(ssim_min)
        ensure_ssim_available()
    out_bytes, result = _convert_image_data(
        data,
        to=to,
        name=name,
        quality=quality,
        remove_transparency=remove_transparency,
        max_w=max_w,
        max_h=max_h,
        keep_exif=keep_exif,
        bg_color=bg_color,
        grayscale=grayscale,
        ignore_size_comparison=ignore_size_comparison,
        webp_quality=webp_quality,
        webp_lossless=webp_lossless,
        webp_method=webp_method,
        ssim_min=ssim_min,
        show_ssim=show_ssim,
        jpeg_tables=jpeg_tables,
    )
    return out_bytes, _to_public_result(result)


def watch_directory(
        options: PublicBatchOptions,
        on_result: Callable[[PublicTaskResult], None],
        stop_event: Optional[threading.Event] = None,
) -> None:
    """Watch a directory for new image files and optimize them as they appear."""
    validate_jpeg_tables(options.jpeg_tables)
    if options.ssim_min is not None:
        validate_ssim_min(options.ssim_min)
        ensure_ssim_available()
    internal = _to_internal_options(options)
    if not internal.src_path or not os.path.isdir(os.path.abspath(internal.src_path)):
        raise OIImagesNotFoundError("Please specify a valid path to an existing folder.")

    try:
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer
    except ImportError:
        raise ImportError("Watchdog package is required for directory watching. "
                          "Please install it with: pip install watchdog")

    # Create a task - we'll handle the field name mismatch in the event handler
    base_task = _Task(
        internal.src_path,
        internal.quality,
        internal.remove_transparency,
        internal.reduce_colors,
        internal.max_colors,
        internal.max_w,
        internal.max_h,
        internal.keep_exif,
        internal.convert_all,
        internal.conv_big,
        internal.force_del,
        internal.bg_color,
        internal.grayscale,
        internal.ignore_size_comparison,
        internal.fast_mode,
        internal.output_config,
        internal.convert_to,
        internal.webp_quality,
        internal.webp_lossless,
        internal.webp_method,
        internal.ssim_min,
        internal.show_ssim,
        internal.jpeg_tables,
    )

    # Define a function to check if a file is a supported image
    def is_image(filepath):
        if not os.path.isfile(filepath):
            return False
        else:
            extension = os.path.splitext(filepath)[1][1:]
            return extension.lower() in ['jpg', 'jpeg', 'png', 'webp']

    folder = os.path.abspath(base_task.src_path)
    real_folder = os.path.realpath(folder)

    def in_watched_folder(path):
        try:
            return os.path.commonpath([real_folder, os.path.realpath(path)]) == real_folder
        except ValueError:  # e.g. another drive on Windows
            return False

    converts = internal.convert_all or internal.conv_big

    class APIOptimizeImageEventHandler(FileSystemEventHandler):
        """Optimizes each new image file in the watched folder.

        watchdog calls the handler from its single observer thread, so files
        are processed one at a time, in event order. That order is also what
        lets the signatures recognise our own writes: the event for a file
        written here is dispatched only after the handler returns. (Moving the
        work to an executor would need another way to recognise them.)
        """

        def __init__(self, task):
            super().__init__()
            self.task = task
            # (size, mtime_ns) of each file as this handler left it. An event
            # for a file that still matches is our own write (in-place save,
            # converted copy) or a repeated event, not a new file.
            self.signatures = {}
            # File-system clock minus local clock, measured with a probe file
            # at start and refreshed by our own writes (None while unknown):
            # lets the write-finish wait trust a file's mtime age even on a
            # share whose clock disagrees with ours.
            self.clock_offset = None
            self.symbols_shown = False

        def on_created(self, event):
            if not event.is_directory:
                self._handle(event.src_path)

        def on_moved(self, event):
            if event.is_directory:
                return
            # A renamed file keeps its contents and mtime: carry its signature
            # along, so renaming an optimized file does not optimize it again.
            signature = self.signatures.pop(event.src_path, None)
            if signature is not None:
                self.signatures[event.dest_path] = signature
            # Atomic saves (a temp file renamed into place, as browsers and
            # many editors do) only arrive as moves.
            self._handle(event.dest_path)

        def on_deleted(self, event):
            if event.is_directory:
                prefix = os.path.join(event.src_path, '')
                for path in [p for p in self.signatures if p.startswith(prefix)]:
                    del self.signatures[path]
            else:
                self.signatures.pop(event.src_path, None)

        def _handle(self, path):
            # An exception escaping a handler kills watchdog's observer thread
            # and silently ends the watch: report it and go on with the next
            # file, as concurrent.futures does with a failing done-callback.
            try:
                self._process(path)
            except Exception:
                print(f"\nError while handling a watched file: {path}",
                      file=sys.stderr)
                traceback.print_exc()

        def _learn_clock_offset(self, path):
            # The file was just written, so its mtime is "now" on the file
            # system's clock. Taken after the write, the estimate is a little
            # low, which only makes the age test more cautious.
            now = time.time()
            try:
                offset = _clock_offset_from(os.stat(path), now)
            except OSError:
                return
            if offset is not None:
                self.clock_offset = offset

        def _remember(self, path):
            signature = _file_signature(path)
            if signature is None:
                self.signatures.pop(path, None)
            else:
                self.signatures[path] = signature

        def _process(self, path):
            if (not is_image(path)
                    or '~temp~' in path
                    or not in_watched_folder(path)):
                return

            # Our own unchanged write needs no wait (its mtime is recent).
            known = self.signatures.get(path)
            if known is not None and _file_signature(path) == known:
                return
            signature = _wait_for_write_finish(path, self.clock_offset)
            if signature is None or signature == known:
                return

            show_legend = not self.symbols_shown
            self.symbols_shown = True
            if show_legend:
                from optimize_images.platforms import IconGenerator
                icons = IconGenerator()
                print("\nUsing these symbols:\n")
                print(f"  {icons.optimized} Optimized file     {icons.info} EXIF info present")
                print(
                    f"  {icons.skipped} Skipped file       {icons.downsized} Image was downsized     {icons.size_is_smaller} Size reduction (%)\n")

            img_task = self.task._replace(src_path=path)
            result = do_optimization(img_task)

            # Remember the files as left now, before the callback runs, so a
            # failing callback cannot get them processed a second time. The
            # converted copy only when the conversion wrote it: a file of the
            # user's with that name is not ours (an in-place fallback keeps
            # the original format).
            self._remember(path)
            written = path
            if (converts and result.was_optimized
                    and result.result_format != result.orig_format):
                written = converted_path(img_task)
                if written != path:
                    self._remember(written)
            if result.was_optimized:
                self._learn_clock_offset(written)

            on_result(_to_public_result(result))

    # Set up our watcher
    print(f"\nPreparing to watch directory (press CTRL+C to quit):\n {folder}\n")

    event_handler = APIOptimizeImageEventHandler(base_task)
    event_handler.clock_offset = _probe_clock_offset(folder)
    observer = Observer()
    observer.schedule(event_handler, folder, recursive=True)
    observer.start()

    waiter = stop_event if stop_event is not None else threading.Event()
    try:
        while not waiter.wait(1):
            emitters = tuple(observer.emitters)
            if not observer.is_alive() or not all(e.is_alive() for e in emitters):
                raise OIWatchStoppedError(
                    "The folder watcher stopped unexpectedly; new files are "
                    "no longer being noticed.")
    except KeyboardInterrupt:
        print("\b \n\n  == Operation was interrupted by the user. ==\n")
    finally:
        observer.stop()
        observer.join()


# Watch mode: how long a new file must stay unchanged before it is processed,
# how often to look, and when to give up waiting and process it anyway.
WATCH_SETTLE_SECONDS = 0.5
WATCH_POLL_SECONDS = 0.05
WATCH_MAX_WAIT_SECONDS = 60.0


def _clock_offset_from(stat: os.stat_result, now: float) -> Optional[float]:
    """File-system clock minus ours, from a file written just before *now*
    (so the estimate is a little low, which only makes the age test more
    cautious); None on file systems that store whole seconds."""
    if stat.st_mtime_ns % 1_000_000_000 == 0:
        return None
    return stat.st_mtime - now


def _probe_clock_offset(folder: str) -> Optional[float]:
    """Measure the file system's clock in *folder* with a small temporary
    file, created and removed at once ('~temp~' in its name keeps the watcher
    away from it). None when that is not possible (e.g. a read-only folder)."""
    try:
        handle, path = tempfile.mkstemp(prefix='.~temp~clock-', dir=folder)
    except OSError:
        return None
    try:
        os.write(handle, b'0')
        offset = _clock_offset_from(os.fstat(handle), time.time())
    except OSError:
        offset = None
    finally:
        os.close(handle)
        try:
            os.remove(path)
        except OSError:
            pass
    return offset


def _file_signature(path: str) -> Optional[Tuple[int, int]]:
    """(size, mtime_ns) of a file, or None if it cannot be read."""
    try:
        stat = os.stat(path)
    except OSError:
        return None
    return stat.st_size, stat.st_mtime_ns


def _wait_for_write_finish(path: str,
                           clock_offset: Optional[float] = None
                           ) -> Optional[Tuple[int, int]]:
    """Wait until a new file looks completely written.

    Returns its (size, mtime_ns), or None if it disappeared meanwhile. The file
    is ready when size and mtime stayed the same for WATCH_SETTLE_SECONDS, or
    at once when its mtime is already that old: a writer that pauses briefly
    between chunks is waited for, while a file written well before its event
    is handled (for instance in a burst) costs no wait at all.

    The age test needs the file system's clock: *clock_offset* is the file
    system's time minus ours (measured with a probe file when watching starts,
    then from the files we write). Without it (a read-only folder before our
    first write) and on file systems that store whole seconds (HFS+, FAT), an
    mtime can look old while the file is still being written, so only the
    stability test is used.
    After WATCH_MAX_WAIT_SECONDS the file is processed anyway.
    """
    start = time.monotonic()
    previous = None
    stable_since = start
    while True:
        try:
            stat = os.stat(path)
        except (FileNotFoundError, NotADirectoryError):
            return None
        signature = (stat.st_size, stat.st_mtime_ns)
        now = time.monotonic()
        if (clock_offset is not None
                and stat.st_mtime_ns % 1_000_000_000
                and time.time() + clock_offset - stat.st_mtime
                >= WATCH_SETTLE_SECONDS):
            return signature
        if signature != previous:
            previous, stable_since = signature, now
        elif now - stable_since >= WATCH_SETTLE_SECONDS:
            return signature
        if now - start >= WATCH_MAX_WAIT_SECONDS:
            return signature
        time.sleep(WATCH_POLL_SECONDS)
