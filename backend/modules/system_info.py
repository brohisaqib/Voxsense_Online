"""VoxSense — modules/system_info.py"""
import psutil
import socket
from loguru import logger


class SystemInfo:
    async def get_battery(self) -> str:
        try:
            b = psutil.sensors_battery()
            if b is None:
                return "No battery detected. This is a desktop PC."
            status = "charging" if b.power_plugged else "not charging"
            return f"Battery is at {int(b.percent)} percent and {status}."
        except Exception as e:
            return f"Could not get battery info. {e}"

    async def get_ram(self) -> str:
        try:
            r = psutil.virtual_memory()
            used = round(r.used / (1024**3), 1)
            total = round(r.total / (1024**3), 1)
            percent = int(r.percent)
            return f"RAM usage is {percent} percent. {used} GB used out of {total} GB total."
        except Exception as e:
            return f"Could not get RAM info. {e}"

    async def get_wifi(self) -> str:
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            return "Internet is connected."
        except OSError:
            return "Internet is not connected."

    async def get_cpu(self) -> str:
        try:
            cpu = psutil.cpu_percent(interval=1)
            return f"CPU usage is {int(cpu)} percent."
        except Exception as e:
            return f"Could not get CPU info. {e}"

    async def empty_recycle_bin(self) -> str:
        try:
            import winshell
            winshell.recycle_bin().empty(confirm=False, show_progress=False, sound=False)
            return "Recycle Bin has been emptied."
        except Exception as e:
            return f"Could not empty Recycle Bin. {e}"

    async def check_internet_speed(self) -> str:
        try:
            import speedtest
            st = speedtest.Speedtest()
            down = round(st.download() / 1_000_000, 1)
            up = round(st.upload() / 1_000_000, 1)
            return f"Download speed is {down} Mbps. Upload speed is {up} Mbps."
        except Exception as e:
            return f"Could not test speed. Install speedtest-cli first."