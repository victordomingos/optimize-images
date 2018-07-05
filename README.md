**[English](https://github.com/victordomingos/optimize-images/blob/master/README.md)** | [Portugu&ecirc;s](https://github.com/victordomingos/optimize-images/blob/master/docs/README_PT.md)


# Optimize Images [![Github commits (since latest release)](https://img.shields.io/github/commits-since/victordomingos/optimize-images/latest.svg)](https://github.com/victordomingos/optimize-images)
A command-line interface (CLI) utility written in pure Python to help you 
reduce the file size of images.

This application is intended to be pure Python, with no special dependencies
besides Pillow, therefore ensuring compatibility with a wide range of systems,
including iPhones and iPads running Pythonista 3. If you don't have the need
for such a strict dependency management, you will certainly be better served
by any several other image optimization utilities that are based on some well
known external binaries.

![optimize-images_screenshot](https://user-images.githubusercontent.com/18650184/42172232-5788c43a-7e13-11e8-8094-5811e7fd55c1.png)


## Contents
* **[Installation and dependencies](#installation-and-dependencies)**
   - [On regular desktop operating systems](#on-regular-desktop-operating-systems)
   - [On iPhone or iPad (in Pythonista 3 for iOS)](#on-iphone-or-ipad-in-pythonista-3-for-ios)
   
* **[How to use](#how-to-use)**
   * [DISCLAIMER](#disclaimer)
   * [Examples of basic usage](#examples-of-basic-usage)
   * [Getting help on how to use this application](#getting-help-on-how-to-use-this-application)
   * [Format independent options](#format-independent-options)
       - [Image resizing](#image-resizing)
   * [Format specific options](#format-specific-options)
       - [JPEG](#jpeg)
          - [Quality](#quality)
          - [Keep EXIF data](#keep-exif-data)
       - [PNG](#png)
          - [Reduce the number of colors](#reduce-the-number-of-colors)
          - [Maximum number of colors](#maximum-number-of-colors)
          - [Automatic conversion of big PNG images to JPEG](#automatic-conversion-of-big-png-images-to-jpeg)
          - [Changing the default background color](#changing-the-default-background-color)
   * [Other features](#other-features)
   
* **[Did you find a bug or do you have a suggestion?](#did-you-find-a-bug-or-do-you-have-a-suggestion)**


## Installation and dependencies:

### On regular desktop operating systems

The current development version can be installed with `pip install -e`,
followed by the path to the main project directory (the same directory that
has the `setup.py` file). To run this application, you need to have a working
Python 3.6+ instalation. We try to keep the external dependencies at a minimum,
in order to keep compatibility with different plataforms, including Pythonista
on iOS. At this moment, we require:

  - Pillow==5.1.0
  - piexif==1.0.13

Note: If you are on a Mac with Python 3.6 and macOS X 10.11 El Capitan or
earlier, you should use Pillow 5.0.0 instead. In case you have already
migrated to Python 3.7, you should be fine with Pillow 5.1.0.

We plan to submit this to PyPI as soon as possible, in order to provide a more
straight-forward instalation and upgrade process. While that doesn't happen,
please feel free to take a look at the last section and maybe consider
contributing to this project.


### On iPhone or iPad (in Pythonista 3 for iOS)

First you will need a Python environment and a command-line shell compatible
with Python 3. Presently, it means you need to have an app called
[Pythonista 3](http://omz-software.com/pythonista/) (which is, among other
things, a very nice environment for developing and/or running pure Python
applications on iOS).

Then you need to install
[StaSh](https://github.com/ywangd/stash), which is a Python-based shell
application for Pythonista. It will enable you to use useful commands like
`wget`, `git clone`, `pip install` and many others. It really deserves an home
screen shortcut on your iPhone or iPad.

After following the instructions for
StaSh installation, you may need to update it to a more recent version. Try
this command:

```
selfupdate.py -f bennr01:command_testing
```

Then force-quit and restart Pythonista and launch StaSh again. It should now
be running in Python 3. You may now try to install this application, directly
from this git repository:

```
pip install victordomingos/optimize-images
```

If all goes well, it should install any dependencies, place a new `optimize_images`
package inside the `~/Documents/site-packages-3/` folder and create an
entrypoint script named `optimize-images.py` in `stash_extensions/bin`.

Currently, on Pythonista/iOS we require:

  - piexif==1.0.13

Then force-quit and launch StaSh again. You should now be able to run this
application directly from the shell or by creating a home screen shortcut
with the required arguments to the entrypoint script
`~/Documents/stash_extensions/bin/optimize-images.py`, to optimize any
image files that you may have inside your Pythonista environment.



## How to use

The most simple form of usage is to type a simple command in the shell, 
passing the path to an image or a folder containing images as an argument.
The optional -nr or --no-recursion switch argument tells the application not 
to scan recursively through the subdirectories.

By default, this utility applies lossy compression to JPEG files using a 
quality setting of 80% (by Pillow's scale), removes any EXIF metadata, tries 
to optimize each encoder's settings for maximum space reduction and applies 
the maximum ZLIB compression on PNG. 

You must explicitly pass it a path to the source image file or to the
directory containing the image files to be processed. By default, it will scan 
recursively through all subfolders and process any images found using the 
default or user-provided settings, replacing each original file by its 
processed version if its file size is smaller than the original.

If no space savings were achieved for a given file, the original version will 
be kept instead.

In addition to the default settings, you may downsize the images to fit a 
maximum width and/or a maximum height. This image resizing is done as the 
first step in the image optimization process. 

You may also choose to keep the original EXIF data (if it exists) in the 
optimized files. Note, however, that this option is currently available only 
for JPEG files. 

In PNG files, you will achieve a more drastic file size reduction if you 
choose to reduce the number of colors using an adaptive palette. Be aware 
that by using this option all PNG images will loose transparency and image 
quality may be affected in a very noticeable way.


### DISCLAIMER
**Please note that the operation is done DESTRUCTIVELY, by replacing the
original files with the processed ones. You definitely should duplicate the
source file or folder before using this utility, in order to be able to
recover any eventual damaged files or any resulting images that don't have the
desired quality.**
  

### Examples of basic usage

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


### Getting help on how to use this application

To check the list of available options and their usage, you just need to use one of the 
following commands:


```
optimize-images -h
```

```
optimize-images --help
```
  

### Format independent options:

#### Image resizing:

These options will be applied individually to each image being processed. Any 
image that has a dimension exceeding a specified value will be downsized as 
the first optimization step. The resizing will not take effect if, after the 
whole optimization process, the resulting file size isn't any smaller than 
the original. These options are disabled by default.

These optional arguments can be used to constrain the final size of the images:

* Maximum width: `-mw` or `--max-width` 
* Maximum height: `-mh` or `--max-height`

The image will be downsized to a maximum size that fits the specified 
width and/or height. If the user enters values to both dimensions, it will 
calculate the image proportions for each case and use the one that results in 
a smaller size. 

Try to optimize all image files in current working directory, with recursion, 
downsizing each of them to a maximum width of 1600 pixels:

```
optimize-images -mw 1600 ./
```

```
optimize-images --max-width 1600 ./
```


Try to optimize all image files in current working directory, without 
recursion, downsizing each of them to a maximum height of 800 pixels:

```
optimize-images -nr -mh 1600 ./
```

```
optimize-images --no-recursion --max-height 800 ./
```



### Format specific options:

The following format specific settings are optional and may be used
simultaneously, for instance when processing a directory that may
contain images in more than one format. The appropriate format-specific
options entered by the user will then be automatically selected and
applied for each image.

#### JPEG:

##### Quality

Set the quality for JPEG files (an integer value, between 1 and 100), using 
the `-q` or `--quality` argument, folowed by the quality value to apply.
A lower value will reduce both the image quality and the file size. The
default value is 80.

Try to optimize all image files in current working directory and all of its
subdirectories, applying a quality of 65% to JPEG files:

```
optimize-images -q 65 ./
```

```
optimize-images --quality 65 ./
```
  

##### Keep EXIF data

Use the `-ke` or `--keep-exif`) to keep existing image EXIF data in JPEG 
images (by default, if you don't add this argument, EXIF data is discarded).

Try to optimize all image files in current working directory and all of its
subdirectories, applying a quality of 65% to JPEG files and keeping the 
original EXIF data:

```
optimize-images -q 65 -ke ./
```

```
optimize-images --quality 65 --keep-exif ./
```


#### PNG:

##### Reduce the number of colors 

To reduce the number of colors (PNG) using an adaptive color palette with 
dithering, use the `-rc` or `--reduce-colors` optional argument.
This option can have a big impact on file size, but please note that
will also affect image quality in a very noticeable way, especially in
images that have color gradients and/or transparency.

Try to optimize a single image file in current working directory,
applying and adaptive color palette with the default amount of colors
(255):

```
optimize-images -rc ./imagefile.png
```
```
optimize-images --reduce-colors ./imagefile.png
```


##### Maximum number of colors

Use the  `-mc` or `--max-colors` optional argument to specify the maximum  
number of colors for PNG images when using the reduce colors (-rc) option 
(an integer value, between 0 and 255). The default value is 255.

Try to optimize a single image file in current working directory,
reducing the color palette to a specific value:

```
optimize-images -rc -mc 128 ./imagefile.png
```
```
optimize-images --reduce-colors --max-colors 128 ./imagefile.png
```

Try to optimize all image files in current working directory and all of
its subdirectories, applying a quality of 65% to JPEG files and
reducing the color palette of PNG files to just 64 colors:

```
optimize-images -q 60 -rc -mc 64 ./
```
```
optimize-images --quality 60 --reduce-colors --max-colors 64 ./
```


##### Automatic conversion of big PNG images to JPEG

*(work in progess)*

Automatically convert to JPEG format any big PNG images that have with a
large number of colors (presumably a photo or photo-like image). It uses
an algorithm to determine whether it is a good idea to convert to JPG
and automatically decide about it. By default, when using this option,
the original PNG files will remain untouched and will be kept alongside
the optimized JPG images in their original folders.

IMPORTANT: IF A JPEG WITH THE SAME NAME ALREADY EXISTS, IT WILL BE
REPLACED BY THE JPEG FILE RESULTING FROM THIS CONVERTION.**


```
optimize-images -cc
```

```
optimize-images --convert_big
```


You may force the deletion of the original PNG files when using
automatic convertion to JPEG, by adding the `-fd` or `--force-delete`
argument:

```
optimize-images -cc -fd
```

```
optimize-images --convert_big --force-delete
```


##### Changing the default background color

By default, when you choose some operations that remove transparency,
like reducing colors or converting from PNG to JPEG it will apply a
white background color. You may choose a different background by using
the argument `-bg` or `--background-color` folowed by 3 integer numbers,
separated by spaces, between 0 and 255, for Red, Green and Blue. E.g.:
`255 0 0` for a pure red color).


To convert a big PNG image with some transparency (like, for instance,
macOS screenshots) applying a black background:
```
optimize-images -cc -bg 0 0 0 ./image.png
```

```
optimize-images --convert_big --bg-color 0 0 0 ./image.png
```

If you prefer to use hexadecimal values, like those that are usual in
HTML code, you may alternatively use the argument `-hbg` or
`--hex-bg-color` folowed by the color code without the hash (#)
character. E.g.: `00FF00` for a pure
green color).

To convert a big PNG image with some transparency applying a pure green
background:

```
optimize-images -cc -hbg 0 255 0 ./image.png
```

```
optimize-images --convert_big --hex-bg-color 00FF00 ./image.png
```

### Other features


Check the installed version of this application:

```
optimize-images -v
```

```
optimize-images --version
```
  

View a list of the supported image formats by their usual filename extensions 
(please note that files without the corresponding file extension will be ignored):

```
optimize-images -sf
```

```
optimize-images --supported-formats
```
  
  
## Did you find a bug or do you have a suggestion?

Please let me know, by opening a new issue or a pull request.
