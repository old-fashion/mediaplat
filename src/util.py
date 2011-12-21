# -*- coding: utf-8 -*-
import os
import re
from config import settings

def pretty_size(size):
    size = int(size)
    suffixes = [("Byte",2**10), ("KB",2**20), ("MB",2**30), ("GB",2**40), ("TB",2**50)]
    for suf, lim in suffixes:
        if size > lim:
            continue
        else:
            return round(size/float(lim/2**10),2).__str__()+" "+suf

"""
    ex) a = [(0, " item", " items"), (12, " container", " containers")]
"""
def pretty_count(list):
    result = ""
    first = True
    for item in list:
        if item[0] > 0:
            if first:
                first = False
            else:
                result += ", "
            result += {'1': str(item[0]) + item[1]}.get(str(item[0]), str(item[0]) + item[2])
    return result

denylist = settings.get('core','deny_keyword').split(',')

def check_deny_file(str):
    for word in denylist:
        if word.startswith('^'):
            if os.path.basename(str).startswith(word[1:]):
                return True
        elif word.endswith('$'):
            if os.path.basename(str).endswith(word[:-1]):
                return True

    return False

def get_resize(width, height, max_width, max_height):
    if width == 0 or height == 0:
        return 0, 0

    ratio = float(width) / float(height)
    target_ratio = float(max_width) / float(max_height)
    if ratio >= target_ratio:
        out_width = max_width
        out_height = (float(max_width) * float(height)) / float(width)
    else:
        out_width = (float(max_height) * float(width)) / float(height)
        out_height = max_height
    return int(out_width), int(out_height)

