def optimizer(src_path, watch_dir=False, recursive=True, quality=80, remove_transparency=False,
              reduce_colors=False, max_colors=256, max_w=0, max_h=0, keep_exif=False,
              convert_all=False, conv_big=False, force_del=False, bg_color=(255, 255, 255),
              grayscale=False, ignore_size_comparison=False, fast_mode=False, jobs=0):

    from optimize_images.__main__ import optimizer as app

    app(src_path, watch_dir, recursive, quality, remove_transparency, conv_big,
        force_del, reduce_colors, max_colors, max_w, max_h, keep_exif, convert_all,
        bg_color, grayscale, ignore_size_comparison, fast_mode, jobs)
