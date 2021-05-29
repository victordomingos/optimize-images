[English](https://github.com/victordomingos/optimize-images/blob/master/docs/docs_EN.md) | **[Portugu&ecirc;s](https://github.com/victordomingos/optimize-images/blob/master/docs/docs_PT.md)**



# Optimize Images [![Github commits (since latest release)](https://img.shields.io/github/commits-since/victordomingos/optimize-images/latest.svg)](https://github.com/victordomingos/optimize-images)
A command-line interface (CLI) utility written in pure Python to help you 
reduce the file size of images.

This application is intended to be pure Python, with no special dependencies
besides Pillow, therefore ensuring compatibility with a wide range of systems,
including iPhones and iPads running Pythonista 3. If you don't have the need
for such a strict dependency management, you will probably be better served
by any several other image optimization utilities that are based on some well
known external binaries.

Some aditional features can be added which require the presence of other 
third-party packages that are not written in pure Python, but those packages 
and the features depending on them should be treated as optional.

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
       - [Fast mode](#fast-mode)
       - [Watch directory for new files](#watch-directory-for-new-files)
       - [Maximum number of simultaneous jobs](#maximum-number-of-simultaneous-jobs)
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
   
* **[Related projects](#related-projects)**
   * [Optimize Images Docker](#optimize-images-docker)   
   * [Optimize Images X](#optimize-images-x)   


* **[Did you find a bug or do you have a suggestion?](#did-you-find-a-bug-or-do-you-have-a-suggestion)**

## Installation and dependencies:

### On regular desktop operating systems

To install and run this application, you need to have a working
Python 3.6+ installation. We try to keep the external dependencies at a minimum,
in order to keep compatibility with different platforms, including Pythonista
on iOS. At this moment, we require:

  - Pillow==8.2.0
  - piexif>=1.1.3
  - watchdog>=2.0.2

The easiest way to install it in a single step, including any dependencies, is 
by using this command:

```
pip3 install pillow watchdog optimize-images
```

If you are able to swap Pillow with the faster version 
[Pillow-SIMD](https://github.com/uploadcare/pillow-simd), you should be able
to get a considerably faster speed. For that reason, we provide, as a 
friendly courtesy, an optional shell script (`replace_pillow__macOS.sh`) to 
replace Pillow with the faster Pillow-SIMD on macOS. Please notice, however, 
that it usually requires a compilation step and it was not throughly tested 
by us, so your mileage may vary.


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
selfupdate.py -f dev
```

Then force-quit and restart Pythonista and launch StaSh again. It should now
be running in Python 3. You may now try to install this application, directly
from this git repository:

```
pip install optimize-images
```

If all goes well, it should install any dependencies, place a new `optimize_images`
package inside the `~/Documents/site-packages-3/` folder and create an
entrypoint script named `optimize-images.py` in `stash_extensions/bin`.

Currently, on Pythonista/iOS we require:

  - piexif==1.0.13

Then force-quit Pythonista and launch StaSh again. You should now be able to run this
application directly from the shell or by creating a home screen shortcut
with the required arguments to the entrypoint script
`~/Documents/stash_extensions/bin/optimize-images.py`, to optimize any
image files that you may have inside your Pythonista environment.


## Installing the most recent development version (may be unstable):

### On regular desktop operating systems

After cloning this repository, the current development version can be easily, 
by using the shell command `pip install -e`, followed by the path to the main 
project directory (the same directory that has the `setup.py` file). Alternatively,
you can create a virtual environment and use the following command (just replace 
`python3.8` with your intended python3 version)

```
python3.8 -m pip install git+https://github.com/victordomingos/optimize-images
```


### On iPhone or iPad (in Pythonista 3 for iOS)

On iOS, after folowing the required steps to install Pythonista and StaSh,
the current development version can be installed directly from this git 
repository:

```
pip install victordomingos/optimize-images
```

Then, as usual, force-quit and launch StaSh again. You should now be able to 
run this application directly from the shell or by creating a home screen shortcut
with the required arguments to the entrypoint script
`~/Documents/stash_extensions/bin/optimize-images.py`, to optimize any
image files that you may have inside your Pythonista environment.


## How to use

The most simple form of usage is to type a simple command in the shell, 
passing the path to an image or a folder containing images as an argument.
The optional `-nr` or `--no-recursion` switch argument tells the application
not to scan recursively through the subdirectories.

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

In addition to the default settings, you may downsize the images to fit a 
maximum width and/or a maximum height. This image resizing is done as the
first step in the image optimization process. 

You may also choose to keep the original EXIF data (if it exists) in the 
optimized files. Note, however, that this option is currently available only 
for JPEG files. 

In PNG files, you will achieve a more drastic file size reduction if you 
choose to reduce the number of colors using an adaptive palette. Be aware 
that by using this option image quality may be affected in a very
noticeable way.

Since version 1.3.5, Optimize Images also offers experimental support for MPO 
images, which are now treated as single picture JPEG image files (if multiple 
pictures are present in one MPO file, only the first one will be processed).


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

#### Fast mode:

Some of the operations may eventually be finished sooner by using this option.
Generally speaking, this means that the resulting files will have a slightly
bigger size, in order to save instead a few seconds on image processing. Using
this option disables dynamic JPEG quality setting.

Try to optimize all image files in current working directory, with recursion,
using fast mode:

```
optimize-images -fm ./
```

```
optimize-images --fast-mode ./
```


#### Image resizing:

These options will be applied individually to each image being processed. Any 
image that has a dimension exceeding a specified value will be downsized as 
the first optimization step. The resizing will not take effect if, after the 
whole optimization process, the resulting file size isn't any smaller than 
the original. These options are disabled by default.

These optional arguments can be used to constrain the final size of the images:

* Maximum width: `-mw`
* Maximum height: `-mh`

The image will be downsized to a maximum size that fits the specified 
width and/or height. If the user enters values to both dimensions, it will 
calculate the image proportions for each case and use the one that results in 
a smaller size. 

Try to optimize all image files in current working directory, with recursion, 
downsizing each of them to a maximum width of 1600 pixels:

```
optimize-images -mw 1600 ./
```

Try to optimize all image files in current working directory, without 
recursion, downsizing each of them to a maximum height of 800 pixels:

```
optimize-images -nr -mh 800 ./
```


#### Watch directory for new files:

Use this option when you have a folder which you would like to monitor for new 
image files and process them as soon as possible. Optimize Images will watch the 
specified directory continuously and will optimize automatically any newly 
created file. File paths are saved in a temporary list in memory, so that each 
file should just be processed once per session.

Files that exist when Optimized Images is started using this 
option will generally not be processed, but you can force it, by issuing two
consecutive shell commands, first doing a regular pass without the `-wd` 
argument to process existing files, then a second call with the `-wd` argument 
to keep the utility watching for new files and process them as they are created.

```
optimize-images -wd ./
```

```
optimize-images --watch-directory ./
```

This feature requires the optional third-party `watchdog` package and its 
dependencies, and is only available on operating systems supported by it. It is
not available, for instance, on iOS.

At this time, multiprocessing is not available when using this feature.


#### Maximum number of simultaneous jobs

You can specify the maximum number of simultaneous jobs that should be alowed 
to run at a given time. The default value (0), for most platforms, will 
generate a total of N + 1 processes, where N is the number of CPUs or cores in 
the system.

```
optimize-images -jobs 16 ./
```


### Format specific options:

The following format specific settings are optional and may be used
simultaneously, for instance when processing a directory that may
contain images in more than one format. The appropriate format-specific
options entered by the user will then be automatically selected and
applied for each image.

#### JPEG:

##### Quality

Set a fixed value for the quality for JPEG files (an integer value, between 1
and 100), using the `-q` argument, folowed by the quality value to apply. A
lower value will reduce both the image quality and the file size. Using this
option disables the default dynamically variable JPEG quality setting.

Try to optimize all image files in current working directory and all of its
subdirectories, applying a quality of 65% to JPEG files:

```
optimize-images -q 65 ./
```


##### Keep EXIF data

Use the `-ke` or `--keep-exif` option to keep existing EXIF data in JPEG 
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
dithering, use the `-rc` optional argument.
This option can have a big impact on file size, but please note that
will also affect image quality in a very noticeable way, especially in
images that have color gradients and/or transparency.

Try to optimize a single image file in current working directory,
applying and adaptive color palette with the default amount of colors
(255):

```
optimize-images -rc ./imagefile.png
```

##### Maximum number of colors

Use the  `-mc` optional argument to specify the maximum
number of colors for PNG images when using the reduce colors (-rc) option 
(an integer value, between 0 and 255). The default value is 255.

Try to optimize a single image file in current working directory,
reducing the color palette to a specific value:

```
optimize-images -rc -mc 128 ./imagefile.png
```

Try to optimize all image files in current working directory and all of
its subdirectories, applying a quality of 65% to JPEG files and
reducing the color palette of PNG files to just 64 colors:

```
optimize-images -q 60 -rc -mc 64 ./
```

Please note that indicating a very small number of colors may remove transparency,
replacing it with unintended colors. In such cases, you will probably achieve
better results by combining this option with explicit transparency removal 
(`rt`) and background color replacement (`-bg` or `hbg`).

For instance, to optimize a single PNG image file, reducing the color palette
to 8 colors maximum, removing transparency and applying a white background:

```
optimize-images -rc -mc 8 -rt -hbg ffffff ./imagefile.png
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
optimize-images -cb
```

```
optimize-images --convert_big
```


You may force the deletion of the original PNG files when using
automatic conversion to JPEG, by adding the `-fd` or `--force-delete`
argument:

```
optimize-images -cb -fd
```

```
optimize-images --convert_big --force-delete
```


##### Changing the default background color

By default, when removing transparency or converting from PNG to JPEG it
will apply a white background color. You may choose a different
background by using the argument `-bg` followed by 3 integer numbers,
separated by spaces, between 0 and 255, for Red, Green and Blue. E.g.:
`255 0 0` for a pure red color).


To convert a big PNG image with some transparency (like, for instance,
macOS screenshots) applying a black background:
```
optimize-images -cb -bg 0 0 0 ./image.png
```

If you prefer to use hexadecimal values, like those that are usual in
HTML code, you may alternatively use the argument `-hbg` followed by the
color code without the hash (#) character. E.g.: `00FF00` for a pure
green color).

To convert a big PNG image with some transparency applying a pure green
background:
```
optimize-images -cb -hbg 00FF00 ./image.png
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
optimize-images -s
```

```
optimize-images --supported
```


### Related projects

#### [Optimize Images Docker](https://github.com/varnav/optimize-images-docker)
A third-party dockerized implementation of Optimize Images. It includes a few  interesting optimizations, like the usage of a recent version of [mozjpeg](https://github.com/mozilla/mozjpeg) library, or a Pillow binary compiled with [libimagequant](https://github.com/ImageOptim/libimagequant), which should result in faster and more efficient compression.

#### [Optimize Images X](https://github.com/victordomingos/optimize-images-x)
A desktop app written in Python, that exposes and unlocks the full power of Optimize Images in a nice graphical user interface, to help you reduce the file size of images. Just like its CLI companion app, it can process a single file, a folder’s root or all images in a folder, recursively. Multiple image processing tasks are automatically distributed to all available CPU cores. Additionally, it includes a “watch folder” feature that continuously monitors a specified folder for new image files and processes them right after they’re created or placed in that folder.

  
## Did you find a bug or do you have a suggestion?

Please let me know, by opening a new issue or a pull request.
