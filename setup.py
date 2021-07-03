#!/usr/bin/env python3
# Copyright (C) 2010-2021 Sebastian Pipping <sebastian@pipping.org>
# Licensed under GPL v3 or later

from setuptools import find_packages, setup

import sys
sys.path.insert(0, '.')
from svneverever.version import VERSION_STR  # noqa: E402

setup(
    name='svneverever',
    description='Tool collecting path entries across SVN history',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    license='GPL v3 or later',
    version=VERSION_STR,
    url='https://github.com/hartwork/svneverever',
    author='Sebastian Pipping',
    author_email='sebastian@pipping.org',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'svneverever = svneverever.__main__:main',
        ],
    },
    python_requires='>=3.6',
    setup_requires=[
        'setuptools>=38.6.0',  # for long_description_content_type
    ],
    install_requires=[
        # Package 'pysvn' on PyPI is not the PySVN off SourceForge
        # that we need!
    ],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved '
        ':: GNU General Public License v3 or later (GPLv3+)',
        'Natural Language :: English',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Software Development :: Version Control',
        'Topic :: Utilities',
    ],
)
