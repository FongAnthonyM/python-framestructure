#!/usr/bin/env python
# -*- encoding: utf-8 -*-
""" setup.py
The setup for this package.
"""
# Package Header #
from src.framestructure.__header__ import *

# Header #
__author__ = __author__
__credits__ = __credits__
__maintainer__ = __maintainer__
__email__ = __email__


# Imports #
# Standard Libraries #
import io
import re
from glob import glob
from os.path import basename
from os.path import dirname
from os.path import join
from os.path import splitext

# Third-Party Packages #
from setuptools import find_packages
from setuptools import setup


# Definitions #
# Functions #
def read(*names, **kwargs):
    with io.open(
        join(dirname(__file__), *names),
        encoding=kwargs.get('encoding', 'utf8')
    ) as fh:
        return fh.read()


# Main #
setup(
    name=__package_name__,
    version=__version__,
    license=__license__,
    description='Objects for organizing data in frame structures.',
    author='Anthony Michael Fong',
    author_email='FongAnthonyM@gmail.com',
    url='https://github.com/fonganthonym/python-framestructure',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    py_modules=[splitext(basename(path))[0] for path in glob('src/*.py')],
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        # complete classifier list: http://pypi.python.org/pypi?%3Aaction=list_classifiers
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: Unix',
        'Operating System :: POSIX',
        'Operating System :: Microsoft :: Windows',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        # uncomment if you test on these interpreters:
        # 'Programming Language :: Python :: Implementation :: IronPython',
        # 'Programming Language :: Python :: Implementation :: Jython',
        # 'Programming Language :: Python :: Implementation :: Stackless',
        'Topic :: Utilities',
    ],
    project_urls={
        'Documentation': 'https://python-framestructure.readthedocs.io/',
        'Changelog': 'https://python-framestructure.readthedocs.io/en/latest/changelog.html',
        'Issue Tracker': 'https://github.com/fonganthonym/python-framestructure/issues',
    },
    keywords=[
        # eg: 'keyword1', 'keyword2', 'keyword3',
    ],
    python_requires='>=3.6',
    install_requires=[
        'baseobjects>=1.5.0', 'dspobjects', 'numpy', 'scipy'
    ],
    extras_require={
        "dev": ['pytest>=6.2.3', 'nox'],
    },
    entry_points={
        'console_scripts': [
            'framestructure = framestructure.cli:main',
        ]
    },
)
