# encoding: utf-8
import os
import platform
import shutil
import signal
import sys
from concurrent.futures import Executor, ThreadPoolExecutor
from contextlib import contextmanager
from functools import lru_cache
from typing import TYPE_CHECKING, TypeAlias

if TYPE_CHECKING:
    from concurrent.futures import ProcessPoolExecutor

# ProcessPoolExecutor is imported only where it is returned: its module pulls
# in multiprocessing (6-13 ms per start), which threads-only platforms never use.
ExecutorClassType: TypeAlias = "type[ThreadPoolExecutor] | type[ProcessPoolExecutor]"

# Measured 2026-10-02 on 224-file corpus, 18-core Mac: SSIM work competes for
# memory so >8 workers makes every task much slower. 8 workers gives the best
# and most stable timing across Python and free-threaded builds.
SSIM_WORKER_CAP = 8


class IconGenerator:
    """Provides icons for file status output, with Unicode or ASCII fallback."""

    __slots__ = ('use_unicode', 'arrow', 'info', 'downsized', 'optimized',
                 'skipped', 'size_is_smaller', 'legend_text')

    def __init__(self) -> None:
        system = platform.system()
        use_unicode = system not in ("Windows", "Haiku")

        # Even on supported platforms, stdout may use an encoding that cannot
        # represent Unicode icons (e.g. Windows ANSI code page when output is
        # piped or redirected). Try encoding the legend text; if it fails,
        # fall back to ASCII.
        if use_unicode and sys.stdout.encoding:
            try:
                ("✅ Optimized file     ℹ️  EXIF info present"
                 .encode(sys.stdout.encoding))
            except (LookupError, UnicodeEncodeError):
                use_unicode = False

        self.use_unicode = use_unicode
        self.arrow = "->"

        if self.use_unicode:
            self.info = "ℹ️"
            self.downsized = "⤵ "
            self.optimized = "✅"
            self.skipped = "🔴"
            self.size_is_smaller = "🔻"
            self.legend_text = (
                "\n\nUsing these symbols:\n\n"
                "  ✅ Optimized file     ℹ️  EXIF info present\n"
                "  🔴 Skipped file       ⤵  Image was downsized     🔻 Size reduction (%)\n"
            )
        else:
            self.info = "i"
            self.downsized = "V"
            self.optimized = "OK"
            self.skipped = "--"
            self.size_is_smaller = "v"
            self.legend_text = (
                "\n\nUsing these symbols:\n\n"
                "  OK Optimized file      i EXIF info present\n"
                "  -- Skipped file        V Image was downsized      v Size reduction\n"
            )

    def print_legend(self) -> None:
        """Print a legend explaining the icons in use."""
        print(self.legend_text)


@lru_cache(maxsize=1)
def is_free_threaded() -> bool:
    """
    Detect if running in free-threaded Python (3.13t+).
    Returns True if GIL is disabled.
    """
    return hasattr(sys, '_is_gil_enabled') and not sys._is_gil_enabled()


@lru_cache(maxsize=1)
def get_cpu_count() -> int:
    """Get CPU count with caching and fallback."""
    try:
        # Use os.cpu_count() for better compatibility
        count = os.cpu_count()
        return count if count else 4
    except (AttributeError, NotImplementedError):
        return 4


def select_executor(free_threaded: bool, os_name: str, system: str,
                    num_cpus: int) -> tuple[ExecutorClassType, int]:
    """Pure executor-selection policy: choose the pool class and default worker
    count from the platform indicators, with no environment access.

    Kept separate from adjust_for_platform() so it can be tested directly with
    explicit values, instead of mutating the process-global ``os.name`` (which
    also drives path semantics and corrupts unrelated machinery).
    """
    if free_threaded:
        # Free-threaded Python: threads are truly parallel.
        return ThreadPoolExecutor, num_cpus
    if os_name == "nt":
        # Windows: ThreadPoolExecutor to avoid ProcessPoolExecutor overhead.
        return ThreadPoolExecutor, min(num_cpus * 2, 32)
    if system == "Darwin":
        # macOS: ThreadPoolExecutor for better resource handling.
        return ThreadPoolExecutor, min(num_cpus * 4, 64)
    # Unix/Linux: ProcessPoolExecutor to bypass the GIL for CPU-intensive work.
    from concurrent.futures import ProcessPoolExecutor
    return ProcessPoolExecutor, num_cpus + 1


def ignore_sigint() -> None:
    """Worker-process initializer: leave Ctrl-C to the main process.

    A terminal Ctrl-C reaches every process in the group; a worker killed
    while writing an image would leave a truncated file instead of the
    original. Workers start with SIGINT blocked (see sigint_deferred), so
    it is ignored before it is unblocked.
    """
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    if hasattr(signal, 'pthread_sigmask'):
        signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGINT})


@contextmanager
def sigint_deferred():
    """Block Ctrl-C in this thread while worker processes are started.

    Workers inherit the blocked signal mask, so a Ctrl-C cannot kill one
    while it is still starting up (before ignore_sigint runs); this thread
    receives the Ctrl-C as soon as the block ends. No-op where
    pthread_sigmask is missing (Windows, which only uses threads).
    """
    if not hasattr(signal, 'pthread_sigmask'):
        yield
        return
    previous = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGINT})
    try:
        yield
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, previous)


def create_executor(executor_class: ExecutorClassType, workers: int) -> Executor:
    """Create the pool; process pools get workers that ignore Ctrl-C."""
    if issubclass(executor_class, ThreadPoolExecutor):
        return executor_class(max_workers=workers)
    return executor_class(max_workers=workers, initializer=ignore_sigint)


@lru_cache(maxsize=1)
def adjust_for_platform() -> tuple[int, ExecutorClassType, int]:
    """
    Adjusts to allow fine-tuning the program's execution according to
    the current platform and to return the optimal executor type.

    Returns:
        tuple: (line_width, executor_class, default_workers)
    """
    # Get cached CPU count
    num_cpus = get_cpu_count()

    # Determine terminal width
    try:
        line_width = shutil.get_terminal_size((80, 24)).columns
    except (OSError, ValueError):
        line_width = 80

    executor_class, default_workers = select_executor(
        is_free_threaded(), os.name, platform.system(), num_cpus)

    return line_width, executor_class, default_workers


def effective_worker_count(default_workers: int, ssim_active: bool) -> int:
    """Cap parallel workers when the SSIM quality gate is active.

    When ``ssim_active`` is True (``ssim_min`` or ``show_ssim``), scipy
    SSIM work competes for memory across threads, so 8 workers is the
    measured sweet-spot.  The cap is a minimum so smaller platform
    defaults are preserved.
    """
    if ssim_active:
        return min(default_workers, SSIM_WORKER_CAP)
    return default_workers