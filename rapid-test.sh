#!/bin/bash
clear
rm -rf test-images
unzip test-images.zip
clear
/usr/bin/time -lp ./optimize-images.py test-images -rc
