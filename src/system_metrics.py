import datetime
import psutil
import prt


def get_cpu_temp():
    try:
        temp_file = open('/sys/class/thermal/thermal_zone0/temp')
        return round(float(temp_file.read()) / 1000, 2)
    except Exception:
        return 0


def get_cpu_usage():
    try:
        return psutil.cpu_percent()
    except Exception:
        prt.GLOBAL_ENTITY.print_once("Failed to fetch CPU usage", "Successfully fetching CPU usage again", 62)
        return 0


def get_uptime():
    try:
        temp_file = open('/proc/uptime', 'r')
        uptime_seconds = round(float(temp_file.readline().split()[0]))
        return str(datetime.timedelta(seconds=uptime_seconds))
    except Exception:
        return 0


def get_disk_usage():
    try:
        return psutil.disk_usage('/').percent
    except Exception:
        prt.GLOBAL_ENTITY.print_once("Failed to fetch disk usage", "Successfully fetching disk usage again", 62)
        return 0


def get_usb_drive_usage():
    try:
        return psutil.disk_usage('/mnt/storage').percent
    except Exception:
        prt.GLOBAL_ENTITY.print_once("Failed to fetch USB Drive usage", "Successfully fetching USB Drive usage again",
                                     62)
        return 0


def get_total_data_usage():
    for device in ['wwan0', 'wwp1s0u1u3i5', 'wwp1s0u1u4i5', 'ppp0']:
        try:
            netio = psutil.net_io_counters(pernic=True)
            net_usage = netio[device].bytes_sent + netio[device].bytes_recv
            return round(net_usage / 1000000, 2)
        except Exception:
            pass
    prt.GLOBAL_ENTITY.print_once("Failed to fetch data usage", "Successfully fetching data usage again", 62)
    return 0


def get_ram_usage():
    try:
        return psutil.virtual_memory().percent
    except Exception:
        prt.GLOBAL_ENTITY.print_once("Failed to fetch RAM usage", "Successfully fetching RAM usage again",
                                     62)
        return 0