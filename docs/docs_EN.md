[English](https://github.com/victordomingos/optimize-images/blob/master/docs/docs_EN.md) |
**[Portugu&ecirc;s](https://github.com/victordomingos/optimize-images/blob/master/docs/docs_PT.md)**

# Optimize Images [![Github commits (since latest release)](https://img.shields.io/github/commits-since/victordomingos/optimize-images/latest.svg)](https://github.com/victordomingos/optimize-images)

A command-line interface (CLI) utility written in pure Python to help you reduce the file size of images.

This application is intended to be pure Python, with no special dependencies besides Pillow and watchdog, therefore
ensuring compatibility with a wide range of systems. If you don't have the need for such a strict dependency management,
you will probably be better served by any several other image optimization utilities that are based on some well-known
external binaries.

Some additional features can be added which require the presence of other third-party packages that are not written in
pure Python, but those packages and the features depending on them should be treated as optional.

![optimize-images_screenshot](https://user-images.githubusercontent.com/18650184/42172232-5788c43a-7e13-11e8-8094-5811e7fd55c1.png)

## Contents

* **[Installation and dependencies](#installation-and-dependencies)**

* **[How to use](#how-to-use)**
    * [DISCLAIMER](#disclaimer)
    * [Examples of basic usage](#examples-of-basic-usage)
    * [Getting help on how to use this application](#getting-help-on-how-to-use-this-application)
    * [Format independent options](#format-independent-options)
        - [Image resizing](#image-resizing)
        - [Fast mode](#fast-mode)
        - [Watch directory for new files](#watch-directory-for-new-files)
        - [Maximum number of simultaneous jobs](#maximum-number-of-simultaneous-jobs)
        - [Output configuration](#output-configuration)
        - [SSIM quality control](#ssim-quality-control)
    * [Format specific options](#format-specific-options)
        - [JPEG](#jpeg)
            - [Quality](#quality)
            - [Keep EXIF data](#keep-exif-data)
        - [PNG](#png)
            - [Reduce the number of colors](#reduce-the-number-of-colors)
            - [Maximum number of colors](#maximum-number-of-colors)
            - [Automatic conversion of big PNG images (to JPEG or WebP)](#automatic-conversion-of-big-png-images-to-jpeg-or-webp)
            - [Changing the default background color](#changing-the-default-background-color)
        - [WebP](#webp)
            - [WebP quality](#webp-quality)
            - [Lossless WebP](#lossless-webp)
            - [WebP method (compression effort)](#webp-method-compression-effort)
    * [Other features](#other-features)

* **[Programmatic use (as a library)](#programmatic-use-as-a-library)**
    * [Optimize a single image](#optimize-a-single-image)
    * [Optimize a folder (streaming)](#optimize-a-folder-streaming)
    * [Optimize a folder (aggregate)](#optimize-a-folder-aggregate)
    * [Watch a folder](#watch-a-folder)
    * [Options and results](#options-and-results)
    * [Notes](#notes)

* **[Related projects](#related-projects)**
    * [Optimize Images Docker](#optimize-images-docker)
    * [Optimize Images X](#optimize-images-x)

* **[Running the tests](#running-the-tests)**

* **[Did you find a bug or do you have a suggestion?](#did-you-find-a-bug-or-do-you-have-a-suggestion)**

## Installation and dependencies:

To install and run this application, you need to have a working Python 3.10+ installation. We try to keep the external
dependencies at a minimum, in order to keep compatibility with different platforms. At this moment, we require:

- Pillow==12.0.0
- watchdog==6.0.0

The easiest way to install it in a single step, including any dependencies, is by using this command:

```
pip3 install pillow watchdog optimize-images
```

## Installing the most recent development version (may be unstable):

After cloning this repository, the current development version can be easily, by using the shell command
`pip install -e`, followed by the path to the main project directory (the same directory that has the `setup.py` file).
Alternatively, you can create a virtual environment and use the following command (just replace
`python3.10` with your intended python3 version)

```
python3.10 -m pip install git+https://github.com/victordomingos/optimize-images
```

## How to use

The most simple form of usage is to type a simple command in the shell, passing the path to an image or a folder
containing images as an argument. The optional `-nr` or `--no-recursion` switch argument tells the application not to
scan recursively through the subdirectories.

By default, this utility applies lossy compression to JPEG files using a variable quality setting between 75 and 80 (by
Pillow's scale), that is dynamically determined for each image according to the amount of change caused in its pixels,
then it removes any EXIF metadata, tries to optimize each encoder's settings for maximum space reduction and applies the
maximum ZLIB compression on PNG.

You must explicitly pass it a path to the source image file or to the directory containing the image files to be
processed. By default, it will scan recursively through all subfolders and process any images found using the default or
user-provided settings, replacing each original file by its processed version if its file size is smaller than the
original.

If no space savings were achieved for a given file, the original version will be kept instead.

In addition to the default settings, you may downsize the images to fit a maximum width and/or a maximum height. This
image resizing is done as the first step in the image optimization process.

You may also choose to keep the original EXIF data (if it exists) in the optimized files. Note, however, that this
option is currently available only for JPEG and WebP files.

In PNG files, you will achieve a more drastic file size reduction if you choose to reduce the number of colors using an
adaptive palette. Be aware that by using this option image quality may be affected in a very noticeable way.

Since version 1.3.5, Optimize Images also offers experimental support for MPO images, which are now treated as single
picture JPEG image files (if multiple pictures are present in one MPO file, only the first one will be processed).

Since version 2.1.0, WebP images are also optimized: existing WebP files are re-encoded in place to reduce their size
and PNG images can optionally be converted to WebP instead of JPEG. Animated WebP and animated PNG files are left
untouched, to avoid flattening the animation.

### DISCLAIMER

**Please note that the operation is done DESTRUCTIVELY, by replacing the original files with the processed ones. You
definitely should duplicate the source file or folder before using this utility, in order to be able to recover any
eventual damaged files or any resulting images that don't have the desired quality.**

### Examples of basic usage

Try to optimize a single image file:

```
optimize-images filename.jpg
```

Try to optimize all image files in current working directory and all of its subdirectories:

```
optimize-images ./
```

Try to optimize all image files in current working directory, without recursion:

```
optimize-images -nr ./
```

```
optimize-images --no-recursion ./
```

### Getting help on how to use this application

To check the list of available options and their usage, you just need to use one of the following commands:

```
optimize-images -h
```

```
optimize-images --help
```

### Format independent options:

#### Fast mode:

Some of the operations may eventually be finished sooner by using this option. Generally speaking, this means that the
resulting files will have a slightly bigger size, in order to save instead a few seconds on image processing. Using this
option disables dynamic JPEG quality setting.

Try to optimize all image files in current working directory, with recursion, using fast mode:

```
optimize-images -fm ./
```

```
optimize-images --fast-mode ./
```

#### Image resizing:

These options will be applied individually to each image being processed. Any image that has a dimension exceeding a
specified value will be downsized as the first optimization step. The resizing will not take effect if, after the whole
optimization process, the resulting file size isn't any smaller than the original. These options are disabled by
default.

These optional arguments can be used to constrain the final size of the images:

* Maximum width: `-mw`
* Maximum height: `-mh`

The image will be downsized to a maximum size that fits the specified width and/or height. If the user enters values to
both dimensions, it will calculate the image proportions for each case and use the one that results in a smaller size.

Try to optimize all image files in current working directory, with recursion, downsizing each of them to a maximum width
of 1600 pixels:

```
optimize-images -mw 1600 ./
```

Try to optimize all image files in current working directory, without recursion, downsizing each of them to a maximum
height of 800 pixels:

```
optimize-images -nr -mh 800 ./
```

#### Watch directory for new files:

Use this option when you have a folder which you would like to monitor for new image files and process them as soon as
possible. Optimize Images will watch the specified directory continuously and will optimize automatically any newly
created file. File paths are saved in a temporary list in memory, so that each file should just be processed once per
session.

Files that exist when Optimized Images is started using this option will generally not be processed, but you can force
it, by issuing two consecutive shell commands, first doing a regular pass without the `-wd`
argument to process existing files, then a second call with the `-wd` argument to keep the utility watching for new
files and process them as they are created.

```
optimize-images -wd ./
```

```
optimize-images --watch-directory ./
```

This feature uses the third-party `watchdog` package (a core dependency) and its dependencies, and is only available on
operating systems supported by it. It is not available, for instance, on iOS.

At this time, multiprocessing is not available when using this feature.

#### Maximum number of simultaneous jobs

You can specify the maximum number of simultaneous jobs that should be allowed to run at a given time. The default value
(0), for most platforms, will generate a total of N + 1 processes, where N is the number of CPUs or cores in the system.

```
optimize-images -jobs 16 ./
```

#### Output configuration

In order to specify what text to output, you can use these optional flags:

##### Quiet Mode

With the `--quiet` flag, you'll not see any output except from error messages and exceptions during the optimization.

```
optimize-images --quiet ./
```

##### Only Summary

With this flag, you will not see any output during the optimization and only see the summary when finished.

```
optimize-images --only-summary ./
```

##### Show only the progress

This will only show the overall progress and not the optimization result of each file.

```
$ optimize-images --only-progress ./
... 
[14.0s 57.1%] ✅ 18 🔴 68, saved 44.1 MB
...
```

#### SSIM quality control

The structural similarity index (SSIM) measures how close the encoded result is to the image as it looked just before
the final lossy encoding, on a scale between 0 and 1 where 1 means indistinguishable. The reference is a copy of the
image taken *after* all the transforms, so the score reflects only the loss of the final encoding or format conversion:
options such as resizing (`-mw`/`-mh`), color reduction (`-rc`) and grayscale (`-g`) do not lower it. It applies to
JPEG, WebP, and format conversion, and it requires the optional scikit-image package (install it with
`pip install scikit-image`
or `pip install optimize-images[ssim]`). Note that for PNG files that are not converted to another format the encoding
is lossless, so the score is always 1.0000 and the threshold can never reject them. For images with transparency, the
score is computed over the background color (`-bg`/`-hbg`, white by default).

Use `-ssm` or `--ssim-min THRESHOLD` to keep the original file whenever the result scores below the threshold (a decimal
between 0 and 1, for example 0.95). The threshold is checked *after* encoding: it never changes the quality the encoder
uses (dynamic quality selection, a fixed `-q`, or the conversion settings) — it only decides whether the encoded result
is kept. A result is kept only when it is both at least 1% smaller than the original (below 99% of its size) and at or
above the threshold; with `-nc` (size comparison disabled) only the threshold applies. If the score cannot be computed
for a file, the original is kept (the gate fails closed), so `--ssim-min 0` does not disable the gate: files without a
score are still rejected; omit the option to turn the gate off. Without scikit-image, this option stops the run with a
clear error message.

Recommended intervals differ by regime. Measured across 224 photographs with the current default encoder (dynamic
quality, tuned for the web), in-place scores ranged from 0.929 to 1.0 (median 0.981): 0.90 rejects nothing, and useful
values are **0.93-0.97** — rejection starts above 0.92 and grows quickly (0.95 rejects about 2.2% of the files, roughly
2.5% of the total space savings; 0.96 about 5.5%; 0.97 about 17.6%). Conversion scores are lower: 0.95 rejects 16.6% of
the files with `-ca` and 32.3% with
`-ca -cc webp`, so useful values there are **0.85-0.93**. The option is off by default; enable it with `--ssim-min` when
you want the guarantee.

The score is computed with scikit-image's `structural_similarity`, which uses its default uniform 7x7 window rather
than the Gaussian-weighted window of the original SSIM paper, so scores can be slightly higher (about 0.004) than
tools using the Gaussian version. The recommended thresholds above were calibrated with this implementation.

Computing the score is expensive: it can dominate the run time on folders of very large images, so expect a run with
SSIM enabled to take much longer than it would without it.

```
optimize-images --ssim-min 0.95 ./
```

Use `--show-ssim` (or `--no-show-ssim` to force it off) to display the computed score for each file in the report. The
score is shown automatically whenever `--ssim-min` is used; without scikit-image, `--show-ssim` prints a warning once
and no scores are displayed. `--no-show-ssim` hides the scores of optimized files only: a file rejected because its
score fell below the threshold is still reported with its score and the threshold. Optimized files show it on the
details line; files reported as skipped show it on a second line only when the threshold rejected them — flagged with
the threshold — so they stay distinguishable from files skipped merely for not being smaller (files with no score,
such as animated WebP and animated PNG files, are reported as skipped).

```
optimize-images --show-ssim ./
```

### Format specific options:

The following format specific settings are optional and may be used simultaneously, for instance when processing a
directory that may contain images in more than one format. The appropriate format-specific options entered by the user
will then be automatically selected and applied for each image.

#### JPEG:

##### Quality

Set a fixed value for the quality for JPEG files (an integer value, between 1 and 100), using the `-q` argument, folowed
by the quality value to apply. A lower value will reduce both the image quality and the file size. Using this option
disables the default dynamically variable JPEG quality setting.

Try to optimize all image files in current working directory and all of its subdirectories, applying a quality of 65% to
JPEG files:

```
optimize-images -q 65 ./
```

##### Keep EXIF data

Use the `-ke` or `--keep-exif` option to keep existing EXIF data in JPEG and WebP images (by default, if you don't add
this argument, EXIF data is discarded).

Try to optimize all image files in current working directory and all of its subdirectories, applying a quality of 65% to
JPEG files and keeping the original EXIF data:

```
optimize-images -q 65 -ke ./
```

```
optimize-images --quality 65 --keep-exif ./
```

#### PNG:

##### Reduce the number of colors

To reduce the number of colors (PNG) using an adaptive color palette with dithering, use the `-rc` optional argument.
This option can have a big impact on file size, but please note that will also affect image quality in a very noticeable
way, especially in images that have color gradients and/or transparency.

Try to optimize a single image file in current working directory, applying and adaptive color palette with the default
amount of colors (255):

```
optimize-images -rc ./imagefile.png
```

##### Maximum number of colors

Use the  `-mc` optional argument to specify the maximum number of colors for PNG images when using the reduce colors
(-rc) option (an integer value, between 0 and 255). The default value is 255.

Try to optimize a single image file in current working directory, reducing the color palette to a specific value:

```
optimize-images -rc -mc 128 ./imagefile.png
```

Try to optimize all image files in current working directory and all of its subdirectories, applying a quality of 65% to
JPEG files and reducing the color palette of PNG files to just 64 colors:

```
optimize-images -q 60 -rc -mc 64 ./
```

Please note that indicating a very small number of colors may remove transparency, replacing it with unintended colors.
In such cases, you will probably achieve better results by combining this option with explicit transparency removal
(`-rt`) and background color replacement (`-bg` or `-hbg`).

For instance, to optimize a single PNG image file, reducing the color palette to 8 colors maximum, removing transparency
and applying a white background:

```
optimize-images -rc -mc 8 -rt -hbg ffffff ./imagefile.png
```

##### Automatic conversion of big PNG images (to JPEG or WebP)

Automatically convert big PNG images that have a large number of colors (presumably a photo or photo-like image) to a
more efficient format. It uses an algorithm to determine whether the conversion is worthwhile and decides automatically
about it. Use `-cb` (or `--convert-big`) for this automatic selection (specific to big photographic PNGs), or `-ca` (or
`--convert-all`)
to convert every image found, regardless of its source format. By default, the original files remain untouched and are
kept alongside the converted images in their original folders.

The conversion target is JPEG by default. Use `-cf` (or `--convert-to FORMAT`)
to choose another output format. The available targets depend on the codecs compiled into the Pillow build in use
(typically `jpeg`, `png`, `webp`, `avif`
and `jpeg2000`); run with `-h` to see the choices on your system. Unlike JPEG, formats such as WebP, AVIF and PNG keep
any transparency.

Conversion honours the size comparison just like in-place optimization: the converted file is kept only when it actually
turns out at least 1% smaller than the original (below 99% of its size), unless you disable the comparison with `-nc`.
This is what makes it safe to request any target - if it would not save space, it is simply skipped.

**IMPORTANT: IF A FILE WITH THE SAME NAME AND TARGET EXTENSION ALREADY EXISTS, IT WILL BE REPLACED BY THE FILE RESULTING
FROM THIS CONVERSION.**

```
optimize-images -cb ./
```

Convert every image to WebP instead of JPEG:

```
optimize-images -ca --convert-to webp ./
```

You may force the deletion of the original PNG files when converting, by adding the `-fd` or `--force-delete` argument:

```
optimize-images -cb -fd ./
```

```
optimize-images --convert_big --force-delete
```

##### Changing the default background color

By default, when removing transparency or converting from PNG to JPEG it will apply a white background color. You may
choose a different background by using the argument `-bg` followed by 3 integer numbers, separated by spaces, between 0
and 255, for Red, Green and Blue. E.g.:
`255 0 0` for a pure red color).

To convert a big PNG image with some transparency (like, for instance, macOS screenshots) applying a black background:

```
optimize-images -cb -bg 0 0 0 ./image.png
```

If you prefer to use hexadecimal values, like those that are usual in HTML code, you may alternatively use the argument
`-hbg` followed by the color code without the hash (#) character. E.g.: `00FF00` for a pure green color).

To convert a big PNG image with some transparency applying a pure green background:

```
optimize-images -cb -hbg 00FF00 ./image.png
```

#### WebP:

Existing WebP image files are optimized in place, by re-encoding them with the settings below. WebP keeps its
transparency (alpha channel) unless you also ask to remove it with `-rt`. Animated WebP and animated PNG files are
detected and left untouched, to avoid flattening the animation.

You can also convert PNG images to WebP instead of JPEG - see
[Automatic conversion of big PNG images (to JPEG or WebP)](#automatic-conversion-of-big-png-images-to-jpeg-or-webp).

##### WebP quality

Set the quality for WebP files (an integer between 1 and 100) using the `-wq`
argument. It defaults to 80. A lower value reduces both image quality and file size. In lossless mode (see below) this
value controls the compression effort instead.

Try to optimize all WebP files in the current directory with a quality of 75:

```
optimize-images -wq 75 ./
```

##### Lossless WebP

Use the `-wl` or `--webp-lossless` argument to encode WebP images in lossless mode. This preserves every pixel exactly,
but for photographic images it usually produces much larger files than lossy mode.

```
optimize-images -wl ./
```

##### WebP method (compression effort)

Use the `-wm` argument to set the WebP compression method, an integer between 0 and 6, where 6 is the slowest but
usually gives the best compression. It defaults to 6.

```
optimize-images -wm 4 ./
```

### Other features

Check the installed version of this application:

```
optimize-images -v
```

```
optimize-images --version
```

View a list of the supported image formats by their usual filename extensions (please note that files without the
corresponding file extension will be ignored):

```
optimize-images -s
```

```
optimize-images --supported
```

To inspect a single image and print its metadata — format, mode, dimensions, alpha, palette size, progressive/interlaced
flags, frame count, DPI, ICC profile and EXIF, use the `-i`/`--info` option:

```
optimize-images -i photo.jpg
```

```
optimize-images --info photo.jpg
```

## Programmatic use (as a library)

Since version 2.0.0, the package provides a stable, UI-free integration API in
`optimize_images.api` for embedding the optimization logic in your own apps. Prefer it over the lower-level modules,
which are internal and may change without notice.

### Optimize a single image

```python
from optimize_images.api import optimize_single_image

result = optimize_single_image("photo.jpg", quality=70, max_w=1920)
print(result.was_optimized, result.orig_size, result.final_size)
```

Options are keyword-only: `quality`, `max_w`, `max_h`, `reduce_colors`,
`max_colors`, `remove_transparency`, `bg_color`, `grayscale`, `keep_exif`,
`convert_all`, `conv_big`, `force_del`, `fast_mode`, `ignore_size_comparison`,
`convert_to`, `webp_quality`, `webp_lossless`, `webp_method`, `ssim_min`,
`show_ssim`. The conversion target is set by `convert_to` (`'jpeg'` by default, or `'webp'`); WebP encoding is tuned
with `webp_quality`,
`webp_lossless` and `webp_method`. `ssim_min` keeps the original file when the result scores below the minimum
structural similarity, and `show_ssim`
requests the computed score in the result; both rely on the optional scikit-image package.
When only `ssim_min` is given (`show_ssim` is `False`), results rejected for
not being at least 1% smaller are not scored (`ssim` is `None`), and
`show_ssim` always returns the score.

### Optimize an image in memory (bytes in, bytes out)

When images are stored as binary data rather than files — for example inside a content management system, an object
store or a database — and no file path is available, use `optimize_image_data`. It takes the image bytes and returns the
optimized bytes together with a result object:

```python
from optimize_images.api import optimize_image_data

optimized, result = optimize_image_data(original_bytes, quality=70, max_w=1920)
if result.was_optimized:
    store(optimized)   # smaller image; otherwise `optimized` is the original
```

It keeps the original format and accepts the same processing options as
`optimize_single_image` except the file/conversion-specific ones: `quality`,
`max_w`, `max_h`, `reduce_colors`, `max_colors`, `remove_transparency`,
`bg_color`, `grayscale`, `keep_exif`, `fast_mode`, `ignore_size_comparison`,
`webp_quality`, `webp_lossless`, `webp_method`, `ssim_min`, `show_ssim`, plus an optional `name` echoed back in the
result. When optimizing does not help (and the size comparison is not disabled) the original bytes are returned
unchanged. Format conversion is not supported through this entry point.

### Convert an image in memory (bytes in, bytes out)

The in-memory counterpart of format conversion, for the same binary-only callers. `convert_image_data` converts the
bytes to another format and returns the converted bytes plus the resulting format:

```python
from optimize_images.api import convert_image_data

webp_bytes, result = convert_image_data(png_bytes, to="webp", webp_quality=80)
if result.was_optimized:
    store(webp_bytes, content_type="image/" + result.result_format.lower())
```

`to` is the target format (`'jpeg'`, `'png'`, `'webp'`, and `'avif'` or
`'jpeg2000'` when the Pillow build supports them), validated against the codecs actually available. Always check
`result.result_format` to know the format of the returned bytes: when converting would not shrink the image (and the
size comparison is not disabled) the **original** bytes and format are returned unchanged; converting to the source's
own format optimizes it in place; multi-frame sources (animations) are returned unchanged. It accepts the common options
`quality`, `max_w`, `max_h`, `remove_transparency`, `bg_color`,
`grayscale`, `keep_exif`, `ignore_size_comparison`, `webp_quality`,
`webp_lossless`, `webp_method`, `ssim_min`, `show_ssim`, and an optional
`name`.

### Optimize a folder (streaming)

Yields each result as it is processed — ideal for progress reporting:

```python
from optimize_images.api import PublicBatchOptions, optimize_as_batch_stream

options = PublicBatchOptions(src_path="./images", quality=75, jobs=4)
for r in optimize_as_batch_stream(options):
    print(r.img, "saved", r.orig_size - r.final_size, "bytes")
```

### Optimize a folder (aggregate)

Blocks and returns totals:

```python
from optimize_images.api import PublicBatchOptions, optimize_as_batch

summary = optimize_as_batch(PublicBatchOptions(src_path="./images"))
print(summary.optimized_files, "of", summary.found_files,
      "-", summary.total_bytes_saved, "bytes saved")
```

### Watch a folder

```python
import threading
from optimize_images.api import PublicBatchOptions, watch_directory

stop = threading.Event()
options = PublicBatchOptions(src_path="./incoming", quality=80)
watch_directory(options, lambda r: print("optimized:", r.img), stop)
# call stop.set() from another thread to end watching
```

### Inspect image metadata

`inspect_image(path)` returns an `ImageMetadata` object with the image's intrinsic properties and its EXIF grouped by
IFD section (`image`, `camera`,
`gps`), with raw values. `format_exif(metadata.exif)` is an optional helper that turns those raw values into
display-ready strings using standardized EXIF semantics (units such as `f/1.8` and `50 mm`, enumerations such as
`Orientation`, and combined GPS coordinates).

```python
from optimize_images.api import inspect_image, format_exif

meta = inspect_image("photo.jpg")
print(meta.image_format, meta.width, meta.height, meta.has_alpha)

for section, tags in format_exif(meta.exif).items():
    print(section)
    for name, value in tags.items():
        print(f"  {name}: {value}")
```

### Options and results

`PublicBatchOptions` holds every setting; only `src_path` is required (defaults include `quality=80`, `recursive=True`,
`jobs=0` meaning auto-detect). Each optimized file is reported as a `PublicTaskResult` with:
`img`, `orig_format`/`result_format`, `orig_mode`/`result_mode`,
`orig_colors`/`final_colors`, `orig_size`/`final_size` (bytes), `ssim` (the structural similarity score, or None when it
was not computed — when only `ssim_min` was given and the file was rejected by
the size check, when scikit-image is missing and `show_ssim` was requested,
or when the score was not otherwise requested), and the flags
`was_optimized`, `was_downsized`, `had_exif`, `has_exif`. `optimize_as_batch`
returns a `PublicBatchResult` with the file list plus aggregate counts, total size, bytes saved and elapsed seconds.

### Notes

- Worker count is auto-detected from the platform (CPU) unless you set
  `options.jobs` to a non-zero value.
- `watch_directory` prints a legend and banner to standard output, and uses the
  `watchdog` package (a core dependency); if it is missing it raises
  `ImportError`.
- SSIM is only available when the optional scikit-image package is installed (or with the `[ssim]` extra): `ssim_min`
  raises `optimize_images.exceptions.OISSIMNotAvailableError` when it is missing, while `show_ssim` simply yields `None`
  scores; the CLI prints a warning once when `--show-ssim` was requested without it. An `ssim_min` outside 0.0-1.0
  (NaN included) raises `ValueError`.
- `optimize_as_batch`, `optimize_as_batch_stream` and `optimize_single_image`
  raise `optimize_images.exceptions.OIImagesNotFoundError` when a path resolves to no images; `watch_directory` raises
  the same error when the path is not an existing folder.

### Related projects

#### [Optimize Images Docker](https://github.com/varnav/optimize-images-docker)

A third-party dockerized implementation of Optimize Images. It includes a few interesting optimizations, like the usage
of a recent version of [mozjpeg](https://github.com/mozilla/mozjpeg) library, or a Pillow binary compiled
with [libimagequant](https://github.com/ImageOptim/libimagequant), which should result in faster and more efficient
compression.

#### [Optimize Images X](https://github.com/victordomingos/optimize-images-x)

A desktop app written in Python, that exposes and unlocks the full power of Optimize Images in a nice graphical user
interface, to help you reduce the file size of images. Just like its CLI companion app, it can process a single file, a
folder’s root or all images in a folder, recursively. Multiple image processing tasks are automatically distributed to
all available CPU cores. Additionally, it includes a “watch folder” feature that continuously monitors a specified
folder for new image files and processes them right after they’re created or placed in that folder.

## Running the tests

The test suite uses pytest. From a clone of the repository, in a virtual environment:

```
python -m pip install -r requirements-dev.txt
python -m pytest
```

Run the commands from the repository root (`pytest.ini` points pytest to the `tests` folder and to the source code), so
installing the package with `pip install -e .` is not needed. `requirements-dev.txt` includes scikit-image; without it,
the SSIM tests are skipped. If a package has no wheel yet for your Python version, install the other requirements one by
one, or let `scripts/test_matrix.py --install` do it. Useful variations:

```
python -m pytest -m "not slow"             # skip the long SSIM regression matrices
python -m pytest tests/test_webp.py        # one file
python -m pytest --cov=optimize_images     # with a coverage report
```

To test every supported Python version, with and without free-threading, use `scripts/test_matrix.py`. It runs the
suite in one virtual environment per version, kept at the repository root and named after the version (`venv311`,
`venv312`, `venv313`, `venv313t`, ... `venv315t`, where `t` is the free-threaded build), and prints a table with the
results:

```
python scripts/test_matrix.py --create              # create missing venvs, then test them all
python scripts/test_matrix.py                       # test the existing venvs
python scripts/test_matrix.py --install             # update their requirements first
python scripts/test_matrix.py --only 3.14t,3.13 --fast
python scripts/test_matrix.py -- -k watch           # arguments after -- go to pytest
```

`--create` needs the matching interpreters on the `PATH` (`python3.11`, ..., `python3.13t`, ...; when there are several,
the newest patch release is used; on Windows, create the venvs by hand with the `py` launcher); `--recreate` rebuilds
the selected venvs, for instance after a new Python release. `--install` and `--create` install the requirements one by
one and prefer released wheels, so a package that has no wheel yet for a new Python (e.g. scikit-image on 3.15) only
skips its tests, which the table reports. `--jobs` sets how many venvs are tested at the same time. The script uses only
the standard library. The test images in `tests/test-images/` must never be modified: the tests work on copies.

## Did you find a bug or do you have a suggestion?

Please let me know, by opening a new issue or a pull request.