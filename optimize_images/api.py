from optimize_images.data_structures import TaskResult, Task
from optimize_images.do_optimization import do_optimization


def optimize_as_batch(src_path, watch_dir=False, recursive=True, quality=80, remove_transparency=False,
                      reduce_colors=False, max_colors=256, max_w=0, max_h=0, keep_exif=False,
                      convert_all=False, conv_big=False, force_del=False, bg_color=(255, 255, 255),
                      grayscale=False, ignore_size_comparison=False, fast_mode=False, jobs=0):
    """ Try to reduce the file size of all images found in the specified path,
        using The specified parameters.

    :param src_path:
    :param watch_dir:
    :param recursive:
    :param quality:
    :param remove_transparency:
    :param reduce_colors:
    :param max_colors:
    :param max_w:
    :param max_h:
    :param keep_exif:
    :param convert_all:
    :param conv_big:
    :param force_del:
    :param bg_color:
    :param grayscale:
    :param ignore_size_comparison:
    :param fast_mode:
    :param jobs:
    """
    from optimize_images.__main__ import optimize_batch as optimize

    optimize(src_path, watch_dir, recursive, quality, remove_transparency, conv_big,
             force_del, reduce_colors, max_colors, max_w, max_h, keep_exif, convert_all,
             bg_color, grayscale, ignore_size_comparison, fast_mode, jobs)


def optimize_single_img(task: Task) -> TaskResult:
    """ Try to reduce file size of an image.

       Expects a Task object containing all the parameters for the image processing.

       The actual processing is redirected through do_optimization to the
       corresponding function, according to the detected image format.

       :param task: A Task object containing all the parameters for the image processing.
       :return: A TaskResult object containing information for single file report.
       """
    return do_optimization(task)
