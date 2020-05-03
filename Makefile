# Copyright (C) 2011 Sebastian Pipping <sebastian@pipping.org>
# Licensed under GPL v3 or later

DESTDIR = /
PYTHON = python3

all:

dist:
	$(RM) MANIFEST
	$(PYTHON) setup.py sdist

install:
	$(PYTHON) setup.py install --root "$(DESTDIR)"

.PHONY: all dist install
