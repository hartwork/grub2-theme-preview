```
   ___ ___ _   _ ___   _____ _                    ___             _            
  / __| _ \ | | | _ ) |_   _| |_  ___ _ __  ___  | _ \_ _ _____ _(_)_____ __ __
 | (_ |   / |_| | _ \   | | | ' \/ -_) '  \/ -_) |  _/ '_/ -_) V / / -_) V  V /
  \___|_|_\\___/|___/   |_| |_||_\___|_|_|_\___| |_| |_| \___|\_/|_\___|\_/\_/ 
                                                                               
```

## 📓 About

**[grub2-theme-preview](https://github.com/hartwork/grub2-theme-preview) came into life when I was looking around for
available GRUB 2.x themes and wanted a way to quickly see a theme
in action without rebooting real hardware.**

**It takes a theme folder ( or just a single picture ),
creates a temporary bootable image using `grub2-mkrescue` and launches
that image in a virtual machine using [KVM](https://www.linux-kvm.org/page/Main_Page) / [QEMU](https://www.qemu.org/), all without root privileges.**

<p align="center">
  <img width=50% src="https://raw.githubusercontent.com/hartwork/grub2-theme-preview/master/screenshots/grub2-theme-preview__gutsblack-archlinux.png" alt="screenshot" />
</p>
<p align="center">
  <sub>Theme displayed : <a href="https://forums.archlinux.fr/viewtopic.php?t=11361">gutsblack-archlinux</a></sub>
</p>

## ⚙️ Installation

**🔸 First, install these dependencies :**

- **Debian / Ubuntu**
```bash
sudo apt install grub-common ovmf xorriso qemu qemu-system mtools python3 python3-pip
```

**🔸 To install the latest release from [PyPI](https://pypi.org/project/grub2-theme-preview/) :**

```
pip3 install grub2-theme-preview
```

**🔸 To install from a Git clone ( for development ) :**

```
pip3 install --user --editable .
```

## 🛠️ Usage

```
# grub2-theme-preview --help
usage: grub2-theme-preview [-h] [--grub-cfg PATH] [--verbose]
                           [--resolution WxH] [--timeout SECONDS]
                           [--add TARGET=/SOURCE] [--version]
                           [--grub2-mkrescue COMMAND] [--qemu COMMAND]
                           [--xorriso COMMAND] [--no-kvm] [--debug]
                           [--plain-rescue-image]
                           PATH

positional arguments:
  PATH                  path of theme directory (or PNG/TGA image file) to
                        preview

optional arguments:
  -h, --help            show this help message and exit
  --grub-cfg PATH       path of custom grub.cfg file to use (default:
                        /boot/grub{2,}/grub.cfg)
  --verbose             increase verbosity
  --resolution WxH      set a custom resolution, e.g. 800x600
  --timeout SECONDS     set GRUB timeout in whole seconds or -1 to disable
                        (default: 30 seconds)
  --add TARGET=/SOURCE  make grub2-mkrescue add file(s) from /SOURCE to
                        /TARGET in the rescue image (can be passed multiple
                        times)
  --version             show program's version number and exit

command location arguments:
  --grub2-mkrescue COMMAND
                        grub2-mkrescue command (default: auto-detect)
  --qemu COMMAND        KVM/QEMU command (default: qemu-system-<machine>)
  --xorriso COMMAND     xorriso command (default: xorriso)

arguments related to invokation of QEMU/KVM:
  --display DISPLAY     pass "-display DISPLAY" to QEMU, see "man qemu" for
                        details (default: use QEMU's default display)
  --full-screen         pass "-full-screen" to QEMU
  --no-kvm              do not pass -enable-kvm to QEMU (and hence fall back
                        to acceleration "tcg" which is significantly slower
                        than KVM)
  --vga CARD            pass "-vga CARD" to QEMU, see "man qemu" for details
                        (default: use QEMU's default VGA card)

debugging arguments:
  --debug               enable debugging output
  --plain-rescue-image  use unprocessed GRUB rescue image with no theme
                        patched in; useful for checking if a plain GRUB rescue
                        image shows up a GRUB shell, successfully.
```
