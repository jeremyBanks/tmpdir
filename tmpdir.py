#!/usr/bin/env python
"""A module and command line tool for working with temporary directories."""

import calendar
import contextlib
import os
import os.path
import random
import shlex
import shutil
import string
import subprocess
import sys
import time
import tarfile
import tempfile
import zipfile

__version_info__ = 0, 0, 0, "DEV", int(calendar.timegm(time.gmtime()))
__version__ = ".".join(str(part) for part in __version_info__)

__website__ = "https://github.com/jeremybanks/tmpdir"
__author__ = "Jeremy Banks <jeremy@jeremybanks.ca>"

__copyright__ = "Copyright 2011 Jeremy Banks <jeremy@jeremybanks.ca>"
__license__ = "MIT"
__full_license = """\
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE."""

class TmpDir(object):
    """A convenient temporary directory.
    
    The constructor has two optional arguments.
    inner_name is the basename of the temporary directory.
    secure uses the srm command on the directory once closed (slow).
           if "attempt" will not fail if insecure.
    """
    
    def __init__(self, inner_name=None, deletion=False):
        self.closed = True
        
        if deletion not in ("secure", "attempt-secure", "pseudo-secure",
                            "not-secure"):
            raise ArgumentError("Invalid deletion type.")
        
        if deletion in ("secure", "attempt-secure"):
            # confirm availability of secure remove command
            try:
                subprocess.check_call("which srm >/dev/null", shell=True)
                deletion = "secure"
            except subprocess.CalledProcessError, e:
                if deletion == "attempt-secure":
                    deletion = "pseudo-secure"
                else:
                    raise e
        
        self.deletion = deletion
        
        self.__outer_path = tempfile.mkdtemp()
        self.inner_name = inner_name or "tmp"
        
        self.path = os.path.abspath(
                        os.path.join(self.__outer_path, self.inner_name))
        os.mkdir(self.path)
        self.closed = False
    
    def close(self):
        if not self.closed:
            # move to a new path to immediately invalidate paths being deleted
            tmp_path = tempfile.mkdtemp()
            new_path = os.path.abspath(os.path.join(tmp_path, rand_name()))
            
            os.rename(self.path, new_path)
            self.closed = True
            self.path = new_path
            
            if not self.deletion:
                shutil.rmtree(tmp_path)
                shutil.rmtree(self.__outer_path)
            elif self.deletion == "pseudo-secure":
                pseudosecure_delete_directory(tmp_path)
                pseudosecure_delete_directory(self.__outer_path)
            else:
                subprocess.check_call(["srm", "-rfs", "--", tmp_path])
                subprocess.check_call(["srm", "-rfs", "--", self.__outer_path])
        
    def __del__(self):
        self.close()
    
    ##### Context Managers
    # 
    # .as_cwd() # changes CWD to path, restores previous value on exit
    # .__enter__() # .close()es/deletes directory on exit
    
    def as_cwd(self):
        """Use .path as the cwd, restoring old one on exit."""
        
        return WorkingDirectoryContextManager(self.path)
    
    def __enter__(self):
        return self
    
    def __exit__(self, xt, xv, tb):
        self.close()
    
    #### Serialization (tar)
    #
    # @classmethod .load(f, compression=None)
    # .dump(f, compression="gz")
    
    @classmethod
    def load(cls, f, compression=None, inner_name=None, deletion=None):
        """Loads a temp directory from an optionally-compressed tar file.
        
        If compression is None, it will read the first two bytes of the
        stream to look for gzip or bz2 magic numbers, then seek back. To
        disable this (if your file object doesn't support it) you can use
        the null string "" to indicate an uncompressed tar. Other args
        are "bz2" and "gz".
        """
        
        if inner_name is None and hasattr(f, "inner_name"):
            inner_name = os.path.splitext(os.path.split(f.inner_name)[0])[0]
        
        if compression is None:
            compression = sniff_archive_type(f, "tar")
        
        mode = mode="r:" + compression
        self = cls(inner_name, deletion)
        
        if compression == "zip":
            archive = zipfile.ZipFile(f, mode="r")
            archive_infos = archive.infolist()
        else:
            if compression == "tar":
                compression = ""
            
            archive = tarfile.open(fileobj=f, mode="r:" + compression)
            archive_infos = iter(archive)
        
        with self.as_cwd():
            with contextlib.closing(archive) as archive:
                for file_info in archive_infos:
                    try:
                        filename = file_info.name
                    except AttributeError:
                        filename = file_info.filename
                    
                    abs_path = os.path.abspath(os.path.join(self.path, filename))
                    
                    if os.path.commonprefix((abs_path, self.path)) != self.path:
                        raise ValueError("illegal (external) path in archive", abs_path)
                    
                    dir_, base = os.path.split(filename)
                    
                    if dir_ and not os.path.exists(dir_):
                        os.makedirs(dir_)
                    
                    if base:
                        archive.extract(file_info)
        
        return self
    
    def dump(self, f, compression=None):
        """Dumps a compressed-by-default tar of the directory to a file."""
        
        if compression is None:
            compression = sniff_archive_type(f, "gz")
        
        if compression == "zip":
            archive = zipfile.ZipFile(f, mode="w")
            archive_add = archive.write
        else:
            if compression == "tar":
                compression = ""
            
            archive = tarfile.open(fileobj=f, mode="w:" + compression)
            archive_add = archive.add
        
        with contextlib.closing(archive) as tar:
            with self.as_cwd():
                for (path, dirs, files) in os.walk("."):
                    for filename in files:
                        archive_add(os.path.join(path, filename))
                    
                    if compression != "zip":
                        for dirname in dirs:
                            archive_add(os.path.join(path, dirname))

