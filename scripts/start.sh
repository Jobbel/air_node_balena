#!/bin/bash
# Setting DBUS addresss so that we can talk to Modem Manager
export DBUS_SYSTEM_BUS_ADDRESS="unix:path=/host/run/dbus/system_bus_socket"

DEVNAME=/dev/sda1
MOUNT_POINT=/mnt/storage
ID_FS_TYPE=vfat

mkdir -p /mnt/storage
mount -t vfat -U CAA2-D115 -o rw /mnt/storage

# Start main program
python /usr/src/app/main.py &

# Keep Internet up and runnning
while :
do
	sleep 600
	if curl -s --connect-timeout 52 http://google.com  > /dev/null; then
		echo "Internet connection is working"
	else
		echo "Internet connection seems down, restarting modem"
		# Force unmount USB Drive
		umount -l /mnt/storage
		rmdir /mnt/storage
		udisksctl power-off -b /dev/sda
		# Reset USB power
		uhubctl -l 1-1 -a 0  > /dev/null
		sleep 5
		uhubctl -l 1-1 -a 1  > /dev/null
	fi
done
