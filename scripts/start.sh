#!/bin/bash

# USB stick variables
DEVNAME=/dev/sda1
MOUNT_POINT=/mnt/storage
ID_FS_TYPE=vfat

# Mount USB drive on startup
mkdir -p $MOUNT_POINT
mount -v -t $ID_FS_TYPE -o rw $DEVNAME $MOUNT_POINT

# Start main program
python -u /usr/src/app/main.py
