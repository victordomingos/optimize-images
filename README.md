# Optimize Images 
[![Github commits (since latest release)](https://img.shields.io/github/commits-since/victordomingos/optimize-images/latest.svg)](https://github.com/victordomingos/optimize-images) ![PyPI](https://img.shields.io/pypi/v/optimize-images)  [![PyPI Python Versions](https://img.shields.io/pypi/pyversions/optimize-images.svg)](https://pypi.org/project/optimize-images/)  ![https://badgen.net/github/contributors/victordomingos/optimize-images](https://badgen.net/github/contributors/victordomingos/optimize-images) [![PyPI Downloads](https://static.pepy.tech/personalized-badge/optimize-images?period=monthly&units=NONE&left_color=GREY&right_color=ORANGE&left_text=monthly+downloads)](https://pepy.tech/projects/optimize-images) [![GitHub License](https://img.shields.io/github/license/victordomingos/optimize-images.svg)](https://github.com/victordomingos/optimize-images/blob/master/LICENSE) 

A command-line interface (CLI) utility written in pure Python to help you 
reduce the file size of images.

This application is intended to be pure Python, with no special dependencies
besides Pillow and watchdog, therefore ensuring compatibility with a wide range of systems.
If you don't have the need for such a strict dependency management, you will 
probably be better served by any several other image optimization utilities 
that are based on some well known external binaries.

Some aditional features can be added which require the presence of other 
third-party packages that are not written in pure Python, but those packages 
and the features depending on them should be treated as optional.

![optimize-images_screenshot](https://user-images.githubusercontent.com/18650184/42172232-5788c43a-7e13-11e8-8094-5811e7fd55c1.png)

If you were just looking for the graphical user interface (GUI) version of this application, it's a separate project: [Optimize Images X](https://github.com/victordomingos/optimize-images-x). 


## Full Documentation:
 * [English](https://github.com/victordomingos/optimize-images/blob/master/docs/docs_EN.md)
 * [Portugu&ecirc;s](https://github.com/victordomingos/optimize-images/blob/master/docs/docs_PT.md)

Please refer to the above links if you want to know about all the options available in this application. For a quick intro, just to get a feeling of what it can do, please keep reading below.

## Installation and dependencies:

To install and run this application, you need to have a working
Python 3.10+ installation. We try to keep the external dependencies at a minimum,
in order to keep compatibility with different platforms. At this moment, we require:

  - Pillow>=12.0.0
  - watchdog>=6.0.0

The easiest way to install it in a single step, including any dependencies, is 
by using this command:

```
pip3 install pillow optimize-images
```

## How to use

The most simple form of usage is to type a simple command in the shell, 
passing the path to an image or a folder containing images as an argument.
The optional `-nr` or `--no-recursion` switch argument tells the application not 
to scan recursively through the subdirectories.

By default, this utility applies lossy compression to JPEG files using a 
variable quality setting between 75 and 80 (by Pillow's scale), that is
dynamically determined for each image according to the amount of change caused
in its pixels, then it removes any EXIF metadata, tries to optimize each
encoder's settings for maximum space reduction and applies the maximum ZLIB
compression on PNG. WebP images are re-encoded to reduce their size while 
preserving any transparency.

You must explicitly pass it a path to the source image file or to the
directory containing the image files to be processed. By default, it will scan 
recursively through all subfolders and process any images found using the 
default or user-provided settings, replacing each original file by its 
processed version if its file size is smaller than the original.

If no space savings were achieved for a given file, the original version will 
be kept instead.

There are many other features and command-line options, like downsizing, 
keeping EXIF data, color palette reduction, WebP optimization, and PNG to JPEG 
(or WebP) conversion. Please check the docs for further information.

**DISCLAIMER:  
Please note that the operation is done DESTRUCTIVELY, by replacing the
original files with the processed ones. You definitely should duplicate the
source file or folder before using this utility, in order to be able to
recover any eventual damaged files or any resulting images that don't have the
desired quality.**
  

## Basic usage

Try to optimize a single image file:

```
optimize-images filename.jpg
```

  
Try to optimize all image files in current working directory and all of its
subdirectories:

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


## For developers

Besides the command-line interface, Optimize Images exposes a small, stable,
UI-free API for use in your own Python applications, in the
`optimize_images.api` module (since version 2.0.0). It can optimize a single
image or a whole folder, with no terminal output.

```python
from optimize_images.api import optimize_single_image

result = optimize_single_image("photo.jpg", quality=70, max_w=1920)
print(result.orig_size, "->", result.final_size)
```

For batch processing, directory watching, the full set of options and the
result fields, see [Programmatic use](./docs/docs_EN.md#programmatic-use-as-a-library)
in the full documentation.


## Getting help

To check the list of available options and their usage, you just need to use one of the 
following commands:


```
optimize-images -h
```

```
optimize-images --help
```
  
  
## Did you find a bug or do you have a suggestion?

Please let me know, by opening a new issue or a pull request.