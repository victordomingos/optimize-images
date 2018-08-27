# Optimize Images [![Github commits (since latest release)](https://img.shields.io/github/commits-since/victordomingos/optimize-images/latest.svg)](https://github.com/victordomingos/optimize-images)
A command-line interface (CLI) utility written in pure Python to help you 
reduce the file size of images.

This application is intended to be pure Python, with no special dependencies
besides Pillow, therefore ensuring compatibility with a wide range of systems,
including iPhones and iPads running Pythonista 3. If you don't have the need
for such a strict dependency management, you will probably be better served
by any several other image optimization utilities that are based on some well
known external binaries.

![optimize-images_screenshot](https://user-images.githubusercontent.com/18650184/42172232-5788c43a-7e13-11e8-8094-5811e7fd55c1.png)


## Installation and dependencies:

### On regular desktop operating systems

To install and run this application, you need to have a working
Python 3.6+ installation. We try to keep the external dependencies at a minimum,
in order to keep compatibility with different platforms, including Pythonista
on iOS. At this moment, we require:

  - Pillow>=5.1.0
  - piexif==1.0.13

The easiest way to install it in a single step, including any dependencies, is 
by using this command:

```
pip3 install pillow optimize-images
```

However, if you are on a Mac with Python 3.6 and macOS X 10.11 El Capitan or
earlier, you should use Pillow 5.0.0 instead (use instead: 
`pip3 install pillow==5.0.0 optimize-images`). In case you have already
migrated to Python 3.7, you should be fine with Pillow 5.1.0 or later.


### On iPhone or iPad (in Pythonista 3 for iOS)

First you will need a Python environment and a command-line shell compatible
with Python 3. Presently, it means you need to have an app called
[Pythonista 3](http://omz-software.com/pythonista/) (which is, among other
things, a very nice environment for developing and/or running pure Python
applications on iOS).

Then you need to install [StaSh](https://github.com/ywangd/stash), which is a 
Python-based shell application for Pythonista. It will enable you to use 
useful commands like `wget`, `git clone`, `pip install` and many others. It 
really deserves an home screen shortcut on your iPhone or iPad.

After following the instructions for StaSh installation, you may need to 
update it to a more recent version. Try this command:

```
selfupdate.py -f bennr01:command_testing
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

Then force-quit and launch StaSh again. You should now be able to run this
application directly from the shell or by creating a home screen shortcut
with the required arguments to the entrypoint script
`~/Documents/stash_extensions/bin/optimize-images.py`, to optimize any
image files that you may have inside your Pythonista environment.


## Documentation
 * [English](https://github.com/victordomingos/optimize-images/blob/master/README.md)
 * [Portugu&ecirc;s](https://github.com/victordomingos/optimize-images/blob/master/README_PT.md)


## How to use

The most simple form of usage is to type a simple command in the shell, 
passing the path to an image or a folder containing images as an argument.
The optional `-nr` or `--no-recursion` switch argument tells the application not 
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
that by using this option image quality may be affected in a very
noticeable way.


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
  
  
## Did you find a bug or do you have a suggestion?

Please let me know, by opening a new issue or a pull request.
