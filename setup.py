#!/usr/bin/env python2.6
import setuptools 
import datetime
import os.path

name = "tmpdir"
version = datetime.datetime.utcnow().strftime("0.0.dev-%Y-%m-%dT%H%MZ")

pypi_download_url = "http://pypi.python.org/pypi/" + name + "/" + version

setuptools.setup(
    name = name,
    version = version,
    
    url = "http://pypi.python.org/pypi/" + name,
    download_url = pypi_download_url,
    
    description = "A module and command-line tool for working with temporary directories.",
    
    py_modules = ["tmpdir"],
    
    entry_points = {
        "console_scripts": [
            "tmpdir = tmpdir:main"
        ],
    },
    
    classifiers = [
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.6",
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
