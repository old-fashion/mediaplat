# -*- coding: utf-8 -*-

import os, time, datetime
from psycopg2 import *
import subprocess
import unittest
import tempfile, random, difflib, shutil, string

from content import *

""" Move to util module """

def pretty_size(size):
    size = int(size)
    suffixes = [("B",2**10), ("K",2**20), ("M",2**30), ("G",2**40), ("T",2**50)]
    for suf, lim in suffixes:
        if size > lim:
            continue
        else:
            return round(size/float(lim/2**10),2).__str__()+suf

def random_str(length):
    return ''.join(random.choice(string.letters) for i in xrange(length))

def _make_random_tree(dir, count, curcount, maxcount, curdepth, maxdepth):
    dir_count = random.randrange(1, max(count, 2))
    file_count = count - dir_count

    for i in range(dir_count):
        name = os.path.join(dir, "%07d_" % curcount + random_str(8))
        os.mkdir(name)
        curcount += 1
        if curcount > maxcount:
            raise Exception
    for i in range(file_count):
        name = os.path.join(dir, "%07d_" % curcount + random_str(8))
        file = open(name, 'w')
        file.write("hi")
        file.close()
        curcount += 1
        if curcount > maxcount:
            raise Exception

    if curdepth >= maxdepth:
        return
    for d in os.listdir(dir):
        if not os.path.isdir(os.path.join(dir, d)):
            continue
        _make_random_tree(os.path.join(dir, d), 
                               max(2, random.randrange(1, max(2, count / 2))), 
                               curcount + 1, maxcount, curdepth + 1, maxdepth)

def make_random_tree(topdir, count=100, depth=5):
    if count < depth * 2:
        count = depth * 2

    onelevel_count = count / depth
    _make_random_tree(topdir, onelevel_count, 0, count, 1, depth)
    return topdir

""" Move to util module """

class TestContent(unittest.TestCase):
    def setUp(self):
        self.content = Content("test")
        self.devnull = open(os.devnull, 'w')

    def tearDown(self):
        self.content = None
        self.devnull.close()

    def test_001_buildup(self):
        self.content.buildup()

    def test_002_browse_metadata(self):
        self.content.browse_metadata()
        self.assertEqual(None, self.content.browse_metadata("xxxxx"))
        self.assertEqual(None, self.content.browse_metadata(12345))

    def test_003_browse_children(self):
        self.content.browse_children()
        self.assertEqual([], self.content.browse_children("xxxxx"))
        self.assertEqual(None, self.content.browse_children(12345))

    def test_004_tree(self):
        self.content.tree(mode="compare")

    #@unittest.skip("HI")
    def test_005_scan_and_compare(self):
        topdir = tempfile.mkdtemp()
        try:
            make_random_tree(topdir)
        except:
            pass
        self.content.scan(topdir)
        my_result = self.content.tree(str(os.stat(topdir).st_ino), mode="compare")
        your_result = ""
        try:
            command = "tree -n --inodes --dirsfirst " + topdir
            args = command.split(' ')
            your_result = subprocess.check_output(args, stderr=self.devnull)
        except subprocess.CalledProcessError:
            pass

        shutil.rmtree(topdir)

        if my_result != your_result:
            diff = difflib.ndiff(my_result.splitlines(), your_result.splitlines())
            print "Diff ----------------------------------------------"
            print '\n'.join(list(diff))
            self.assertEqual("DB's tree", "Filesystem's tree")

    def test_006_fullpath(self):
        self.content.buildup()
        topdir = tempfile.mkdtemp()
        try:
            make_random_tree(topdir, 2000, 1000)
        except:
            pass
        self.content.scan(topdir)
        node = self.content.last()

        starttime = time.time()
        path = self.content.fullpath(node['uid'])
        elapsed = time.time() - starttime
        if elapsed > 1.0:
           self.assertEqual(str(elpased), "Time Limit : 1.00 Sec")

        self.content.fullpath("xxxxx")

    def test_007_search_keyword(self):
        self.content.STOPWATCH = True
        self.content.search_keyword(Content.ROOT, "Audio")
        self.content.STOPWATCH = False


if __name__ == '__main__':
    unittest.main()
