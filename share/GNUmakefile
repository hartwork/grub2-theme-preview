# Copyright (C) 2015 Sebastian Pipping <sebastian@pipping.org>
# Licensed under GPL v2 or later

DISK = grub2_theme_demo.img
GRUB_CFG_TO_APPLY = grub.cfg
BOOT_MOUNT_POINT = boot
THEME_DIR = /usr/share/grub/themes/starfield/

BLKID = blkid
CP = cp
GRUB2_INSTALL = grub2-install
KVM = qemu-system-x86_64
LOSETUP = losetup
KPARTX = kpartx
MKDIR = mkdir
MKFS = mkfs
MOUNT = mount
PARTED = /usr/sbin/parted
SUDO = sudo
SYNC = sync
TOUCH = touch
TRUNCATE = truncate

# Activate bashism
override SHELL = /bin/bash


define FIND_DISK_DEVICE
$(SUDO) $(LOSETUP) -j "$(DISK)" | awk -F: '{print $$1}'
endef

define FIND_BOOT_PARTITION_DEVICE
$(SUDO) $(LOSETUP) -j "$(DISK)" | awk -F: '{print $$1}' | sed 's|/dev/loop\([0-9]\+\)|/dev/mapper/loop\1p1|'
endef


all:

disk-created:
	[[ -f "$(DISK)" ]] \
		|| { \
			$(TOUCH) "$(DISK)" \
			&& $(TRUNCATE) --size $$((500 * 1024**2)) "$(DISK)" \
		; }

disk-partitioned: disk-created
	$(PARTED) --script --machine "$(DISK)" print 2>/dev/null | fgrep -q msdos \
		|| { \
			$(PARTED) --script "$(DISK)" mklabel msdos \
			&& $(PARTED) --script "$(DISK)" mkpart primary ext2 0% 100% \
		; }

disk-device-set-up: disk-partitioned
	[[ `$(SUDO) $(LOSETUP) -j "$(DISK)" | wc -l` -eq 1 ]] \
		|| $(SUDO) $(LOSETUP) --show -f "$(DISK)"

boot-partition-device-set-up: disk-device-set-up
	DISK_DEVICE="$$($(call FIND_DISK_DEVICE))"; \
	[[ "$${DISK_DEVICE}" = /dev/loop* ]] || exit 1 \
		; $(SUDO) $(KPARTX) -p p -a -v "$${DISK_DEVICE}"

boot-partition-formatted: boot-partition-device-set-up
	BOOT_PARTITION_DEVICE="$$($(call FIND_BOOT_PARTITION_DEVICE))"; \
	[[ "$${BOOT_PARTITION_DEVICE}" = /dev/mapper/loop*p* ]] || exit 1 ; \
	$(SUDO) $(BLKID) "$${BOOT_PARTITION_DEVICE}" | fgrep -q ext2 \
		|| $(SUDO) $(MKFS) -t ext2 "$${BOOT_PARTITION_DEVICE}"

$(BOOT_MOUNT_POINT):
	$(MKDIR) "$(BOOT_MOUNT_POINT)"

boot-partition-mounted: boot-partition-device-set-up boot-partition-formatted | $(BOOT_MOUNT_POINT)
	BOOT_PARTITION_DEVICE="$$($(call FIND_BOOT_PARTITION_DEVICE))"; \
	[[ "$${BOOT_PARTITION_DEVICE}" = /dev/mapper/loop*p* ]] || exit 1 \
	; mount | fgrep -q "$${BOOT_PARTITION_DEVICE} on " \
		|| $(SUDO) $(MOUNT) "$${BOOT_PARTITION_DEVICE}" "$(BOOT_MOUNT_POINT)"

grub-installed: disk-device-set-up boot-partition-mounted
	DISK_DEVICE="$$($(call FIND_DISK_DEVICE))"; \
	[[ "$${DISK_DEVICE}" = /dev/loop* ]] || exit 1 \
	; [[ -d "$(BOOT_MOUNT_POINT)/grub" ]] \
		|| $(SUDO) $(GRUB2_INSTALL) \
			--boot-directory="$(BOOT_MOUNT_POINT)" \
			"$${DISK_DEVICE}"

grub-config-placed: grub-installed boot-partition-mounted
	$(SUDO) $(CP) -v $(GRUB_CFG_TO_APPLY) $(BOOT_MOUNT_POINT)/grub/grub.cfg

theme-copied: boot-partition-mounted
	[[ -d "$(BOOT_MOUNT_POINT)/grub/themes/DEMO" ]] \
		|| { \
			$(SUDO) $(MKDIR) "$(BOOT_MOUNT_POINT)/grub/themes/DEMO" \
			&& $(SUDO) $(CP) -Rv $(THEME_DIR)/* "$(BOOT_MOUNT_POINT)/grub/themes/DEMO/" \
		; }

disk-synced: grub-config-placed theme-copied
	$(SYNC)

run: disk-synced
	$(SUDO) $(KVM) -hda "$(DISK)"


.PHONY: TODO
