import os
import time

try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer
except ImportError:
    print("Watchdog is not available.")
    exit(1)

from optimize_images.data_structures import Task
from optimize_images.do_optimization import do_optimization
from optimize_images.reporting import show_file_status, show_final_report
from optimize_images.platforms import adjust_for_platform, IconGenerator


def is_image(filepath):
    if not os.path.isfile(filepath):
        return False
    else:
        extension = os.path.splitext(filepath)[1][1:]
        return extension.lower() in ['jpg', 'jpeg', 'png']


def optimize_image(img_path):
    print(img_path)


def wait_for_write_finish(filename):
    # https://stackoverflow.com/a/23525690/6167478 (by goncalopp@stackoverflow)
    last_size, size = -1, 0
    while size != last_size:
        last_size, size = size, os.stat(filename).st_size


class OptimizeImageEventHandler(FileSystemEventHandler):
    def __init__(self, t: Task):
        super().__init__()
        self.t = t
        self.paths_to_ignore = []
        self.new_files = 0
        self.optimized_files = 0
        self.total_bytes_saved = 0
        self.total_src_size = 0

        self.line_width, _, _ = adjust_for_platform()
        self.icons = IconGenerator()

    def on_created(self, event):
        t = self.t
        if '~temp~' in event.src_path:
            return
        if event.is_directory:
            return
        if event.src_path in self.paths_to_ignore:
            return

        self.paths_to_ignore.append(event.src_path)
        if is_image(event.src_path) and '~temp~' not in event.src_path:
            wait_for_write_finish(event.src_path)
            self.new_files += 1

            img_task = Task(event.src_path, t.quality, t.remove_transparency,
                            t.reduce_colors, t.max_colors, t.max_w, t.max_h,
                            t.keep_exif, t.convert_all, t.conv_big, t.force_del,
                            t.bg_color, t.grayscale, t.no_size_comparison,
                            t.fast_mode)

            r = do_optimization(img_task)
            self.total_src_size += r.orig_size
            if r.was_optimized:
                self.optimized_files += 1
                self.total_bytes_saved += r.orig_size - r.final_size

            show_file_status(r, self.line_width, self.icons)


def watch_for_new_files(t: Task):
    folder = os.path.abspath(t.src_path)
    print(f"\nPreparing to watch directory (press CTRL+C to quit):\n {folder}\n")

    event_handler = OptimizeImageEventHandler(t)
    observer = Observer()
    observer.schedule(event_handler, folder, recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\b \n\n  == Operation was interrupted by the user. ==\n")
        observer.stop()
    observer.join()

    if event_handler.new_files > 0:
        show_final_report(event_handler.new_files,
                          event_handler.optimized_files,
                          event_handler.total_src_size,
                          event_handler.total_bytes_saved,
                          -1)
    else:
        print("No files were processed.\n")
