"""
Public integration API for third-party applications.

This module exposes stable, UI-free entry points to the image optimization
logic of this package. Prefer using these functions over lower-level modules.
"""
import os
import threading
from concurrent.futures import as_completed
from dataclasses import dataclass
from timeit import default_timer as timer
from typing import Iterator, List, Callable, Optional
from typing import Tuple

from optimize_images.batch_core import build_tasks as _build_tasks
from optimize_images.data_structures import TaskResult as _TaskResult, \
    Task as _Task, BatchOptions as _BatchOptions
from optimize_images.do_optimization import do_optimization
from optimize_images.exceptions import OIImagesNotFoundError
from optimize_images.formats import (
    normalize_target as _normalize_convert_to,
    available_input_formats,
    available_output_formats,
    format_capabilities,
)
from optimize_images.metadata import ImageMetadata, inspect_image
from optimize_images.platforms import adjust_for_platform

# Public API surface. Declaring __all__ documents what third-party code may
# import and marks the re-exported discovery helpers as exported, so linters
# do not report them as unused imports.
__all__ = [
    "PublicBatchOptions",
    "PublicTaskResult",
    "PublicBatchResult",
    "optimize_single_image",
    "optimize_as_batch",
    "optimize_as_batch_stream",
    "watch_directory",
    "available_input_formats",
    "available_output_formats",
    "format_capabilities",
    "ImageMetadata",
    "inspect_image",
]


# -----------------------
# Public API data classes
# -----------------------

@dataclass(frozen=True)
class PublicBatchOptions:
    src_path: str
    recursive: bool = True
    quality: int = 80
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
    )


# -----------------------
# Public API functions
# -----------------------

def optimize_as_batch_stream(options: PublicBatchOptions) -> Iterator[PublicTaskResult]:
    internal = _to_internal_options(options)
    line_width, our_pool_executor, workers = adjust_for_platform()
    if internal.jobs != 0:
        workers = internal.jobs
    tasks = _build_tasks(internal)
    with our_pool_executor(max_workers=workers) as executor:
        # Submit every task and yield each result as soon as it finishes
        # (completion order), so the report streams continuously instead of
        # stalling on a slow image that happens to be early in the list.
        futures = [executor.submit(do_optimization, task) for task in tasks]
        for future in as_completed(futures):
            yield _to_public_result(future.result())


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
        quality: int = 80,
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
) -> PublicTaskResult:
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
    )
    internal = _to_internal_options(options)
    tasks = list(_build_tasks(internal))
    if not tasks:
        raise OIImagesNotFoundError("No image files were found. Provide a valid file path.")
    res = do_optimization(tasks[0])
    return _to_public_result(res)


def watch_directory(
        options: PublicBatchOptions,
        on_result: Callable[[PublicTaskResult], None],
        stop_event: Optional[threading.Event] = None,
) -> None:
    """Watch a directory for new image files and optimize them as they appear."""
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
    )

    # Define a function to check if a file is a supported image
    def is_image(filepath):
        if not os.path.isfile(filepath):
            return False
        else:
            extension = os.path.splitext(filepath)[1][1:]
            return extension.lower() in ['jpg', 'jpeg', 'png', 'webp']

    # Create our own event handler directly
    class APIOptimizeImageEventHandler(FileSystemEventHandler):
        def __init__(self, task):
            super().__init__()
            self.task = task
            self.paths_to_ignore = []
            self.symbols_shown = False
            self._lock = threading.Lock()

            self.line_width, pool_ex, default_workers = adjust_for_platform()

        def on_created(self, event):
            if (event.is_directory
                    or not is_image(event.src_path)
                    or '~temp~' in event.src_path):
                return

            with self._lock:
                if event.src_path in self.paths_to_ignore:
                    return
                self.paths_to_ignore.append(event.src_path)

            self._wait_for_write_finish(event.src_path)

            with self._lock:
                show_legend = not self.symbols_shown
                if show_legend:
                    self.symbols_shown = True

            if show_legend:
                from optimize_images.platforms import IconGenerator
                icons = IconGenerator()
                print("\nUsing these symbols:\n")
                print(f"  {icons.optimized} Optimized file     {icons.info} EXIF info present")
                print(
                    f"  {icons.skipped} Skipped file       {icons.downsized} Image was downsized     {icons.size_is_smaller} Size reduction (%)\n")

            # Create task for this specific file
            task = self.task
            img_task = _Task(
                event.src_path,
                task.quality,
                task.remove_transparency,
                task.reduce_colors,
                task.max_colors,
                task.max_w,
                task.max_h,
                task.keep_exif,
                task.convert_all,
                task.conv_big,
                task.force_del,
                task.bg_color,
                task.grayscale,
                internal.ignore_size_comparison,
                task.fast_mode,
                task.output_config,
                task.convert_to,
                task.webp_quality,
                task.webp_lossless,
                task.webp_method,
            )

            # Process the image
            result = do_optimization(img_task)

            # Call the callback with our result
            on_result(_to_public_result(result))

        @staticmethod
        def _wait_for_write_finish(filename):
            """Wait until file has been completely written (when file size stabilizes)"""
            import time
            size = -1
            while size != os.stat(filename).st_size:
                size = os.stat(filename).st_size
                time.sleep(0.01)

    # Set up our watcher
    folder = os.path.abspath(base_task.src_path)
    print(f"\nPreparing to watch directory (press CTRL+C to quit):\n {folder}\n")

    event_handler = APIOptimizeImageEventHandler(base_task)
    observer = Observer()
    observer.schedule(event_handler, folder, recursive=True)
    observer.start()

    try:
        import time
        while stop_event is None or not stop_event.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        print("\b \n\n  == Operation was interrupted by the user. ==\n")
    finally:
        observer.stop()
        observer.join()
