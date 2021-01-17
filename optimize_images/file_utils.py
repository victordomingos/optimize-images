# encoding: utf-8
import os
from typing import Iterable

from optimize_images.constants import SUPPORTED_FORMATS


def search_images(dirpath: str, recursive: bool) -> Iterable[str]:
    if recursive:
        for root, _, files in os.walk(dirpath):
            for filename in files:
                if not os.path.isfile(os.path.join(root, filename)):
                    continue
                extension = os.path.splitext(filename)[1][1:]
                if extension.lower() in SUPPORTED_FORMATS:
                    yield os.path.join(root, filename)
    else:
        with os.scandir(dirpath) as directory:
            for dir_entry in directory:
                if not os.path.isfile(os.path.normpath(dir_entry)):
                    continue
                extension = os.path.splitext(dir_entry)[1][1:]
                if extension.lower() in SUPPORTED_FORMATS:
                    yield os.path.normpath(dir_entry)
