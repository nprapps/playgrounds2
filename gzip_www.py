#!/usr/bin/env python

from fnmatch import fnmatch
import gzip
import os
import shutil
import sys

class FakeTime:
    def time(self):
        return 1261130520.0

# Hack to override gzip's time implementation
# See: http://stackoverflow.com/questions/264224/setting-the-gzip-timestamp-from-python
gzip.time = FakeTime()

def main():
    with open('gzip_types.txt') as f:
        gzip_globs = [glob.strip() for glob in f]

    shutil.rmtree(sys.argv[2], ignore_errors=True)
    shutil.copytree(sys.argv[1], sys.argv[2])

    for path, dirs, files in os.walk(sys.argv[2]):
        for filename in files:
            if not any([fnmatch(filename, glob) for glob in gzip_globs]):
                continue

            file_path = os.path.join(path, filename)
            
            f_in = open(file_path, 'rb')
            contents = f_in.readlines()
            f_in.close()
            f_out = gzip.open(file_path, 'wb')
            f_out.writelines(contents)
            f_out.close();

if __name__ == '__main__':
    main()
