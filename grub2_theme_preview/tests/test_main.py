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

from ..__main__ import _GRUB_DEBUG_SPEC, main


@contextmanager
def path_inserted(path):
    """
    Context manager that inserts ``path`` at the start of ``${PATH}``
    """
    original_path = os.environ["PATH"]
    new_path = f"{path}{os.pathsep}{os.environ['PATH']}"

    os.environ["PATH"] = new_path
    try:
        yield
    finally:
        os.environ["PATH"] = original_path


@contextmanager
def fake_grub2_mkrescue():
    """
    Context manager that creates a fake ``grub2-mkrescue``
    command (that only touches the output file name) and puts it
    at the start of ``${PATH}``
    """
    with TemporaryDirectory() as tempdir:
        with open(os.path.join(tempdir, "grub2-mkrescue"), "w") as f:
            print(
                dedent("""\
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
                file=f,
            )
            f.flush()
            os.fchmod(f.fileno(), 0o555)
            f.close()

            with path_inserted(tempdir):
                yield


class CliTest(unittest.TestCase):
    @parameterized.expand(
        [
            ("with --verbose", ["--verbose"], "# true", True),
            ("without --verbose", [], "# true", False),
            ("with --display", ["--verbose", "--display=sdl"], "-display sdl", True),
            ("without --display", ["--verbose"], "-display sdl", False),
            ("with --vga", ["--verbose", "--vga=virtio"], "-vga virtio", True),
            ("without --vga", ["--verbose"], "-vga virtio", False),
            ("with --full-screen", ["--verbose", "--full-screen"], "-full-screen", True),
            ("without --full-screen", ["--verbose"], "-full-screen", False),
            ("with --no-kvm", ["--verbose", "--no-kvm"], "-enable-kvm", False),
            ("without --no-kvm", ["--verbose"], "-enable-kvm", True),
            (
                "with --add",
                ["--verbose", "--add", "foo1=/bar1", "--add", "foo2=/bar2"],
                " foo1=/bar1 foo2=/bar2",
                True,
            ),
            (
                "without --add",
                [
                    "--verbose",
                ],
                " foo1=/bar1 foo2=/bar2",
                False,
            ),
            (
                "with --plain-rescue-image",
                ["--verbose", "--plain-rescue-image"],
                " boot/grub/grub.cfg=",
                False,
            ),
            ("without --plain-rescue-image", ["--verbose"], " boot/grub/grub.cfg=", True),
            (
                "without --grub-debug-file qemu serial backend",
                ["--verbose"],
                "file:",
                False,
            ),
        ]
    )
    def test_argument_effect__stdout(self, _label, extra_argv, needle, needed_expected):
        with TemporaryDirectory() as tempdir:
            argv = [None, "--qemu", "true"] + extra_argv + [tempdir]
            with (
                patch("sys.stdout", StringIO()) as stdout,
                patch("sys.stderr", StringIO()),
                fake_grub2_mkrescue(),
            ):
                main(argv)

            assertion = self.assertIn if needed_expected else self.assertNotIn
            assertion(needle, stdout.getvalue())

    def test_grub_debug_file_adds_qemu_serial_backend(self):
        with TemporaryDirectory() as tempdir:
            capture_abs = os.path.join(tempdir, "grub-debug.txt")
            argv = [
                None,
                "--qemu",
                "true",
                "--verbose",
                "--grub-debug-file",
                capture_abs,
                tempdir,
            ]
            with (
                patch("sys.stdout", StringIO()) as stdout,
                patch("sys.stderr", StringIO()),
                fake_grub2_mkrescue(),
            ):
                main(argv)
            stdout_text = stdout.getvalue()
            self.assertIn("file:", stdout_text)
            self.assertIn(capture_abs, stdout_text)

    @parameterized.expand(
        [
            (
                "with --resolution",
                ["--debug", "--resolution", "100x200"],
                "set gfxmode=100x200",
                True,
            ),
            ("without --resolution", ["--debug"], "set gfxmode=100x200", False),
            ("with --timeout", ["--debug", "--timeout", "123"], "set timeout=123", True),
            ("without --timeout", ["--debug"], "set timeout=123", False),
        ]
    )
    def test_argument_effect__stderr(self, _label, extra_argv, needle, needed_expected):
        with TemporaryDirectory() as tempdir:
            argv = [None, "--qemu", "true"] + extra_argv + [tempdir]
            with (
                patch("sys.stdout", StringIO()),
                patch("sys.stderr", StringIO()) as stderr,
                fake_grub2_mkrescue(),
            ):
                main(argv)

            assertion = self.assertIn if needed_expected else self.assertNotIn
            assertion(needle, stderr.getvalue())

    def test_grub_debug_file_stderr_grub_cfg_has_debug_spec_and_serial(self):
        with TemporaryDirectory() as tempdir:
            capture_abs = os.path.join(tempdir, "grub-debug.txt")
            argv = [
                None,
                "--qemu",
                "true",
                "--debug",
                "--grub-debug-file",
                capture_abs,
                tempdir,
            ]
            with (
                patch("sys.stdout", StringIO()),
                patch("sys.stderr", StringIO()) as stderr,
                fake_grub2_mkrescue(),
            ):
                main(argv)
            dump = stderr.getvalue()
            self.assertIn(
                f"set debug={_GRUB_DEBUG_SPEC}\nserial\n",
                dump,
            )
            self.assertIn("terminal_output gfxterm serial", dump)

    def test_without_grub_debug_file_stderr_grub_cfg_skips_serial_and_set_debug(self):
        with TemporaryDirectory() as tempdir:
            argv = [None, "--qemu", "true", "--debug", tempdir]
            with (
                patch("sys.stdout", StringIO()),
                patch("sys.stderr", StringIO()) as stderr,
                fake_grub2_mkrescue(),
            ):
                main(argv)
            dump = stderr.getvalue()
            self.assertNotIn("set debug=", dump)
            self.assertNotIn("terminal_output gfxterm serial", dump)

    def test_grub_debug_file_truncates_existing_capture_file(self):
        with TemporaryDirectory() as tempcwd:
            with TemporaryDirectory() as theme_dir:
                with open(os.path.join(theme_dir, "theme.txt"), "w") as tf:
                    tf.write("# minimal theme\n")
                capture_relative = "grub-debug.txt"
                capture = os.path.join(tempcwd, capture_relative)
                with open(capture, "w") as xf:
                    xf.write("discard-me")

                cwd_before = os.getcwd()
                os.chdir(tempcwd)
                try:
                    argv = [
                        None,
                        "--qemu",
                        "true",
                        "--grub-debug-file",
                        capture_relative,
                        theme_dir,
                    ]
                    with (
                        patch("sys.stdout", StringIO()),
                        patch("sys.stderr", StringIO()),
                        fake_grub2_mkrescue(),
                    ):
                        main(argv)
                finally:
                    os.chdir(cwd_before)

            self.assertTrue(os.path.isfile(capture))
            with open(capture, "rb") as f:
                self.assertEqual(f.read(), b"")

    @parameterized.expand(
        [
            ("with --debug", ["--debug"], "Exception: ", True),
            ("without --debug", [], "Exception: ", False),
        ]
    )
    def test_exception_handling(self, _label, extra_argv, needle, needed_expected):
        exception_message = "1cb121f0eebce6d7aba8e2c937dc07d41294f6f5"  # arbitrary
        argv = [None] + extra_argv + [None]

        with (
            patch(
                "grub2_theme_preview.__main__._inner_main",
                side_effect=Exception(exception_message),
            ),
            patch("sys.stdout", StringIO()),
            patch("sys.stderr", StringIO()) as stderr,
            self.assertRaises(SystemExit) as caught,
        ):
            main(argv)

        self.assertEqual(caught.exception.code, 1)
        self.assertIn(exception_message, stderr.getvalue())

        assertion = self.assertIn if needed_expected else self.assertNotIn
        assertion(needle, stderr.getvalue())
