#!/usr/bin/env python3
# encoding: utf-8
"""
A little CLI utility written in Python to apply some compression to images
using PIL

© 2018 Victor Domingos (MIT License)
"""
import os
import io
import shutil
import platform
import concurrent.futures

from argparse import ArgumentParser
from PIL import Image, ImageFile
from timeit import default_timer as timer
 

if platform.system() == 'Darwin':
    if platform.machine().startswith('iP'):
        CURRENT_PLATFORM = "iOS"
    else:
        CURRENT_PLATFORM = "macOS"
else:
    CURRENT_PLATFORM = "other"


SUPPORTED_FORMATS = ['png', 'jpg', 'jpeg', 'gif']


if CURRENT_PLATFORM == 'iOS':
    import console
    console.clear()
    console.set_font("Menlo", 10)
    TERM_WIDTH = 58
    ourPoolExecutor = concurrent.futures.ThreadPoolExecutor
    WORKERS = 2
else:
    TERM_WIDTH, _ = shutil.get_terminal_size((80, 24))
    ourPoolExecutor = concurrent.futures.ProcessPoolExecutor
    from multiprocessing import cpu_count
    WORKERS = cpu_count()

appstart = timer()
parser = ArgumentParser(description="Optimize images")

path_help = 'The path to the image file or to the folder containing the ' \
            'images to be optimized.'
parser.add_argument('path',
                    nargs="?",
                    type=str,
                    help=path_help)

parser.add_argument('-nr', "--no-recursion",
                    action='store_true',
                    help="Don't recurse through subdirectories")


def search_images(dirpath, recursive=True):
    if recursive:
        for root, dirs, files in os.walk(dirpath):
            for f in files:
                if not os.path.isfile(os.path.join(root, f)):
                    continue
                extension = os.path.splitext(f)[1][1:]
                if extension.lower() in SUPPORTED_FORMATS:
                    yield os.path.join(root, f)
    else:
        with os.scandir(dirpath) as directory:
            for f in directory:
                if not os.path.isfile(os.path.normpath(f)):
                    continue
                extension = os.path.splitext(f)[1][1:]
                if extension.lower() in SUPPORTED_FORMATS:
                    yield os.path.normpath(f)


def do_optimization(image_file):
    img_timer_start = timer()
    img = Image.open(image_file)
    img_format = img.format

    # Remove EXIF data
    data = list(img.getdata())
    no_exif_img = Image.new(img.mode, img.size)
    no_exif_img.putdata(data)

    saved_bytes = 0

    while True:
        with io.BytesIO() as file_bytes:
            try:
                no_exif_img.save(file_bytes,
                        quality=70,
                        optimize=True,
                        progressive=True,
                        format=img_format)
            except IOError:
                ImageFile.MAXBLOCK = no_exif_img.size[0] * no_exif_img.size[1]
                no_exif_img.save(file_bytes,
                        quality=70,
                        optimize=True,
                        progressive=True,
                        format=img_format)

            
            orig_size = os.path.getsize(image_file)
            final_size = file_bytes.tell()
            saved_bytes = orig_size - final_size
            
            if saved_bytes > 100:
                start_size = os.path.getsize(image_file) / 1000
                end_size = file_bytes.tell() / 1000
                saved = saved_bytes / 1000
                percent = saved / start_size * 100
                file_bytes.seek(0, 0)
                with open(image_file, 'wb') as f_output:
                    f_output.write(file_bytes.read())
                img_time = timer() - img_timer_start

                print(f'\n✅  [OPTIMIZED] {image_file[-(TERM_WIDTH-16):].ljust(TERM_WIDTH-16)}\n    {start_size:.1f}kB -> {end_size:.1f}kB (🔻{saved:.1f}kB/{percent:.1f}%, {img_time:.2f}s)', end='')
                status = 1   
            else:
                print(f'\n🔴  [SKIPPED] {image_file[-(TERM_WIDTH-15):].ljust(TERM_WIDTH-15)}', end='')
                saved_bytes = 0
                final_size = orig_size
                status = 0
            break
    return (orig_size, final_size, saved_bytes, status)


def main(*args):
    args = parser.parse_args(*args)
    src_path = os.path.expanduser(args.path)
    recursive = not args.no_recursion
    found_files = 0
    total_src_size = 0
    total_optimized = 0
    total_bytes_saved = 0

    if not src_path:
        parser.exit(status=0, message="\nPlease specifiy the path of the image or folder to process.\n\n")

    if os.path.isdir(src_path):
        if recursive:
            recursion_txt = "Recursively searching"
        else:
            recursion_txt = "Searching"

        print(f"\n{recursion_txt} and optimizing image files in:\n{args.path}\n")

        images = (i for i in search_images(src_path, recursive=recursive))
           
        if CURRENT_PLATFORM == 'iOS': 
    	    with ourPoolExecutor(max_workers=WORKERS) as executor:
                results = executor.map(do_optimization, images)
        else:
    	    with ourPoolExecutor(max_workers=WORKERS) as executor:
                results = executor.map(do_optimization, images)
        
        for r in results:     
            total_src_size += r[0]
            found_files += 1
            total_bytes_saved = r[2]
            total_optimized += r[3]
            
    elif os.path.isfile(src_path):
        total_src_size, final_size, total_bytes_saved, status = do_optimization(src_path)
        total_optimized = found_files = status
    else:
        print("No image files were found. Please enter a valid path to the " \
              "image file or the folder containing any images to be processed.")
        exit()

    
    if found_files:
        total_saved = total_bytes_saved / 1000
        time_passed = timer() - appstart
        fps = found_files / time_passed
        opt_p_sec = total_optimized / time_passed
            
        if total_bytes_saved:
            average = total_bytes_saved / total_optimized /1000
            percent = total_bytes_saved / total_src_size * 100
        else:
            average = 0
            percent = 0
            
        print(f"\n{40*'-'}\n")
        print(f"  Processed {found_files} files ({total_src_size/1000000:.1f}MB) in {time_passed:.1f}s ({fps:.1f} f/s).")
        print(f"  Optimized {total_optimized} files  ({opt_p_sec:.1f} f/s).")
        print(f"  Total space saved: {total_saved:.1f}kB ({percent:.1f}%, avg: {average:.1f}kB)")
    else:
        print("No supported image files were found in the specified directory.\n")
    

if __name__ == "__main__":
    main()
