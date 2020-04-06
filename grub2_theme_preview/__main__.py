# Copyright (C) 2015 Sebastian Pipping <sebastian@pipping.org>
# Licensed under GPL v2 or later

import errno
import glob
import os
import re
from argparse import ArgumentParser
from textwrap import dedent
import signal
import subprocess
import sys
import tempfile
import traceback
import platform

from .version import VERSION_STR
from .which import which


_PATH_IMAGE_ONLY = 'themes/DEMO.png'
_PATH_FULL_THEME = 'themes/DEMO'

_KILL_BY_SIGNAL = 128


class _CommandNotFoundException(Exception):
    def __init__(self, command, package=None):
        self._command = command
        self._package = package

    def __str__(self):
        if self._package is None:
            return 'Command "%s" not found' % self._command
        else:
            return 'Command "%s" of %s not found' % (self._command, self._package)


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

    try:
        subprocess.call(cmd, stdout=stdout, stderr=stdout)
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise
        raise _CommandNotFoundException(cmd[0])
    finally:
        if not verbose:
            stdout.close()


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


def _make_grub_cfg_load_our_theme(grub_cfg_content, is_full_theme, resolution_or_none, font_files_to_load, timeout_seconds):
    # NOTE: The last font loaded becomes the default/fallback font
    #       So if we load fonts first, the remaining default font
    #       will remain unchanged and the theme will display unchanged.
    prolog_chunks = [
            'loadfont $prefix/fonts/unicode.pf2',
            ]

    for relative_path in font_files_to_load:
        prolog_chunks.append('loadfont $prefix/%s/%s' % (_PATH_FULL_THEME, relative_path))

    prolog_chunks += [
            'insmod all_video',
            'insmod gfxterm',
            'insmod png',
            ]

    if resolution_or_none is not None:
        # We need to be the first call to 'terminal_output gfxterm'
        # if we want to have a say with resolution
        prolog_chunks.append('set gfxmode=%dx%d' % resolution_or_none)
        prolog_chunks.append('terminal_output gfxterm')

    prolog_chunks.append('')  # trailing new line

    epilog_chunks = [
            '',  # leading new line
            'set timeout=%d' % timeout_seconds,
            ]

    if resolution_or_none is None:
        # If we haven't ensured GFX mode earlier, do it now
        # so it's done at least once
        epilog_chunks.append('terminal_output gfxterm')

    if is_full_theme:
        epilog_chunks.append('set theme=$prefix/%s/theme.txt' % _PATH_FULL_THEME)
    else:
        epilog_chunks.append('background_image $prefix/%s' % _PATH_IMAGE_ONLY)

    return '\n'.join(prolog_chunks) + grub_cfg_content + '\n'.join(epilog_chunks)


def _make_final_grub_cfg_content(is_full_theme, source_grub_cfg, resolution_or_none, font_files_to_load, timeout_seconds):
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

    return _make_grub_cfg_load_our_theme(content, is_full_theme, resolution_or_none, font_files_to_load, timeout_seconds)


def resolution(text):
    m = re.match('^([1-9][0-9]{2,})x([1-9][0-9]{2,})$', text)
    if not m:
        raise ValueError('Not a supported resolution: "%s"' % text)
    width = int(m.group(1))
    height = int(m.group(2))
    return (width, height)


def timeout(text):
    seconds = int(text)
    if seconds < 0:
        seconds = -1
    return seconds


def iterate_pf2_files_relative(abs_theme_dir):
    # Imitate /etc/grub.d/00_header:
    # for x in "$themedir"/*.pf2 "$themedir"/f/*.pf2; do
    for pattern in (
            os.path.join(abs_theme_dir, '*.pf2'),
            os.path.join(abs_theme_dir, 'f', '*.pf2'),
            ):
        for path in sorted(glob.iglob(pattern), key=lambda path: path.lower()):
            relative_path = os.path.relpath(path, abs_theme_dir)
            print('INFO: Appending to fonts to load: %s' % relative_path)
            yield relative_path


def parse_command_line():
    parser = ArgumentParser(prog='grub2-theme-preview')
    parser.add_argument('--image', action='store_true', help='Preview a background image rather than a whole theme')
    parser.add_argument('--grub-cfg', metavar='PATH', help='Path of custom grub.cfg file to use (default: /boot/grub{2,}/grub.cfg)')
    parser.add_argument('--verbose', default=False, action='store_true', help='Increase verbosity')
    parser.add_argument('--resolution', metavar='WxH', type=resolution, help='Set a custom resolution, e.g. 800x600')
    parser.add_argument('--timeout', metavar='SECONDS', dest='timeout_seconds', type=timeout, default=30,
            help='Set timeout in whole seconds or -1 to disable (default: %(default)s seconds)')
    parser.add_argument('source', metavar='PATH', help='Path of theme directory (or image file) to preview')
    parser.add_argument('--version', action='version', version='%(prog)s ' + VERSION_STR)

    commands = parser.add_argument_group('command location arguments')
    commands.add_argument('--grub2-mkrescue', default='grub-mkrescue', metavar='COMMAND', help='grub2-mkrescue command (default: %(default)s)')
    commands.add_argument('--qemu', metavar='COMMAND', help='KVM/QEMU command (default: qemu-system-<machine>)')
    commands.add_argument('--xorriso', default='xorriso', metavar='COMMAND', help='xorriso command (default: %(default)s)')

    debugging = parser.add_argument_group('debugging arguments')
    debugging.add_argument('--debug', default=False, action='store_true', help='Enable debugging output')
    debugging.add_argument('--plain-rescue-image', default=False, action='store_true',
                           help='Use unprocessed GRUB rescue image with no theme patched in; '
                           'useful for checking if a plain GRUB rescue image shows up a GRUB shell, successfully.')

    options = parser.parse_args()

    if options.qemu is None:
        import platform
        options.qemu = 'qemu-system-%s' % platform.machine()

    return options


