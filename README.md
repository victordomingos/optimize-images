# Optimize Images [![Github commits (since latest release)](https://img.shields.io/github/commits-since/victordomingos/optimize-images/latest.svg)](https://github.com/victordomingos/optimize-images)
A little command-line interface (CLI) utility written in pure Python to help
you reduce the file size of images.

You must explicitly pass it a path to the source image file or to the
directory containing the image files to be processed. By default, it will go
through all of its subdirectories and try to optimize the images found. You
may however choose to process the specified directory only, without recursion.

Please note that the operation is done DESTRUCTIVELY, by replacing the
original files with the processed ones. You definitely should duplicate the
source file or folder before using this utility, in order to be able to
recover any eventual damaged files or any resulting images that don't have the
desired quality.

This application is intended to be pure Python, with no special dependencies
besides Pillow, therefore ensuring compatibility with a wide range of systems,
including iPhones and iPads running Pythonista 3. If you don't have the need
for such a strict dependency management, you will certainly be better served
by any several other image optimization utilities that are based on some well
known external binaries.

  
## Basic usage:

Get a little help about how to use this application:

`optimize-images.py -h`  
`optimize-images.py --help`


Check the installed version of this application:

`optimize-images.py -v`    
`optimize-images.py --version`
  
  
View a list of the supported image formats:

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
default value is 70.

Try to optimize all image files in current working directory and all of its
subdirectories, applying a quality of 65% to JPEG files:

`optimize-images.py -q 65 ./`  
`optimize-images.py --quality 65 ./`


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

No special instructions by now, as this is currently an experimental, early
development, version. Just make sure you are running Python 3.6+ and have
Pillow installed (we are targeting both Pillow 5.1.0 on desktop and the
built-in Pillow 2.9.0 in Pythonista for iOS).

* On desktop:
  - Pillow==5.1.0

* iOS
  - No dependencies, besides Pythonista's built-in modules.

  
## Did you find a bug or do you have a suggestion?

Please let me know, by opening a new issue or a pull request.
