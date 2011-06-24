#!/usr/bin/env python2.6
import setuptools 
import os.path
import tmpdir

name = "tmpdir"
version = tmpdir.__version__

url = tmpdir.__website__
pypi_url = "http://pypi.python.org/pypi/" + name
pypi_versioned_url = "http://pypi.python.org/pypi/" + name + "/" + version

description = tmpdir.__doc__.partition("\n")[0]

try:
    long_description = open(os.path.join(os.path.dirname(__file__), "README.md")).read()
except Exception:
    long_description = tmpdir.__doc__

setuptools.setup(
    name = name,
    version = version,
    
    install_requires=["argparse>1.1, <2"],
    
    url = url,
    download_url = pypi_versioned_url,
    
    description = description,
    long_description = long_description,
    
    py_modules = ["tmpdir"],
    
    data_files=[("", ["README.md"])],
    
    entry_points = {
        "console_scripts": [
            "tmpdir = tmpdir:main"
        ],
    },
    
    classifiers = [
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "License :: OSI Approved :: MIT License",
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "Environment :: Console",
        "Topic :: Utilities"
    ],
    
    author = "Jeremy Banks",
    author_email = "jeremy@jeremybanks.ca"
)