class WorkingDirectoryContextManager(object):
    def __init__(self, path, value=None):
        self.path = path
        self.value = value
        self.previous_paths = []
    
    def __enter__(self):
        self.previous_paths.append(os.getcwd())
        os.chdir(self.path)
        return self.value
    
    def __exit__(self, xt, xv, tb):
        os.chdir(self.previous_paths.pop())

def sniff_archive_type(f, default="tar"):
    """Attempts to determine the type of an archive.
    
    Uses file extensions and magic numbers."""
    
    types_by_extension = {
        ".bz2": "bz2",
        ".tbz": "bz2",
        ".tb2": "bz2",
        ".tbz2": "bz2",
        ".zip": "zip",
        ".gzip": "gz",
        ".gz": "gz",
        ".tgz": "gz",
        ".tar": "tar"
    }
    
    if isinstance(f, (str, unicode)):
        _name = f
        class f(object): 
            name = _name
    
    if hasattr(f, "name"):
        ext = os.path.splitext(f.name)[1]
        
        if ext in types_by_extension:
            return types_by_extension[ext]
    
    if hasattr(f, "seek") and hasattr(f, "tell") and "r" in getattr(f, "mode", ""):
        start = f.tell()
        leading_two = f.read(2)
        f.seek(start)
        
        if leading_two == b"\x1F\x8B":
            return "gz"
        elif leading_two == b"BZ":
            return "bz2"
        elif leading_two == b"PK":
            return "zip"
        else:
            f.seek(257, os.SEEK_CUR)
            ustar = f.read(5)
            f.seek(start)
            
            if ustar == b"ustar":
                return "tar"
    
    return default

def rand_name(length=8, chars=string.ascii_letters + string.digits + "_"):
    return "".join(random.choice(chars) for i in range(length))

def pseudosecure_delete_directory(path):
    # zero out each file
    for (subpath, dirs, files) in os.walk(path):
        for filename in files:
            filepath = os.path.abspath(os.path.join(path, subpath, filename))
            
            bytes_to_overwrite = os.path.getsize(filepath)
            
            with open(filepath, "r+") as f:
                f.seek(0)
                
                while bytes_to_overwrite > 0:
                    n = min(bytes_to_overwrite, 1024)
                    f.write(b"\x00" * n)
                    f.flush()
                    os.fsync(f.fileno())
                    bytes_to_overwrite -= n
    
    # rename each file and directory randomly
    for (subpath, dirs, files) in os.walk(path, topdown=False):
        for filename in list(files):
            filepath = os.path.abspath(os.path.join(os.path.join(path, subpath), filename))
            randpath = os.path.abspath(os.path.join(os.path.join(path, subpath), rand_name(8) + ".tmp"))
            os.rename(filepath, randpath)
        for dirname in list(dirs):
            dirpath = os.path.abspath(os.path.join(os.path.join(path, subpath), dirname))
            randpath = os.path.abspath(os.path.join(os.path.join(path, subpath), rand_name(8)))
            os.rename(dirpath, randpath)
    
    # delete everything, bottom-up
    for (subpath, dirs, files) in os.walk(path, topdown=False):
        for filename in files:
            filepath = os.path.abspath(os.path.join(os.path.join(path, subpath), filename))
            os.remove(filepath)
        for dirname in dirs:
            dirpath = os.path.abspath(os.path.join(os.path.join(path, subpath), dirname))
            os.rmdir(dirpath)
    
    # remove the top directory itself
    shutil.rmtree(path)

