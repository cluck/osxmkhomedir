#!/usr/bin/env python
# -*- Mode: Python; py-indent-offset: 4; coding: utf-8 -*-
# vim: tabstop=4 shiftwidth=4 expandtab

## Copyright (c) 2015, Claudio Luck (Zurich, Switzerland)
##
## Licensed under the terms of the MIT License, see LICENSE file.

from __future__ import print_function

import os
import sys
import codecs
import re

try:
    from setuptools import setup, Command
except ImportError:
    if __name__ == "__main__":
        print("setuptools missing: run `make prepare' first\n")
    raise

#PACKAGE_DIR={
#    'osxmkhomedir': '.',
#}
PACKAGES = ['osxmkhomedir']

with codecs.open(os.path.join('.', 'osxmkhomedir', 'commands.py')) as init:
    METADATA = dict(re.findall("__([A-Za-z][A-Za-z0-9_]+)__\s*=\s*'([^']+)'", init.read().decode('utf-8')))

if sys.version_info < (3, ):
    extra = {}
else:
    extra = {
        'use_2to3': False,
        'convert_2to3_doctests': ['README.rst'],
    }

if os.path.exists("README.rst"):
    long_description = codecs.open("README.rst", "r", "utf-8").read()
else:
    long_description = "See https://github.com/cluck/osxmkhomedir"

# TODO: make exclude get-pip.py
setup(
    name = 'osxmkhomedir',
    packages=PACKAGES,
    version=METADATA['version'],
    description = 'OS X mkhomedir',
    long_description = long_description,
    url = 'https://github.com/cluck/osxmkhomedir',
    #zip_safe=False,
    author = METADATA['author'],
    author_email = METADATA['author_email'],
    maintainer = 'Claudio Luck',
    maintainer_email = 'claudio.luck@gmail.com',
    license = 'MIT',
    #include_package_data=True,
    platforms=["any"],
    #package_dir=PACKAGE_DIR,
    requires=['argparse', 'AppKit'],
    entry_points={
        'console_scripts': [
            'osxmkhomedir = osxmkhomedir.commands:command',
            'osxmkhomedir-hook = osxmkhomedir.commands:login_hook',
            'osxmkhomedir-set-desktop = osxmkhomedir.commands:set_desktop',
        ],
    },
    classifiers=[
        'Programming Language :: Python',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    **extra
)

