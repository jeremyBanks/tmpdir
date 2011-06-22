#!/usr/bin/env python2.6
import setuptools 
import datetime
import os.path

# timestamped 0.0.dev versions
version = datetime.datetime.utcnow().strftime("0.0.dev-%Y-%m-%dT%H%MZ")

name = "tmpdir"

url = "https://github.com/jeremybanks/tmpdir"
pypi_url = "http://pypi.python.org/pypi/" + name
pypi_versioned_url = "http://pypi.python.org/pypi/" + name + "/" + version

setuptools.setup(
    name = name,
    version = version,
    
    url = url,
    download_url = pypi_versioned_url,
    
    description = "A module and command-line tool for working with temporary directories.",
    long_description = open(os.path.join(os.path.dirname(__file__), "README.md")).read(),
    
    py_modules = ["tmpdir"],
    
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
