#!/bin/bash

# USB stick variables
DEVNAME=/dev/sda1
MOUNT_POINT=/mnt/storage
ID_FS_TYPE=vfat

# umount if mounted, required to safely run fsck
umount -v $DEVNAME

# check drive and autofix
fsck -p $DEVNAME

# Mount USB drive on startup
mkdir -p $MOUNT_POINT
mount -v -o rw $DEVNAME $MOUNT_POINT

# Start main program
python -u /usr/src/app/main.py
