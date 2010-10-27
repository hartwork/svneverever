#!/usr/bin/env python
# Copyright (C) 2010 Sebastian Pipping <sebastian@pipping.org>
# Licensed under GPL v3 or later

from distutils.core import setup

import sys
sys.path.append('modules')
from svneverever.version import VERSION_STR

setup(
    name='svneverever',
    description='Tool collecting path entries across SVN history',
    license='GPL v3 or later',
    version=VERSION_STR,
    url='http://git.goodpoint.de/?p=svneverever.git;a=summary',
    author='Sebastian Pipping',
    author_email='sebastian@pipping.org',
    package_dir={'':'modules', },
    packages=['svneverever', ],
    scripts=['svneverever', ],
)
