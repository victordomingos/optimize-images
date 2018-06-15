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

  
## Examples of usage:

Get a little help about how to use this application:

`optimize-images.py -h`  
`optimize-images.py --help`

  
Try to optimize a single image file:

`optimize-images.py filename.jpg`

  
Try to optimize all image files in current working directory and all of its
subdirectories:

`optimize-images.py ./`  

  
Try to optimize all image files in current working directory, without recursion:

`optimize-images.py ./ -nr`  
`optimize-images.py ./ --no-recursion`

  
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
