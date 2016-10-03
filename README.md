About
=====

*grub2-theme-preview* came into life when I was looking around for
available GRUB 2.x themes and wanted a way to quickly see a theme
in action without rebooting real hardware.

It takes a theme folder (or just a single picture),
creates a temporary bootable image using `grub2-mkrescue` and launches
that image in a virtual machine using KVM/QEMU, all without root privileges.


## Usage

```
$ grub2-theme-preview --help
usage: grub2-theme-preview [-h] [--image] [--grub-cfg PATH] [--qemu COMMAND]
                           [--verbose] [--debug] [--resolution WxH]
                           [--timeout SECONDS] [--version]
                           [--grub2-mkrescue COMMAND] [--xorriso COMMAND]
                           PATH

positional arguments:
  PATH                  Path of theme directory (or image file) to preview

optional arguments:
  -h, --help            show this help message and exit
  --image               Preview a background image rather than a whole theme
  --grub-cfg PATH       Path of custom grub.cfg file to use (default:
                        /boot/grub{2,}/grub.cfg)
  --qemu COMMAND        KVM/QEMU command (default: qemu-system-<machine>)
  --verbose             Increase verbosity
  --debug               Enable debugging output
  --resolution WxH      Set a custom resolution, e.g. 800x600
  --timeout SECONDS     Set timeout in whole seconds or -1 to disable
                        (default: 30 seconds)
  --version             show program's version number and exit

command location arguments:
  --grub2-mkrescue COMMAND
                        grub2-mkrescue command (default: grub2-mkrescue)
  --xorriso COMMAND     xorriso command (default: xorriso)
```
