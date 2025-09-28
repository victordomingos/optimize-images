#!/bin/bash
clear
rm -rf test-images
unzip 1.jpeg-photos.zip
unzip 2.pelican_output.zip
unzip 3.by-type.zip
unzip 4.test-PNG.zip
clear
/usr/bin/time -lp python3 -m optimize_images test-images $@
