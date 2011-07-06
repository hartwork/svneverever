# Copyright (C) 2011 Sebastian Pipping <sebastian@pipping.org>
# Licensed under GPL v3 or later

all:

dist:
	rm -f MANIFEST
	./setup.py sdist

.PHONY: dist
