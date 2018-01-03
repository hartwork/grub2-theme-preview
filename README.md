About
=====

*grub2-theme-preview* came into life when I was looking around for
available GRUB 2.x themes and wanted a way to quickly see a theme
in action without rebooting real hardware.

It takes a theme folder (or just a single picture),
creates a temporary bootable image using `grub2-mkrescue` and launches
that image in a virtual machine using KVM/QEMU, all without root privileges.


## Install

Run `make install` with root privileges.

Dependencies:
 - `grub2-mkrescue` - (can be installed as `grub-mkrescue` on some systems)
 - [QEMU](http://wiki.qemu.org/Main_Page) - "... hypervisor that performs hardware virtualization"
 - [mtools](https://www.gnu.org/software/mtools/) - "... collection of utilities to access MS-DOS"
 - [libisoburn](http://libburnia-project.org/) - "frontend [...] which enables creation and expansion of the ISO format"


## Usage

```
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
