#!/bin/bash

# USB stick variables
MOUNT_POINT=/mnt/storage

# Ensure the mount point exists
mkdir -p $MOUNT_POINT

# Check if /dev/sda exists
if [ -e /dev/sda1 ]; then
    DEVNAME=/dev/sda1
else
    DEVNAME=/dev/sdb1
fi

# Unmount the device if it's already mounted
if mount | grep -q "$DEVNAME on $MOUNT_POINT"; then
    umount -v $MOUNT_POINT
fi

# Attempt to repair the USB drive with fsck (for VFAT)
fsck -p $DEVNAME

# Check the exit status of fsck
if [ $? -eq 0 ]; then
    echo "USB drive file system restored successfully."
else
    echo "USB drive file system repair failed. You may need to manually repair the device."
fi

# Mount USB drive
mount -v -o rw $DEVNAME $MOUNT_POINT

# Start main program
python -u /usr/src/app/main.py