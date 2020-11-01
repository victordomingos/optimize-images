# Optimize Images [![Github commits (since latest release)](https://img.shields.io/github/commits-since/victordomingos/optimize-images/latest.svg)](https://github.com/victordomingos/optimize-images) ![PyPI](https://img.shields.io/pypi/v/optimize-images) ![PyPI - Downloads](https://img.shields.io/pypi/dm/optimize-images)
A command-line interface (CLI) utility written in pure Python to help you 
reduce the file size of images.

This application is intended to be pure Python, with no special dependencies
besides Pillow, therefore ensuring compatibility with a wide range of systems,
including iPhones and iPads running Pythonista 3. If you don't have the need
for such a strict dependency management, you will probably be better served
by any several other image optimization utilities that are based on some well
known external binaries.

![optimize-images_screenshot](https://user-images.githubusercontent.com/18650184/42172232-5788c43a-7e13-11e8-8094-5811e7fd55c1.png)


## Full Documentation:
 * [English](https://github.com/victordomingos/optimize-images/blob/master/docs/docs_EN.md)
 * [Portugu&ecirc;s](https://github.com/victordomingos/optimize-images/blob/master/docs/docs_PT.md)

Please refer to the above links if you want to know about all the options available in this application. For a quick intro, just to get a feeling of what it can do, please keep reading below.

## Installation and dependencies:

To install and run this application, you need to have a working
Python 3.6+ installation. We try to keep the external dependencies at a minimum,
in order to keep compatibility with different platforms, including Pythonista
on iOS. At this moment, we require:

  - Pillow>=8.0.1
  - piexif>=1.1.3
  - watchdog>=0.10.3

The easiest way to install it in a single step, including any dependencies, is 
by using this command:

```
pip3 install pillow optimize-images
```

If you are able to swap Pillow with the faster version 
[Pillow-SIMD](https://github.com/uploadcare/pillow-simd), you should be able
to get a considerably faster speed. For that reason, we provide, as a 
friendly courtesy, an optional shell script (`replace_pillow__macOS.sh`) to 
replace Pillow with the faster Pillow-SIMD on macOS. Please notice, however, 
that it usually requires a compilation step and it was not throughly tested 
by us, so your mileage may vary.

You can also use this application on iOS, using an called
[Pythonista 3](http://omz-software.com/pythonista/) (which is, among other
things, a very nice environment for developing and/or running pure Python
applications on iOS). Please check the detailed install procedure full in the 
user documentation.

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
compression on PNG.

You must explicitly pass it a path to the source image file or to the
directory containing the image files to be processed. By default, it will scan 
recursively through all subfolders and process any images found using the 
default or user-provided settings, replacing each original file by its 
processed version if its file size is smaller than the original.

If no space savings were achieved for a given file, the original version will 
be kept instead.

There are many other features and command-line options, like downsizing, 
keeping EXIF data, color palete reduction, PNG to JPEG conversion. Please 
check the docs for further information.

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
