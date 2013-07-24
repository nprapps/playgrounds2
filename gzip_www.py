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


def compress(file_path):
    f_in = open(file_path, 'rb')
    contents = f_in.readlines()
    f_in.close()
    f_out = gzip.open(file_path, 'wb')
    f_out.writelines(contents)
    f_out.close()


def main():
    in_path = sys.argv[1]
    out_path = sys.argv[2]

    with open('gzip_types.txt') as f:
        gzip_globs = [glob.strip() for glob in f]

    if os.path.isdir(in_path):
        shutil.rmtree(out_path, ignore_errors=True)
        shutil.copytree(in_path, out_path)

        for path, dirs, files in os.walk(sys.argv[2]):
            for filename in files:
                if not any([fnmatch(filename, glob) for glob in gzip_globs]):
                    continue

                file_path = os.path.join(path, filename)

                compress(file_path)
    else:
        if not any([fnmatch(in_path, glob) for glob in gzip_globs]):
            return 

        try:
            os.remove(out_path)
        except OSError:
            pass

        shutil.copy(in_path, out_path)

        compress(out_path)


if __name__ == '__main__':
    main()
