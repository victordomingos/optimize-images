#!/bin/bash
clear
rm -rf test-images
unzip 1.jpeg-photos.zip
unzip 2.pelican_output.zip
unzip 3.by-type.zip
clear
/usr/bin/time -lp python3 -m optimize_images test-images/1.jpeg-photos -mw 1600 -q 85
/usr/bin/time -lp python3 -m optimize_images test-images/2.pelican_output --insane
/usr/bin/time -lp python3 -m optimize_images test-images/3.by-type/JPEG/big -mw 1600 -mh 800 -ke
/usr/bin/time -lp python3 -m optimize_images test-images/3.by-type/JPEG/small -mh 80 -q 60
/usr/bin/time -lp python3 -m optimize_images "test-images/3.by-type/PNG/big rgb" -cb -hbg ccffcc -ins
/usr/bin/time -lp python3 -m optimize_images "test-images/3.by-type/PNG/big rgb with transparency" -mw 1600 -bg 0 0 255 -rc -mc 64 -ins
/usr/bin/time -lp python3 -m optimize_images "test-images/3.by-type/PNG/console_screenshot_imgoptim.png" -ins
/usr/bin/time -lp python3 -m optimize_images "test-images/3.by-type/PNG/console_screenshot.png" -ins
