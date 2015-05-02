# Copyright (C) 2015 Sebastian Pipping <sebastian@pipping.org>
# Licensed under GPL v2 or later

from __future__ import print_function

import errno
import inspect
import os
from argparse import ArgumentParser
import subprocess
import sys
import tempfile
from .version import VERSION_STR


def _get_abs_self_dir():
    return os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))


def _is_run_from_git():
    return os.path.exists(os.path.join(_get_abs_self_dir(), '..', '.git'))


def _mkdir_if_missing(path):
    try:
        os.mkdir(path)
        return True
    except OSError as e:
        if e.errno == errno.EEXIST:
            return False
        raise


def _run(cmd, verbose):
    if verbose:
        print('# %s' % ' '.join(cmd))
        stdout = None
    else:
        stdout = open('/dev/null', 'w')

    subprocess.call(cmd, stdout=stdout, stderr=stdout)

    if not verbose:
        stdout.close()


def _check_for_xorriso(xorriso_command):
    cmd = [xorriso_command, '--version']
    dev_null = open('/dev/null', 'w')
    try:
        subprocess.call(cmd, stdout=dev_null, stderr=dev_null)
    except OSError:
        msg = (
            'ERROR: '
            'You do not seem to have xorriso (of libisoburn/libburnia) installed.'
            ' '
            'Without xorriso, grub2-mkrescue has little chance of producing bootable images.'
            ' '
            'If this complaint seems mistaken to you, please use the --xorriso parameter to work around this check.'
        )
        print(msg, file=sys.stderr)
        sys.exit(1)
    finally:
        dev_null.close()


def main():
    parser = ArgumentParser()
    parser.add_argument('--image', action='store_true', help='Preview a background image rather than a whole theme')
    parser.add_argument('--grub-cfg', metavar='PATH', help='Path grub.cfg file to apply')
    parser.add_argument('--grub2-mkrescue', default='grub2-mkrescue', metavar='COMMAND', help='grub2-mkrescue command (default: %(default)s)')
    parser.add_argument('--qemu', default='qemu-system-x86_64', metavar='COMMAND', help='kvm/qemu command (default: %(default)s)')
    parser.add_argument('--xorriso', default='xorriso', metavar='COMMAND', help='xorriso command (default: %(default)s)')
    parser.add_argument('--verbose', default=False, action='store_true', help='Increase verbosity')
    parser.add_argument('source', metavar='PATH', help='Path of theme directory (or image file) to preview')
    parser.add_argument('--version', action='version', version='%(prog)s ' + VERSION_STR)
    options = parser.parse_args()

    _check_for_xorriso(options.xorriso)

    if _is_run_from_git():
        abs_share_root = os.path.normpath(os.path.join(_get_abs_self_dir(), '..', 'share'))
    else:
        abs_share_root = '/usr/share/grub2-theme-preview/'

    if options.image:
        if options.grub_cfg:
            abs_grub_cfg = os.path.abspath(options.abs_grub_cfg)
        else:
            abs_grub_cfg = os.path.join(abs_share_root, 'background_image.cfg')
    else:
        abs_grub_cfg = os.path.join(abs_share_root, 'full_theme.cfg')

    normalized_source = os.path.normpath(os.path.abspath(options.source))

    abs_tmp_folder = tempfile.mkdtemp()
    try:
        abs_tmp_img_file = os.path.join(abs_tmp_folder, 'grub2_theme_demo.img')

        assemble_cmd = [
            options.grub2_mkrescue,
            '--output', abs_tmp_img_file,
            'boot/grub/grub.cfg=%s' % abs_grub_cfg,
            ]

        if options.image:
            assemble_cmd += [
                'boot/grub/themes/DEMO.png=%s' % normalized_source,
                ]
        else:
            assemble_cmd += [
                'boot/grub/themes/DEMO/=%s' % normalized_source,
                ]

        run_command = [
            options.qemu,
            '-hda', abs_tmp_img_file,
            ]

        _run(assemble_cmd, options.verbose)
        _run(run_command, options.verbose)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            os.remove(abs_tmp_img_file)
            os.rmdir(abs_tmp_folder)
        except OSError:
            pass
