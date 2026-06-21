import os
import ctypes
from datetime import datetime
from pathlib import Path
from loguru import logger


class SystemActions:
    async def get_time(self) -> str:
        return f"The time is {datetime.now().strftime('%I:%M %p')}"

    async def get_date(self) -> str:
        return f"Today is {datetime.now().strftime('%A, %B %d %Y')}"

    async def take_screenshot(self) -> str:
        try:
            import mss
            path = Path.home() / "Desktop" / "screenshot.png"
            with mss.mss() as s:
                s.shot(output=str(path))
            return "Screenshot saved to Desktop."
        except Exception as e:
            return f"Screenshot failed. {e}"

    async def lock_pc(self) -> str:
        ctypes.windll.user32.LockWorkStation()
        return "PC locked."

    async def sleep_pc(self) -> str:
        os.system("rundll32 powrprof.dll,SetSuspendState 0,1,0")
        return "Going to sleep."

    async def restart_pc(self) -> str:
        os.system("shutdown /r /t 5")
        return "Restarting in 5 seconds."

    async def shutdown_pc(self) -> str:
        os.system("shutdown /s /t 5")
        return "Shutting down in 5 seconds."