def _ignore_oserror(func, *args, **kwargs):
    try:
        func(*args, **kwargs)
    except OSError:
        pass


def _grub2_directory(platform):
    return  '/usr/lib/grub/%s' % platform


def _grub2_platform():
    if os.path.exists('/sys/firmware/efi'):
        _cpu = platform.machine()
        _platform = 'efi'
    else:
        # for BIOS-based machines
        # https://www.gnu.org/software/grub/manual/grub/grub.html#Installation
        _cpu = 'i386'
        _platform = 'pc'
    return '%s-%s' % (_cpu, _platform)


def _inner_main(options):
    for command, package in (
            (options.grub2_mkrescue, 'Grub 2.x'),
            ('mcopy', 'mtools'),    # see issue #8
            ('mformat', 'mtools'),  # see issue #8
            (options.qemu, 'KVM/QEMU'),
            (options.xorriso, 'libisoburn'),
            ):
        try:
            which(command)
        except OSError:
            raise _CommandNotFoundException(command, package)

    normalized_source = os.path.normpath(os.path.abspath(options.source))

    if options.image:
        font_files_to_load = []
    else:
        font_files_to_load = list(iterate_pf2_files_relative(normalized_source))

    abs_grub_cfg_or_none = options.grub_cfg and os.path.abspath(options.grub_cfg)
    grub_cfg_content = _make_final_grub_cfg_content(
            not options.image,
            abs_grub_cfg_or_none,
            options.resolution,
            font_files_to_load,
            options.timeout_seconds,
            )

    abs_tmp_folder = tempfile.mkdtemp()
    try:
        abs_tmp_grub_cfg_file = os.path.join(abs_tmp_folder, 'grub.cfg')
        with open(abs_tmp_grub_cfg_file, 'w') as f:
            f.write(grub_cfg_content)

        grub2_platform_directory = _grub2_directory(_grub2_platform())
        if not os.path.exists(grub2_platform_directory):
            raise OSError(errno.ENOENT, 'GRUB platform directory "%s" not found' % grub2_platform_directory)

        try:
            abs_tmp_img_file = os.path.join(abs_tmp_folder, 'grub2_theme_demo.img')
            assemble_cmd = [
                options.grub2_mkrescue,
                '--directory=%s' % grub2_platform_directory,
                '--xorriso', options.xorriso,
                '--output', abs_tmp_img_file,
                ]

            if not options.plain_rescue_image:
                assemble_cmd.append('boot/grub/grub.cfg=%s' % abs_tmp_grub_cfg_file)

            try:
                if options.image:
                    assemble_cmd += [
                        'boot/grub/%s=%s' % (_PATH_IMAGE_ONLY, normalized_source),
                        ]
                else:
                    assemble_cmd += [
                        'boot/grub/%s/=%s' % (_PATH_FULL_THEME, normalized_source),
                        ]
                _run(assemble_cmd, options.verbose)

                if not os.path.exists(abs_tmp_img_file):
                    command = os.path.basename(options.grub2_mkrescue)
                    raise OSError(errno.ENOENT, '%s failed to create the rescue image' % command)

                print('INFO: Please give GRUB a moment to show up in QEMU...')

                run_command = [
                    options.qemu,
                    '-drive', 'file=%s,index=0,media=disk,format=raw' % abs_tmp_img_file,
                    ]
                _run(run_command, options.verbose)
            finally:
                _ignore_oserror(os.remove, abs_tmp_img_file)
        finally:
            _ignore_oserror(os.remove, abs_tmp_grub_cfg_file)
    finally:
        _ignore_oserror(os.rmdir, abs_tmp_folder)


def main():
    try:
        options = parse_command_line()
    except KeyboardInterrupt:
        sys.exit(_KILL_BY_SIGNAL + signal.SIGINT)

    try:
        _inner_main(options)
    except KeyboardInterrupt:
        sys.exit(_KILL_BY_SIGNAL + signal.SIGINT)
    except BaseException as e:
        if options.debug:
            traceback.print_exc()
        print('ERROR: %s' % str(e), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
