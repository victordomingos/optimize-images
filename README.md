# Optimize Images [![Github commits (since latest release)](https://img.shields.io/github/commits-since/victordomingos/optimize-images/latest.svg)](https://github.com/victordomingos/optimize-images)
A little command-line interface (CLI) utility written in pure Python to help
you reduce the file size of images.

This application is intended to be pure Python, with no special dependencies
besides Pillow, therefore ensuring compatibility with a wide range of systems,
including iPhones and iPads running Pythonista 3. If you don't have the need
for such a strict dependency management, you will certainly be better served
by any several other image optimization utilities that are based on some well
known external binaries.


## Default behavior 
By default, this utility applies lossy compression to JPEG files using a quality setting of 75% (by Pillow's scale), removes any EXIF metadata, tries to optimize each encoder's settings for maximum space reduction and applies the maximum ZLIB compression on PNG. 

You must explicitly pass it a path to the source image file or to the
directory containing the image files to be processed. By default, it will scan recursively through all subfolders and process any images found using the default or user-provided settings, replacing each original file by its processed version if its file size is smaller than the original.

If no space savings were achieved for a given file, the original version will be kept instead.

## Options
In addition to the default settings, you may downsize the images to fit a maximum width and/or a maximum height. This image resizing is done as the first step in the image optimization process. 

You may also choose to keep the original EXIF data (if it exists) in the optimized files. Note, however, that this option is currently available only for JPEG files. 

In PNG files, you will achieve a more drastic file size reduction if you choose to reduce the number of colors using an adaptive palette. Be aware that by using this option all PNG images will loose transparency and image quality may be affected in a very noticeable way.

There is also an option to process only the specified directory, without recursion.
  

## DISCLAIMER
**Please note that the operation is done DESTRUCTIVELY, by replacing the
original files with the processed ones. You definitely should duplicate the
source file or folder before using this utility, in order to be able to
recover any eventual damaged files or any resulting images that don't have the
desired quality.**
  
  
## Basic usage:

Get a little help about how to use this application:

`optimize-images.py -h`  
`optimize-images.py --help`


Check the installed version of this application:

`optimize-images.py -v`    
`optimize-images.py --version`
  

View a list of the supported image formats by their usual filename extensions (please note that files without the corresponding file extension will be ignored):

`optimize-images.py -sf`    
`optimize-images.py --supported-formats`
  
  
Try to optimize a single image file:

`optimize-images.py filename.jpg`

  
Try to optimize all image files in current working directory and all of its
subdirectories:

`optimize-images.py ./`


Try to optimize all image files in current working directory, without recursion:

`optimize-images.py -nr ./`  
`optimize-images.py --no-recursion ./`


## Format independent options:

### Image resizing:

These options will be applied individually to each image being processed. Any 
image that has a dimension exceeding a specified value will be downsized as 
the first optimization step. The resizing will not take effect if, after the 
whole optimization process, the resulting file size isn't any smaller than 
the original. These options are disabled by default.

#### Maximum width (-mw or --max-width)
#### Maximum height (-mh ou --max-height)


Try to optimize all image files in current working directory, with recursion, downsizing each of them to a maximum width of 1600 pixels:

`optimize-images.py -mw 1600 ./`  
`optimize-images.py --max-width 1600 ./`


Try to optimize all image files in current working directory, without recursion, downsizing each of them to a maximum height of 800 pixels:

`optimize-images.py -nr -mh 1600 ./`  
`optimize-images.py --no-recursion --max-height 800 ./`



## Format specific options:

The following format specific settings are optional and may be used
simultaneously, for instance when processing a directory that may
contain images in more than one format. The appropriate format-specific
options entered by the user will then be automatically selected and
applied for each image.

### JPEG:

#### Quality (-q or --quality)

Set the quality for JPEG files (an integer value, between 1 and 100).
A lower value will reduce both the image quality and the file size. The
default value is 75.

Try to optimize all image files in current working directory and all of its
subdirectories, applying a quality of 65% to JPEG files:

`optimize-images.py -q 65 ./`  
`optimize-images.py --quality 65 ./`
  

#### Keep EXIF data (-ke or --keep-exif)

Keep existing image EXIF data in JPEG images (by default, EXIF data is discarded).

Try to optimize all image files in current working directory and all of its
subdirectories, applying a quality of 65% to JPEG files and keeping the original EXIF data:

`optimize-images.py -q 65 -ke ./`  
`optimize-images.py --quality 65 --keep-exif ./`


### PNG:

#### Reduce colors (-rc or --reduce-colors)

Reduce colors (PNG) using an adaptive color palette with dithering.
This option can have a big impact on file size, but please note that
will also affect image quality in a very noticeable way, especially in
images that have color gradients and/or transparency.

Try to optimize a single image file in current working directory,
applying and adaptive color palette with the default amount of colors
(256):

`optimize-images.py -rc ./imagefile.png`  
`optimize-images.py --reduce-colors ./imagefile.png`


#### Maximum number of colors (-mc or --max-colors)

Use this option to specify the maximum number of colors for PNG
images when using the reduce colors (-rc) option (an integer value,
between 1 and 256). The default value is 256.

Try to optimize a single image file in current working directory,
reducing the color palette to a specific value:

`optimize-images.py -rc -mc 128 ./imagefile.png`  
`optimize-images.py --reduce-colors --max-colors 128 ./imagefile.png`

Try to optimize all image files in current working directory and all of
its subdirectories, applying a quality of 65% to JPEG files and
reducing the color palette of PNG files to just 64 colors:

`optimize-images.py -q 60 -rc -mc 64 ./`  
`optimize-images.py --quality 60 --reduce-colors --max-colors 64 ./`


## Installation and dependencies:

The `optimize-images.py` script should be placed in some folder included in your shell path, and should have executable permissions.

Please make sure that you are running Python 3.6+ and have the following packages installed (we are targeting both Pillow 5.1.0 on desktop and the
built-in Pillow 2.9.0 in Pythonista for iOS):

* On desktop:
  - Pillow==5.1.0
  - piexif==1.0.13

* iOS
  - piexif==1.0.13

  
## Did you find a bug or do you have a suggestion?

Please let me know, by opening a new issue or a pull request.
