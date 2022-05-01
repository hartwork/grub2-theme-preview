# Copyright (c) 2022 Sebastian Pipping <sebastian@pipping.org>
# Licensed under GPL v2 or later

import os
import unittest
from contextlib import contextmanager
from io import StringIO
from tempfile import TemporaryDirectory
from textwrap import dedent
from unittest.mock import patch

from parameterized import parameterized

from ..__main__ import _make_grub_cfg_load_our_theme, _SourceType, main


@contextmanager
def path_inserted(path):
    """
    Context manager that inserts ``path`` at the start of ``${PATH}``
    """
    original_path = os.environ['PATH']
    new_path = f'{path}{os.pathsep}{os.environ["PATH"]}'

    os.environ['PATH'] = new_path
    try:
        yield
    finally:
        os.environ['PATH'] = original_path


@contextmanager
def fake_grub2_mkrescue():
    """
    Context manager that creates a fake ``grub2-mkrescue``
    command (that only touches the output file name) and puts it
    at the start of ``${PATH}``
    """
    with TemporaryDirectory() as tempdir:
        with open(os.path.join(tempdir, 'grub2-mkrescue'), 'w') as f:
            print(dedent("""\
                #! /usr/bin/env bash
                # Look for "--output <filename>" in $@ and touch that file
                set -e -u
                while [[ $# -gt 0 ]]; do
                    case "$1" in
                    --output)
                        touch "$2"
                        exit 0
                        ;;
                    esac
                    shift
                done
                false
            """),
                  file=f)
            f.flush()
            os.fchmod(f.fileno(), 0o555)
            f.close()

            with path_inserted(tempdir):
                yield


class CliTest(unittest.TestCase):

    @parameterized.expand([
        ('with --verbose', ['--verbose'], '# true', True),
        ('without --verbose', [], '# true', False),
        ('with --display', ['--verbose', '--display=sdl'], '-display sdl', True),
        ('without --display', ['--verbose'], '-display sdl', False),
        ('with --no-kvm', ['--verbose', '--no-kvm'], '-enable-kvm', False),
        ('without --no-kvm', ['--verbose'], '-enable-kvm', True),
        ('with --add', ['--verbose', '--add', 'foo1=/bar1', '--add',
                        'foo2=/bar2'], ' foo1=/bar1 foo2=/bar2', True),
        ('without --add', [
            '--verbose',
        ], ' foo1=/bar1 foo2=/bar2', False),
        ('with --plain-rescue-image', ['--verbose',
                                       '--plain-rescue-image'], ' boot/grub/grub.cfg=', False),
        ('without --plain-rescue-image', ['--verbose'], ' boot/grub/grub.cfg=', True),
    ])
    def test_argument_effect__stdout(self, _label, extra_argv, needle, needed_expected):
        with TemporaryDirectory() as tempdir:
            argv = [None, '--qemu', 'true'] + extra_argv + [tempdir]
            with patch('sys.stdout', StringIO()) as stdout, \
                    patch('sys.stderr', StringIO()), \
                    fake_grub2_mkrescue():
                main(argv)

            assertion = self.assertIn if needed_expected else self.assertNotIn
            assertion(needle, stdout.getvalue())

    @parameterized.expand([
        ('with --resolution', ['--debug', '--resolution', '100x200'], 'set gfxmode=100x200', True),
        ('without --resolution', ['--debug'], 'set gfxmode=100x200', False),
        ('with --timeout', ['--debug', '--timeout', '123'], 'set timeout=123', True),
        ('without --timeout', ['--debug'], 'set timeout=123', False),
    ])
    def test_argument_effect__stderr(self, _label, extra_argv, needle, needed_expected):
        with TemporaryDirectory() as tempdir:
            argv = [None, '--qemu', 'true'] + extra_argv + [tempdir]
            with patch('sys.stdout', StringIO()), \
                    patch('sys.stderr', StringIO()) as stderr, \
                    fake_grub2_mkrescue():
                main(argv)

            assertion = self.assertIn if needed_expected else self.assertNotIn
            assertion(needle, stderr.getvalue())

    @parameterized.expand([
        ('with --debug', ['--debug'], 'Exception: ', True),
        ('without --debug', [], 'Exception: ', False),
    ])
    def test_exception_handling(self, _label, extra_argv, needle, needed_expected):
        exception_message = '1cb121f0eebce6d7aba8e2c937dc07d41294f6f5'  # arbitrary
        argv = [None] + extra_argv + [None]

        with patch('grub2_theme_preview.__main__._inner_main',
                   side_effect=Exception(exception_message)), \
                patch('sys.stdout', StringIO()), \
                patch('sys.stderr', StringIO()) as stderr, \
                self.assertRaises(SystemExit) as caught:
            main(argv)

        self.assertEqual(caught.exception.code, 1)
        self.assertIn(exception_message, stderr.getvalue())

        assertion = self.assertIn if needed_expected else self.assertNotIn
        assertion(needle, stderr.getvalue())


class GrubCfgContentProcessingTest(unittest.TestCase):

    def _process_grub_cfg_content(self, grub_cfg_content, resolution_or_none):
        source_type = _SourceType.DIRECTORY  # arbitrary
        font_files_to_load = []  # arbitrary
        timeout_seconds = 123  # arbitrary
        return _make_grub_cfg_load_our_theme(grub_cfg_content, source_type, resolution_or_none,
                                             font_files_to_load, timeout_seconds)

    def test_no_custom_resolution(self):
        grub_cfg_input = ''
        resolution_or_none = None

        grub_cfg_output = self._process_grub_cfg_content(grub_cfg_input, resolution_or_none)

        self.assertNotIn('gfxmode', grub_cfg_output)

    def test_custom_resolution_with_gfxmode_auto(self):
        grub_cfg_input = dedent("""\
            some random line
            set gfxmode=auto
            set gfxmode=auto  # with comment
                set gfxmode=auto  # with indent
            some random line
        """)
        resolution_or_none = (1024, 768)

        grub_cfg_output = self._process_grub_cfg_content(grub_cfg_input, resolution_or_none)

        self.assertNotIn('set gfxmode=auto', grub_cfg_output)
        self.assertEqual(grub_cfg_output.count('set gfxmode=1024x768'), 1 + 3)
        self.assertEqual(grub_cfg_output.count('set gfxmode='), 1 + 3)

    def test_custom_resolution_without_gfxmode_auto(self):
        grub_cfg_input = ''
        resolution_or_none = (1024, 768)

        grub_cfg_output = self._process_grub_cfg_content(grub_cfg_input, resolution_or_none)

        self.assertIn('set gfxmode=1024x768', grub_cfg_output)
        self.assertEqual(grub_cfg_output.count('set gfxmode='), 1)