def main(*raw_args):
    import argparse
    import tmpdir
    
    parser = argparse.ArgumentParser(description="""\
Creates a temporary directory, optionally loading the contents of an archive
(tar, tgz, tbz2 or zip). If run from a shell, opens a bash login shell inside
the directory. Otherwise by default I'll prompt for a newline then exit, but
any other command can be specified.

If an empty directory is created, I automatically attempt to delete it
securely. In other cases, use the args.""")
    
    parser.add_argument(dest="archive", metavar="$ARCHIVE", nargs="?",
                        help="loads an archive into the directory.")
    
    parser.add_argument("-o", "--out", dest="out",
                      action="store", type=str, metavar="$ARCHIVE",
                      help="saves directory as an archive.")
    
    command_options = parser.add_mutually_exclusive_group()
    command_options.add_argument("-c", "--command", dest="command",
                      action="store", type=str, metavar="$COMMAND",
                      help="run this command in directory instead of default")
    command_options.add_argument("-s", "--shell", dest="shell_command",
                      action="store", type=str, metavar="$COMMAND",
                      help="as --command, but run in /bin/sh/")
    
    parser.add_argument("-d", "--delete", dest="deletion", metavar="$SECURITY",
                        choices=["secure", "pseudo-secure", "attempt-secure",
                                 "not-secure"],
                        help="Specifies the deletion method/security.")
    
    # parser.add_argument("-r", "--on-error", dest="on_error", metavar="$ON_ERROR",
                        # choices=["ignore", "fail", "abort"], default="fail")
    
    parser.set_defaults(deletion=None, archive=None, out=None, command=None,
                        shell_command=None)
    args = parser.parse_args(list(raw_args))
    
    if args.command is None:
        if hasattr(sys.stdin, "isatty") and sys.stdin.isatty():
            command = ["bash", "--login"]
        else:
            command = ["read", "-p", "Press enter to delete directory..."]
    else:
        command = shlex.split(args.command)
    
    path = args.archive
    
    deletion = args.deletion
    
    if path is None:
        if deletion is None:
            deletion = "attempt-secure"
        
        sys.stderr.write("Initializing temporary directory... ")
        d = tmpdir.TmpDir(deletion=deletion)
    else:
        if deletion is None:
            deletion = "not-secure"
        
        sys.stderr.write("Loading archive to temporary directory... ")
        
        with open(path, "rb") as f:
            d = TmpDir.load(f, inner_name=os.path.basename(path), deletion=deletion)
    
    with d:
        sys.stderr.write("(deletion: %s)\n" % (d.deletion))
        sys.stderr.flush()
        
        print d.path
        
        sys.stderr.write("----" * 4 + "\n")

        if len(command) == 3 and command[:2] == ["read", "-p"]:
            sys.stderr.write(command[2])
            sys.stderr.flush()
            sys.stdin.read(1)
        else:
            env = dict(os.environ)
            env["HISTFILE"] = ""
            
            subprocess.call(command, cwd=d.path, env=env)
        
        sys.stderr.write("----"  * 4 + "\n")
        
        if args.out:
            sys.stderr.write("Archiving directory contents...\n")
            sys.stderr.flush()
            
            with open(args.out, "wb") as f:
                d.dump(f)
        
        sys.stderr.write("Deleting temporary directory... ")
        sys.stderr.write("(deletion: %s)\n" % (d.deletion))
        sys.stderr.flush()

if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
