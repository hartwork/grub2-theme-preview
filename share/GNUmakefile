# Copyright (C) 2015 Sebastian Pipping <sebastian@pipping.org>
# Licensed under GPL v2 or later

DISK = grub2_theme_demo.img
GRUB_CFG_TO_APPLY = grub.cfg
FULL_THEME = 1
THEME_DIR = /usr/share/grub/themes/starfield/
BACKGROUND_IMAGE = /usr/share/grub/themes/starfield/starfield.png

GRUB2_MKRESCUE = grub2-mkrescue
KVM = qemu-system-x86_64

all:

disk-created:
ifeq ($(FULL_THEME),1)
	$(GRUB2_MKRESCUE) \
		--output "$(DISK)" \
		boot/grub/grub.cfg="$(GRUB_CFG_TO_APPLY)" \
		boot/grub/themes/DEMO/="$(THEME_DIR)"
else
	$(GRUB2_MKRESCUE) \
		--output "$(DISK)" \
		boot/grub/grub.cfg="$(GRUB_CFG_TO_APPLY)" \
		boot/grub/themes/DEMO.png="$(BACKGROUND_IMAGE)"
endif

run: disk-created
	$(KVM) -hda "$(DISK)"


.PHONY: TODO
