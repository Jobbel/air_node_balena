#!/bin/bash
# Setting DBUS addresss so that we can talk to Modem Manager
export DBUS_SYSTEM_BUS_ADDRESS="unix:path=/host/run/dbus/system_bus_socket"

# USB stick variables
DEVNAME=/dev/sda1
MOUNT_POINT=/mnt/storage
ID_FS_TYPE=vfat

# This Function checks if a device is mounted
isMounted    () { findmnt -rno SOURCE,TARGET "$1" >/dev/null;} #path or device

# Mount flash drive on startup
mkdir -p $MOUNT_POINT
mount -v -t $ID_FS_TYPE -o rw $DEVNAME $MOUNT_POINT

# Start main program
python /usr/src/app/main.py &

# Keep Internet up and copy new logging data to usb stick every 10 minutes
while :
do
	sleep 600
	
	if isMounted $DEVNAME; then
		echo "USB device is mounted, updating log files"
		rsync -a /data/log_data $MOUNT_POINT
	else 
		echo "No USB device is mounted"
	fi
	
	if curl -s --connect-timeout 52 http://google.com  > /dev/null; then
		echo "Internet connection is working"
	else
		echo "Internet connection seems down, restarting modem"
		# Force unmount USB Drive
		umount -f $MOUNT_POINT
		rmdir $MOUNT_POINT
		udisksctl power-off -b /dev/sda
		# Reset USB power
		uhubctl -l 1-1 -a 0  > /dev/null
		sleep 5
		uhubctl -l 1-1 -a 1  > /dev/null
	fi
done
