# Copyright (C) 2015 Sebastian Pipping <sebastian@pipping.org>
# Licensed under GPL v2 or later

import errno
import glob
import os
import re
from argparse import ArgumentParser
from enum import Enum
from textwrap import dedent
import signal
import subprocess
import sys
import tempfile
import traceback
import platform

from .version import VERSION_STR
from .which import which


_PATH_IMAGE_ONLY_PNG = 'themes/DEMO.png'
_PATH_IMAGE_ONLY_TGA = 'themes/DEMO.tga'
_PATH_IMAGE_ONLY_JPEG = 'themes/DEMO.jpeg'
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


class _SourceType(Enum):
    DIRECTORY = 1
    FILE_PNG = 2
    FILE_TGA = 3
    FILE_JPEG = 4


def _classify_source(abspath_source):
    abspath_source_lower = abspath_source.lower()
    if abspath_source_lower.endswith('.tga'):
        return _SourceType.FILE_TGA
    elif abspath_source_lower.endswith('.png'):
        return _SourceType.FILE_PNG
    elif abspath_source_lower.endswith('.jpeg'):
        return _SourceType.FILE_JPEG
    elif abspath_source_lower.endswith('.jpg'):
        return _SourceType.FILE_JPEG
    return _SourceType.DIRECTORY


def _get_image_path_for(source_type):
    if source_type == _SourceType.FILE_TGA:
        return _PATH_IMAGE_ONLY_TGA
    elif source_type == _SourceType.FILE_JPEG:
        return _PATH_IMAGE_ONLY_JPEG
    return _PATH_IMAGE_ONLY_PNG


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


