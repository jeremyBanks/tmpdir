#!/usr/bin/env python2.6
import contextlib
import tempfile
import shutil
import tarfile
import os
import os.path
try: from cStringIO import StringIO
except:
    try: from StringIO import StringIO
    except: from io import StringIO

class TempDir(object):
    """A temporary directory.
    
    - Absolute path is in .path.
    - Deleted when .close()d or __exit__()ed.
    - Iterate to os.walk (path, subdirectories, files).
    - Enter or enter .as_cwd() to use as CWD.
    - TempDir.from_tar(instance.tar()) # bz2 by default
    - Picklable (though .path changes).
    - You can .open() a file inside it.
    """
    
    def __init__(self):
        self.path = tempfile.mkdtemp()
        self.closed = False
    
    def close(self):
        if not self.closed:
            shutil.rmtree(self.path)
            self.closed = True
    
    def __del__(self):
        self.close()
    
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
        return os.walk(self.path)
    
    @contextlib.contextmanager
    def as_cwd(self):
        """Use .path as cwd."""
        
        owd = os.getcwd()
        os.chdir(self.path)
        yield self
        os.chdir(owd)
    
    @contextlib.contextmanager
    def __enter__(self):
        """Use .path as CWD, close when leaving."""
        
        owd = os.getcwd()
        os.chdir(self.path)
        yield self
        os.chdir(owd)
        self.close()
    
    @classmethod
    def from_tar(cls, f, compression=None, ):
        """Loads a temp directory from an optionally-compressed tar file.
        
        A filename may be used instead of a file object."""
        
        if isinstance(f, (str, unicode)):
            f = open(f, "rb")
            closing_f = True
        else:
            closing_f = False
        
        try:
            if compression is None:
                magic_number = f.read(2)
                f.seek(-2, os.SEEK_CUR)
            
                if magic_number == b"\x1F\x8B":
                    compression = "gz"
                elif magic_number == b"BZ":
                    compression = "bz2"
            
            mode = mode="r:{0}".format(compression or "")
            self = cls()
            
            with self.as_cwd:
                with tarfile.open(fileobj=f, mode=mode) as tar:
                    # for each file: extract!
                    after checking that 
                    os.path.abspath(os.path.realpath())
                    can be split() repeatedly to end up with
                    os.path.abspath(os.getcwd())
        finally:
            if closing_f:
                f.close()
        
        return self
    
    def tar(self, compression="bz2"):
        """Returns a named temp file of this directory, tarred."""
        
        with self:
            return a named temp file containing a compressed-by-default
            tar archive of this folder.
    
    def __reduce__(self):
        """Pickle as a tar in a StringIO()."""
        
        tar_in_memory = StingIO()
        tarred = self.tar()
        
        while True:
            data = tarred.read(4096)
            if data:
                tar_in_memory.write(data)
            else:
                break
        
        return (type(self).from_tar, (tar_in_memory,))
