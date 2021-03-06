#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of the CSP.LMC project
#
# Distributed under the terms of the BSD-3-Clause license.
# See LICENSE.txt for more info.

import os
import sys
from setuptools import setup

setup_dir = os.path.dirname(os.path.abspath(__file__))

# make sure we use latest info from local code
sys.path.insert(0, setup_dir)

INFO = {}
readme_filename = os.path.join(setup_dir, 'README.rst')
with open(readme_filename) as file:
    long_description = file.read()

release_filename = os.path.join(setup_dir, '..', 'release.py')
exec(open(release_filename).read(), INFO)

setup(
        name=INFO['name'],
        version=INFO['version'],
        description='CspMaster is the CSP Element.',
        packages=[
          'CspMaster'
        ],
        include_package_data=True,
        test_suite="test",
        entry_points={'console_scripts':['CspMaster = CspMaster:main']},
        author='E.G',
        author_email='elisabetta.giani@inaf.it',
        license='BSD-3-Clause',
        long_description=long_description,
        url='www.tango-controls.org',
        platforms="All Platforms",
        install_requires = [
            'pytango==9.3.1', 
        ],
        #test_suite='test',
        setup_requires=[
            'pytest-runner',
            'sphinx',
            'recommonmark'
        ],
        tests_require=[
            'pytest',
            'pytest-cov',
            'pytest-json-report',
            'pycodestyle',
        ],
        extras_require={
            'dev':  ['prospector[with_pyroma]', 'yapf', 'isort']
      })
