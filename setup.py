#!/usr/bin/env python2
# Copyright (C) 2010 Sebastian Pipping <sebastian@pipping.org>
# Licensed under GPL v3 or later

from distutils.core import setup

import sys
sys.path.insert(0, 'modules')
from svneverever.version import VERSION_STR

setup(
    name='svneverever',
    description='Tool collecting path entries across SVN history',
    license='GPL v3 or later',
    version=VERSION_STR,
    url='https://github.com/hartwork/svneverever',
    author='Sebastian Pipping',
    author_email='sebastian@pipping.org',
    package_dir={'':'modules', },
    packages=['svneverever', ],
    scripts=['svneverever', ],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Natural Language :: English',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development :: Version Control',
        'Topic :: Utilities',
    ],
)
