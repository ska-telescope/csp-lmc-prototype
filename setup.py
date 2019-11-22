#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the CSP.LMC project
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.

import os
import sys
from setuptools import setup, find_packages

setup_dir = os.path.dirname(os.path.abspath(__file__))

# make sure we use latest info from local code
sys.path.insert(0, setup_dir)

INFO = {}
with open("README.md") as file:
    long_description = file.read()

RELEASE_FILENAME = os.path.join(setup_dir, 'csplmc', 'release.py')
exec(open(RELEASE_FILENAME).read(), INFO)

setup(
        name=INFO['name'],
        version=INFO['version'],
        description=INFO['description'],
        author=INFO['author'],
        author_email=INFO['author_email'],
        packages=find_packages(),
        license=INFO['license'],
        url=INFO['url'],
        long_description=long_description,
        keywords="csp lmc ska tango",
        platforms="All Platforms",
        include_package_data=True,
        install_requires = [
            'pytango >=9.3.1',
            'future'
        ],
        setup_requires=[
            'pytest-runner',
            'sphinx',
            'recommonmark'
        ],
        test_suite="test",
        entry_points={'console_scripts':['CspMaster = CspMaster:main']},
        classifiers=[
            "Development Status :: 3 - Alpha",
            "Programming Language :: Python :: 3",
            "Operating System :: POSIX :: Linux",
            "Intended Audience :: Developers",
            "License :: Other/Proprietary License",
            "Topic::Scientific/Enineering :: Astronomy",
            ],
        tests_require=[
            'pytest',
            'pytest-cov',
            'pytest-json-report',
            'pycodestyle',
        ],
        extras_require={
      })
