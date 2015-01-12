# Copyright (C) 2015 Sebastian Pipping <sebastian@pipping.org>
# Licensed under GPL v2 or later

from __future__ import print_function

import errno
import hashlib
import inspect
import os
from argparse import ArgumentParser
import subprocess
from .version import VERSION_STR


def _get_abs_self_dir():
    return os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))


def _is_run_from_git():
    return os.path.exists(os.path.join(_get_abs_self_dir(), '..', '.git'))


def _sha256(text):
    h = hashlib.sha256()
    h.update(text)
    return h.hexdigest()


def _mkdir_if_missing(path):
    try:
        os.mkdir(path)
        return True
    except OSError as e:
        if e.errno == errno.EEXIST:
            return False
        raise


def main():
    parser = ArgumentParser()
    parser.add_argument('--image', action='store_true', help='Preview a background image rather than a whole theme')
    parser.add_argument('--grub-cfg', metavar='PATH', help='Path grub.cfg file to apply')
    parser.add_argument('source', metavar='PATH', help='Path of theme directory (or image file) to preview')
    parser.add_argument('--version', action='version', version='%(prog)s ' + VERSION_STR)
    options = parser.parse_args()


    if _is_run_from_git():
        abs_share_root = os.path.normpath(os.path.join(_get_abs_self_dir(), '..', 'share'))
        abs_workdir_root = os.path.normpath(os.path.join(_get_abs_self_dir(), '..'))
    else:
        abs_share_root = '/usr/share/grub2-theme-preview/'
        abs_workdir_root = '/var/tmp/grub2-theme-preview/'

    abs_makefile = os.path.join(abs_share_root, 'GNUmakefile')

    if options.image:
        if options.grub_cfg:
            abs_grub_cfg = os.path.abspath(options.abs_grub_cfg)
        else:
            abs_grub_cfg = os.path.join(abs_share_root, 'background_image.cfg')
    else:
        abs_grub_cfg = os.path.join(abs_share_root, 'full_theme.cfg')

    normalized_source = os.path.normpath(os.path.abspath(options.source))
    theme_id = _sha256(normalized_source)
    tmp_folder = os.path.join(abs_workdir_root, theme_id)


    cmd_start = [
        'make',
        '-f', abs_makefile,
        '-C', tmp_folder
        ]

    if options.image:
        cmd_middle = [
            'FULL_THEME=0',
            'BACKGROUND_IMAGE=%s' % normalized_source,
            ]
    else:
        cmd_middle = [
            'FULL_THEME=1',
            'THEME_DIR=%s' % normalized_source,
            ]

    cmd_end = [
            'BOOT_MOUNT_POINT=%s' % os.path.join(tmp_folder, 'boot'),
            'GRUB_CFG_TO_APPLY=%s' % abs_grub_cfg,
            'run',
        ]

    created = _mkdir_if_missing(tmp_folder)
    cmd = cmd_start + cmd_middle + cmd_end

    print('# %s' % ' '.join(cmd))
    subprocess.call(cmd)
