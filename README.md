# About

**grub2-theme-preview** came into life when I was looking around for
available GRUB 2.x themes and wanted a way to quickly see a theme
in action without rebooting real hardware.

It takes a theme folder (or just a single picture),
creates a temporary bootable image using `grub2-mkrescue` and launches
that image in a virtual machine using KVM/QEMU, all without root privileges.

![grub2-theme-preview showing theme "gutsblack-archlinux"](https://raw.githubusercontent.com/hartwork/grub2-theme-preview/master/screenshots/grub2-theme-preview__gutsblack-archlinux.png)

(Showing theme [gutsblack-archlinux](https://forums.archlinux.fr/viewtopic.php?t=11361))


## Installation

To install the latest release from [PyPI](https://pypi.org/):

```console
# pip install --user grub2-theme-preview
```

To install from a Git clone _for development_:

```console
# pip install --user --editable .
```

Please make sure to install these _non-PyPI dependencies_ as well:
 - `grub2-mkrescue` (can be installed as `grub-mkrescue` on some systems)
 - [QEMU](https://wiki.qemu.org/Main_Page) — _hypervisor that performs hardware virtualization_
 - [mtools](https://www.gnu.org/software/mtools/) — _collection of utilities to access MS-DOS_
 - [libisoburn](https://dev.lovelyhq.com/libburnia/libisoburn) — _frontend which enables creation and expansion of the ISO format_


## Usage

```console
# grub2-theme-preview --help
usage: grub2-theme-preview [-h] [--image] [--grub-cfg PATH] [--verbose]
                           [--resolution WxH] [--timeout SECONDS] [--version]
                           [--grub2-mkrescue COMMAND] [--qemu COMMAND]
                           [--xorriso COMMAND] [--debug]
                           [--plain-rescue-image]
                           PATH

positional arguments:
  PATH                  Path of theme directory (or image file) to preview

optional arguments:
  -h, --help            show this help message and exit
  --image               Preview a background image rather than a whole theme
  --grub-cfg PATH       Path of custom grub.cfg file to use (default:
                        /boot/grub{2,}/grub.cfg)
  --verbose             Increase verbosity
  --resolution WxH      Set a custom resolution, e.g. 800x600
  --timeout SECONDS     Set timeout in whole seconds or -1 to disable
                        (default: 30 seconds)
  --version             show program's version number and exit

command location arguments:
  --grub2-mkrescue COMMAND
                        grub2-mkrescue command (default: grub-mkrescue)
  --qemu COMMAND        KVM/QEMU command (default: qemu-system-<machine>)
  --xorriso COMMAND     xorriso command (default: xorriso)

debugging arguments:
  --debug               Enable debugging output
  --plain-rescue-image  Use unprocessed GRUB rescue image with no theme
                        patched in; useful for checking if a plain GRUB rescue
                        image shows up a GRUB shell, successfully.
```
