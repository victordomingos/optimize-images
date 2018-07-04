#!/bin/bash
clear
rm -rf test-images
unzip test-images.zip
clear
/usr/bin/time -lp python3 -m optimize_images test-images
