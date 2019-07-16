#!/usr/bin/env python
# Copyright (C) 2010-2019 Sebastian Pipping <sebastian@pipping.org>
# Licensed under GPL v3 or later

from setuptools import setup

import sys
sys.path.insert(0, 'modules')
from svneverever.version import VERSION_STR  # noqa: E402

setup(
    name='svneverever',
    description='Tool collecting path entries across SVN history',
    license='GPL v3 or later',
    version=VERSION_STR,
    url='https://github.com/hartwork/svneverever',
    author='Sebastian Pipping',
    author_email='sebastian@pipping.org',
    package_dir={'': 'modules', },
    packages=['svneverever', ],
    entry_points={
        'console_scripts': [
            'svneverever = svneverever.__main__:main',
        ],
    },
    install_requires=[
        'six',
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
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Software Development :: Version Control',
        'Topic :: Utilities',
    ],
)
