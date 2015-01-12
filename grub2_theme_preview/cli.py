# Copyright (C) 2015 Sebastian Pipping <sebastian@pipping.org>
# Licensed under GPL v2 or later

from __future__ import print_function

from argparse import ArgumentParser
from .version import VERSION_STR


def main():
    parser = ArgumentParser()
    parser.add_argument('--version', action='version', version='%(prog)s ' + VERSION_STR)
    parser.parse_args()
