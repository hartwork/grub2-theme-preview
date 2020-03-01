# Copyright (C) 2015 Sebastian Pipping <sebastian@pipping.org>
# Licensed under GPL v2 or later

PYTHON = python3
DESTDIR = /

all:

clean:
	find -name '*.pyc' -delete

dist:
	$(PYTHON) setup.py sdist

install:
	$(PYTHON) setup.py install --root "$(DESTDIR)"

.PHONY: all clean dist install
