#!/usr/bin/env python2.6
import contextlib
import tempfile
import shutil
import tarfile
import os
import os.path
import sys
import subprocess

class TmpDir(object):
    """A convenient temporary directory.
    
    The constructor has two optional arguments.
    inner_name is the basename of the temporary directory.
    secure uses the srm command on the directory once closed (slow).
           if "attempt" will not fail if insecure.
    """
    
    def __init__(self, inner_name=None, secure=False):
        self.closed = True
        
        if secure:
            # confirm availability of secure remove command
            try:
                subprocess.check_call("which srm >/dev/null", shell=True)
                secure = True
            except subprocess.CalledProcessError, e:    
                if secure != "attempt":
                    raise e
                secure = False
                    
        self.secure = secure
        
        self.__outer_path = tempfile.mkdtemp("", "")
        self.inner_name = inner_name or "tmp"
        
        self.path = os.path.abspath(
                        os.path.join(self.__outer_path, self.inner_name))
        os.mkdir(self.path)
        self.closed = False
    
    def close(self):
        if not self.closed:
            # move to a new path to immediately invalidate paths being deleted
            tmp_path = tempfile.mkdtemp()
            
            os.rename(self.__outer_path, tmp_path)
            if not self.secure:
                shutil.rmtree(tmp_path)
            else:
                subprocess.check_call(["srm", "-rfs", "--", tmp_path])
            self.closed = True
    
    def __del__(self):
        self.close()
    
    ##### Content Shortcuts
    # 
    # .open(path, ...) # an open() relative to this directory + $(mkdir -p)
    # .__iter__() # os.walk()s contents by (path, subdirectories, files).
    
    def open(self, path, *a, **kw):
        """Opens a file in the directory.
        
        Intermediary folders are automatically created for nonexistent files.
        """
        
        path = os.path.join(self.path, path)
        dir_path = os.path.dirname(path)
        
        if not os.path.isdir(dir_path):
            os.makedirs(dir_path)
        
        return open(path, *a, **kw)
    
    def __iter__(self):
        """os.walk() the directory tree's (path, subdirectories, files)."""
        
        return os.walk(self.path)
    
    ##### Context Managers
    # 
    # .as_cwd() # changes CWD to path, restores previous value on exit
    # .__enter__() # .close()es/deletes folder on exit
    
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
    # .dump(f, compression="bz2")
    
    @classmethod
    def load(cls, f, compression=None, inner_name=None, secure=None):
        """Loads a temp directory from an optionally-compressed tar file.
        
        If compression is None, it will read the first two bytes of the
        stream to look for gzip or bz2 magic numbers, then seek back. To
        disable this (if your file object doesn't support it) you can use
        the null string "" to indicate an uncompressed tar. Other options
        are "bz2" and "gz".
        """
        
        if inner_name is None and hasattr(f, "inner_name"):
            inner_name = os.path.splitext(os.path.split(f.inner_name)[0])[0]
        
        if compression is None:
            magic_number = f.read(2)
            f.seek(-2, os.SEEK_CUR)
        
            if magic_number == b"\x1F\x8B":
                compression = "gz"
            elif magic_number == b"BZ":
                compression = "bz2"
            else:
                compression = ""
        elif compression not in ("", "bz2", "gz"):
            raise ValueError("Unknown compression type", compression)
        
        mode = mode="r:" + compression
        self = cls(inner_name, secure)
        
        with self.as_cwd():
            with contextlib.closing(tarfile.open(fileobj=f, mode=mode)) as tar:
                for file_info in tar:
                    abs_path = os.path.abspath(os.path.join(self.path, file_info.name))
                    
                    if os.path.commonprefix((abs_path, self.path)) != self.path:
                        raise ValueError("illegal (external) path in tar", abs_path)
                    
                    tar.extract(file_info, path="")
        
        return self
    
    def dump(self, f, compression=None):
        """Dumps a compressed-by-default tar of the directory to a file."""
        
        if compression is None:
            compression = "bz2"
        elif compression not in ("", "bz2", "gz"):    
            raise ValueError("Unknown compression type", compression)
        
        with self.as_cwd():
            with contextlib.closing(tarfile.open(fileobj=f, mode="w:" + compression)) as tar:
                for (path, dirs, files) in self:
                    if os.path.abspath(path) == self.path:
                        for filename in files:
                            tar.add(filename)
                        for dirname in dirs:
                            tar.add(dirname)
                        break

load = TmpDir.load

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

def main(raw_args=None):
    import optparse
    import tmpdir
    
    parser = optparse.OptionParser(usage="Usage: %prog [options] [archive]")
    
    parser.add_option("-s", "--secure", dest="secure",
                      action="store_const", const=True)
    parser.add_option("-t", "--attempt-secure", dest="secure",
                      action="store_const", const="attempt")
    parser.add_option("-n", "--not-secure", dest="secure",
                      action="store_const", const=False)
    parser.add_option("-o", "--out", dest="out",
                      action="store", type="string", metavar="archive")
    parser.set_defaults(secure=None, out=None)
    options, args = parser.parse_args(raw_args)
    
    if len(args) > 1:
        raise ArgumenError("Too many arguments.")
    elif args:
        path = args[0]
    else:
        path = None
    
    secure = options.secure
    
    if path is None:
        if secure is None:
            secure = "attempt"
        
        d = tmpdir.TmpDir(secure=secure)
    else:
        if secure is None:
            secure = False
        
        with open(path, "rb") as f:
            d = TmpDir.load(f, secure=secure)
    
    with d:
        print d.path
        
        if (hasattr(sys.stdin, "isatty") and sys.stdin.isatty()
            and subprocess.call("which bash >/dev/null", shell=True) == 0):
            sys.stdout.write("Close shell to remove folder...\n")
            subprocess.call(["bash", "--login"], cwd=d.path, env={"HISTFILE": ""})
        else:
            try:
                subprocess.call(("open", d.path))
            except OSError:
                try:
                    subprocess.call(("start", d.path), shell=True)
                except OSError:
                    subprocess.call(("xdg-open", d.path))
            
            raw_input("Press enter to remove folder...")
        
        if options.out:
            with open(options.out, "wb") as f:
                d.dump(f)

if __name__ == "__main__":
    sys.exit(main())
