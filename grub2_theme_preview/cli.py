# Copyright (C) 2015 Sebastian Pipping <sebastian@pipping.org>
# Licensed under GPL v2 or later

from __future__ import print_function

import errno
import inspect
import os
from argparse import ArgumentParser
from textwrap import dedent
import subprocess
import sys
import tempfile
from .version import VERSION_STR


_PATH_IMAGE_ONLY = 'themes/DEMO.png'
_PATH_FULL_THEME = 'themes/DEMO'


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


def _make_menu_entries():
    return dedent("""\
            menuentry 'Debian' --class debian --class gnu-linux --class linux --class gnu --class os {
                reboot
            }

            menuentry 'Gentoo' --class gentoo --class gnu-linux --class linux --class gnu --class os {
                reboot
            }

            menuentry "Memtest86+" {
                reboot
            }

            submenu 'Reboot / Shutdown' {
                menuentry Reboot { reboot }
                menuentry Shutdown { halt }
            }
            """)


def _make_grub_cfg_load_our_theme(grub_cfg_content, is_full_theme):
    # NOTE: The last font loaded becomes the default/fallback font
    #       So if we load fonts first, the remaining default font
    #       will remain unchanged and the theme will display unchanged.
    prolog = dedent("""\
            loadfont $prefix/fonts/unicode.pf2

            insmod all_video
            insmod gfxterm
            insmod png
            """)

    common_epilog = dedent("""\
            set timeout=-1
            terminal_output gfxterm
            """)

    if is_full_theme:
        epilog = common_epilog + dedent("""\
                set theme=$prefix/%s/theme.txt
                """ % _PATH_FULL_THEME)
    else:
        epilog = common_epilog + dedent("""\
                background_image $prefix/%s
                """ % _PATH_IMAGE_ONLY)

    return prolog + grub_cfg_content + epilog


def _make_final_grub_cfg_content(is_full_theme, source_grub_cfg):
    if source_grub_cfg is not None:
        files_to_try_to_read = [source_grub_cfg]
        fail_if_missing = True
    else:
        files_to_try_to_read = [
                '/boot/grub2/grub.cfg',
                '/boot/grub/grub.cfg',
                ]
        fail_if_missing = False

    for candidate in files_to_try_to_read:
        if not os.path.exists(candidate):
            if fail_if_missing:
                print('ERROR: [Errno %d] %s: \'%s\'' % (errno.ENOENT, os.strerror(errno.ENOENT), candidate), file=sys.stderr)
                sys.exit(1)
            continue

        try:
            f = open(candidate, 'r')
            content = f.read()
            f.close()
        except IOError as e:
            print('INFO: %s' % str(e))
        else:
            break
    else:
        print('INFO: Could not read external GRUB config file, falling back to internal example config')
        content = _make_menu_entries()

    return _make_grub_cfg_load_our_theme(content, is_full_theme)


def main():
    parser = ArgumentParser()
    parser.add_argument('--image', action='store_true', help='Preview a background image rather than a whole theme')
    parser.add_argument('--grub-cfg', metavar='PATH', help='Path of custom grub.cfg file to use (default: /boot/grub{2,}/grub.cfg)')
    parser.add_argument('--grub2-mkrescue', default='grub2-mkrescue', metavar='COMMAND', help='grub2-mkrescue command (default: %(default)s)')
    parser.add_argument('--qemu', default='qemu-system-x86_64', metavar='COMMAND', help='kvm/qemu command (default: %(default)s)')
    parser.add_argument('--xorriso', default='xorriso', metavar='COMMAND', help='xorriso command (default: %(default)s)')
    parser.add_argument('--verbose', default=False, action='store_true', help='Increase verbosity')
    parser.add_argument('source', metavar='PATH', help='Path of theme directory (or image file) to preview')
    parser.add_argument('--version', action='version', version='%(prog)s ' + VERSION_STR)
    options = parser.parse_args()

    _check_for_xorriso(options.xorriso)

    abs_grub_cfg_or_none = options.grub_cfg and os.path.abspath(options.grub_cfg)
    grub_cfg_content = _make_final_grub_cfg_content(not options.image, abs_grub_cfg_or_none)

    normalized_source = os.path.normpath(os.path.abspath(options.source))

    abs_tmp_folder = tempfile.mkdtemp()
    try:
        abs_tmp_img_file = os.path.join(abs_tmp_folder, 'grub2_theme_demo.img')
        abs_tmp_grub_cfg_file = os.path.join(abs_tmp_folder, 'grub.cfg')

        f = open(abs_tmp_grub_cfg_file, 'w')
        f.write(grub_cfg_content)
        f.close()

        assemble_cmd = [
            options.grub2_mkrescue,
            '--output', abs_tmp_img_file,
            'boot/grub/grub.cfg=%s' % abs_tmp_grub_cfg_file,
            ]

        if options.image:
            assemble_cmd += [
                'boot/grub/%s=%s' % (_PATH_IMAGE_ONLY, normalized_source),
                ]
        else:
            assemble_cmd += [
                'boot/grub/%s/=%s' % (_PATH_FULL_THEME, normalized_source),
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
            os.remove(abs_tmp_grub_cfg_file)
            os.rmdir(abs_tmp_folder)
        except OSError:
            pass