def _generate_dummy_menu_entries():
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
            """)


def _make_grub_cfg_load_our_theme(grub_cfg_content, source_type, resolution_or_none, font_files_to_load, timeout_seconds):
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
            'insmod tga',
            'insmod jpeg',
            ]

    if resolution_or_none is not None:
        # We need to be the first call to 'terminal_output gfxterm'
        # if we want to have a say with resolution
        prolog_chunks.append('set gfxmode=%dx%d' % resolution_or_none)
        prolog_chunks.append('terminal_output gfxterm')

    prolog_chunks.append('')  # blank line
    prolog_chunks.append('')  # trailing new line

    epilog_chunks = [
            # Ensure that we always have one or more menu entries
            '',
            'submenu \'Reboot / Shutdown\' {',
            '    menuentry Reboot { reboot }',
            '    menuentry Shutdown { halt }',
            '}',

            '',
            'set default=0',  # i.e. move cursor to first entry
            'set timeout=%d' % timeout_seconds,
            ]

    if resolution_or_none is None:
        # If we haven't ensured GFX mode earlier, do it now
        # so it's done at least once
        epilog_chunks.append('terminal_output gfxterm')

    if source_type == _SourceType.DIRECTORY:
        epilog_chunks.append('set theme=$prefix/%s/theme.txt' % _PATH_FULL_THEME)
    else:
        epilog_chunks.append('background_image $prefix/%s' % _get_image_path_for(source_type))

    # Make sure that lines like "set root='hd0,msdos1'" do not get us
    # into unnecessary "unknown filesystem" error situations
    grub_cfg_content = re.sub('^([ \\t]*set root=)(.+)',
                              "\\1'hd0'  # replaced by grub2-theme-preview, was \\2",
                              grub_cfg_content,
                              flags=re.MULTILINE)

    return '\n'.join(prolog_chunks) + grub_cfg_content + '\n'.join(epilog_chunks)


def _make_final_grub_cfg_content(source_type, source_grub_cfg, resolution_or_none, font_files_to_load, timeout_seconds):
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
        content = _generate_dummy_menu_entries()

    return _make_grub_cfg_load_our_theme(content, source_type, resolution_or_none, font_files_to_load, timeout_seconds)


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


def validate_grub2_mkrescue_addition(candidate: str) -> str:
    if not '=/' in candidate:
        raise ValueError
    return candidate

# This string is picked up by argparse error message generator:
validate_grub2_mkrescue_addition.__name__ = 'grub2-mkrescue addition'


def parse_command_line():
    parser = ArgumentParser(prog='grub2-theme-preview')
    parser.add_argument('--grub-cfg', metavar='PATH', help='Path of custom grub.cfg file to use (default: /boot/grub{2,}/grub.cfg)')
    parser.add_argument('--verbose', default=False, action='store_true', help='Increase verbosity')
    parser.add_argument('--resolution', metavar='WxH', type=resolution, help='Set a custom resolution, e.g. 800x600')
    parser.add_argument('--timeout', metavar='SECONDS', dest='timeout_seconds', type=timeout, default=30,
            help='Set timeout in whole seconds or -1 to disable (default: %(default)s seconds)')
    parser.add_argument('--add', action='append', dest='addition_requests', metavar='TARGET=/SOURCE', type=validate_grub2_mkrescue_addition,
                        help=('make grub2-mkrescue add file(s) from /SOURCE to /TARGET in the rescue image'
                              ' (can be passed multiple times)'))
    parser.add_argument('source', metavar='PATH', help='Path of theme directory (or PNG/TGA image file) to preview')
    parser.add_argument('--version', action='version', version='%(prog)s ' + VERSION_STR)

    commands = parser.add_argument_group('command location arguments')
    commands.add_argument('--grub2-mkrescue', metavar='COMMAND', help='grub2-mkrescue command (default: auto-detect)')
    commands.add_argument('--qemu', metavar='COMMAND', help='KVM/QEMU command (default: qemu-system-<machine>)')
    commands.add_argument('--xorriso', default='xorriso', metavar='COMMAND', help='xorriso command (default: %(default)s)')

    qemu = parser.add_argument_group('arguments related to invokation of QEMU/KVM')
    qemu.add_argument('--no-kvm', dest='enable_kvm', default=True, action='store_false',
                      help='Do not pass -enable-kvm to QEMU (and hence fall back to acceleration "tcg" which is significantly slower than KVM)')

    debugging = parser.add_argument_group('debugging arguments')
    debugging.add_argument('--debug', default=False, action='store_true', help='Enable debugging output')
    debugging.add_argument('--plain-rescue-image', default=False, action='store_true',
                           help='Use unprocessed GRUB rescue image with no theme patched in; '
                           'useful for checking if a plain GRUB rescue image shows up a GRUB shell, successfully.')

    options = parser.parse_args()

    if options.qemu is None:
        import platform
        options.qemu = 'qemu-system-%s' % platform.machine()

    if options.grub2_mkrescue is None:
        try:
            which('grub2-mkrescue')
        except OSError:
            options.grub2_mkrescue = 'grub-mkrescue'  # without "2"
        else:
            options.grub2_mkrescue = 'grub2-mkrescue'  # with "2"

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


def _grub2_ovmf_tuple():
    """
    Returns a 3-tuple with:
    1. the absolute filename of the OVMF image to use or None if missing
    2. a display hint for humans where the file is located, roughly
    3. a list of package names to try install, potentially
    """
    candidates = [
        '/usr/share/edk2-ovmf/OVMF_CODE.fd',  # Gentoo and its derivatives
        '/usr/share/edk2-ovmf/x64/OVMF_CODE.fd',  # Arch Linux and its derivatives
        '/usr/share/OVMF/OVMF_CODE.fd',  # Debian and its derivatives
        '/usr/share/edk2/ovmf/OVMF_CODE.fd',  # Fedora (and its derivatives?)
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate, None, []
    else:
        return None, '/usr/share/[..]/OVMF_CODE.fd', ['edk2-ovmf', 'ovmf']


def _dump_grub_cfg_content(grub_cfg_content, target):
    bar = '>>> grub.cfg ' + '<' * 40
    print(file=target)
    print(bar, file=target)
    print(grub_cfg_content, file=target)
    print(bar, file=target)
    print(file=target)


def _require_recursive_read_access_at(abs_path):
    for root, directories, files in os.walk(abs_path):
        for basename in directories + files:
            abs_path = os.path.join(root, basename)
            if not os.access(abs_path, os.R_OK):
                raise IOError(errno.EACCES, 'Permission denied: \'%s\'' % abs_path)


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

    source_type = _classify_source(options.source)

    if source_type != _SourceType.DIRECTORY:
        font_files_to_load = []
    else:
        font_files_to_load = list(iterate_pf2_files_relative(normalized_source))

    abs_grub_cfg_or_none = options.grub_cfg and os.path.abspath(options.grub_cfg)
    grub_cfg_content = _make_final_grub_cfg_content(
            source_type,
            abs_grub_cfg_or_none,
            options.resolution,
            font_files_to_load,
            options.timeout_seconds,
            )
    if options.debug:
        _dump_grub_cfg_content(grub_cfg_content, target=sys.stderr)

    abs_tmp_folder = tempfile.mkdtemp()
    try:
        abs_tmp_grub_cfg_file = os.path.join(abs_tmp_folder, 'grub.cfg')
        with open(abs_tmp_grub_cfg_file, 'w') as f:
            f.write(grub_cfg_content)

        grub2_platform = _grub2_platform()
        grub2_platform_directory = _grub2_directory(grub2_platform)
        if not os.path.exists(grub2_platform_directory):
            raise OSError(errno.ENOENT, 'GRUB platform directory "%s" not found' % grub2_platform_directory)

        is_efi_host = 'efi' in grub2_platform
        if is_efi_host:
            omvf_image_path, omvf_image_path_hint, omvf_candidate_package_names = _grub2_ovmf_tuple()
            if omvf_image_path is None:
                package_names_hint = ' or '.join(repr(package_name)
                                                 for package_name
                                                 in omvf_candidate_package_names)
                raise OSError(errno.ENOENT,
                              'OVMF image file "%s" is missing, please install package %s.'
                              % (omvf_image_path_hint, package_names_hint))
            print(f'INFO: Found OVMF image at {omvf_image_path!r}.')

        try:
            abs_tmp_img_file = os.path.join(abs_tmp_folder, 'grub2_theme_demo.img')
            assemble_cmd = [
                options.grub2_mkrescue,
                '--directory=%s' % grub2_platform_directory,
                '--xorriso', options.xorriso,
                '--output', abs_tmp_img_file,
                ]

            if not options.plain_rescue_image:
                # Add boot loader entry files read by GRUB's blscfg command, e.g. on recent Fedora
                abs_boot_loader_path = '/boot/loader/'
                if os.path.exists(abs_boot_loader_path):
                    try:
                        _require_recursive_read_access_at(abs_boot_loader_path)
                    except IOError as e:
                        print('INFO: %s' % str(e))
                        print('INFO: Files at "%s" will NOT be added to the GRUB rescue image.'
                              % abs_boot_loader_path)
                    else:
                        assemble_cmd.append('boot/loader=' + abs_boot_loader_path)

                assemble_cmd.append('boot/grub/grub.cfg=%s' % abs_tmp_grub_cfg_file)

            if source_type != _SourceType.DIRECTORY:
                assemble_cmd += [
                    'boot/grub/%s=%s' % (_get_image_path_for(source_type), normalized_source),
                    ]
            else:
                assemble_cmd += [
                    'boot/grub/%s/=%s' % (_PATH_FULL_THEME, normalized_source),
                    ]

            assemble_cmd += options.addition_requests

            try:
                _run(assemble_cmd, options.verbose)

                if not os.path.exists(abs_tmp_img_file):
                    command = os.path.basename(options.grub2_mkrescue)
                    raise OSError(errno.ENOENT, '%s failed to create the rescue image' % command)

                run_command = [
                    options.qemu,
                    '-m', '256',
                    '-drive', 'file=%s,index=0,media=disk,format=raw' % abs_tmp_img_file,
                ]
                if options.enable_kvm:
                    run_command.append('-enable-kvm')
                if is_efi_host:
                    run_command += [
                        '-bios', omvf_image_path,
                    ]

                print('INFO: Please give GRUB a moment to show up in QEMU...')

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
