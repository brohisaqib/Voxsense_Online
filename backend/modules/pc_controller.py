"""
VoxSense — modules/pc_controller.py
Windows PC automation: apps, volume, keyboard, files, clipboard, system actions.
All functions are async-compatible wrappers around sync Windows APIs.
"""

import asyncio
import ctypes
import datetime
import os
import subprocess
import winreg
from pathlib import Path
from typing import Optional

import psutil
import pyperclip
import pyautogui
import keyboard
import mss
from PIL import Image
from loguru import logger


# ─── Helpers ─────────────────────────────────────

def _run_sync(func, *args, **kwargs):
    """Run a sync function in the default thread pool."""
    loop = asyncio.get_event_loop()
    return loop.run_in_executor(None, lambda: func(*args, **kwargs))


def _find_exe_from_registry(name: str) -> Optional[str]:
    """Search common registry paths for an installed application EXE."""
    keys = [
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths",
    ]
    name_lower = name.lower()
    for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        for key_path in keys:
            try:
                with winreg.OpenKey(hive, key_path) as base:
                    i = 0
                    while True:
                        try:
                            sub_name = winreg.EnumKey(base, i)
                            if name_lower in sub_name.lower():
                                with winreg.OpenKey(base, sub_name) as sub:
                                    val, _ = winreg.QueryValueEx(sub, "")
                                    if val and Path(val).exists():
                                        return val
                        except OSError:
                            break
                        i += 1
            except OSError:
                continue
    return None


# Common well-known app shortcuts for convenience
KNOWN_APPS: dict[str, str] = {
    "chrome":     "chrome.exe",
    "google chrome": "chrome.exe",
    "edge":       "msedge.exe",
    "microsoft edge": "msedge.exe",
    "firefox":    "firefox.exe",
    "notepad":    "notepad.exe",
    "calculator": "calc.exe",
    "calc":       "calc.exe",
    "word":       "WINWORD.EXE",
    "excel":      "EXCEL.EXE",
    "powerpoint": "POWERPNT.EXE",
    "outlook":    "OUTLOOK.EXE",
    "paint":      "mspaint.exe",
    "explorer":   "explorer.exe",
    "file explorer": "explorer.exe",
    "task manager": "taskmgr.exe",
    "vlc":        "vlc.exe",
    "spotify":    "Spotify.exe",
    "discord":    "Discord.exe",
    "zoom":       "Zoom.exe",
    "teams":      "Teams.exe",
    "microsoft teams": "Teams.exe",
    "skype":      "Skype.exe",
    "snipping tool": "SnippingTool.exe",
}


class PCController:
    """Controls Windows PC: apps, volume, keys, files, clipboard, system."""

    # ─── APPLICATIONS ────────────────────────────

    async def open_app(self, name: str) -> str:
        """Open an application by name."""
        try:
            name_clean = name.strip().lower()
            exe = KNOWN_APPS.get(name_clean)

            # Fallback: registry search
            if not exe:
                exe = await _run_sync(_find_exe_from_registry, name_clean)

            if exe:
                await _run_sync(subprocess.Popen, exe)
                logger.info(f"Opened app: {exe}")
                return f"Opening {name} now."
            else:
                # Last resort: try the name directly
                await _run_sync(subprocess.Popen, name_clean)
                return f"Attempting to open {name}."

        except FileNotFoundError:
            logger.warning(f"App not found: {name}")
            return f"I could not find the application called {name}. Please make sure it is installed."
        except Exception as e:
            logger.error(f"open_app error: {e}")
            return f"Sorry, I could not open {name}. {str(e)}"

    async def close_app(self, name: str) -> str:
        """Close a running application by process name or window title."""
        try:
            name_lower = name.strip().lower()
            closed = []
            for proc in psutil.process_iter(["name", "pid"]):
                proc_name = (proc.info.get("name") or "").lower()
                if name_lower in proc_name:
                    proc.terminate()
                    closed.append(proc.info["name"])

            if closed:
                logger.info(f"Closed processes: {closed}")
                return f"Closed {name}."
            else:
                return f"I could not find a running application called {name}."
        except Exception as e:
            logger.error(f"close_app error: {e}")
            return f"Sorry, I could not close {name}."

    async def list_open_apps(self) -> str:
        """Return names of currently running user-facing apps."""
        try:
            seen = set()
            apps = []
            for proc in psutil.process_iter(["name", "status"]):
                try:
                    n = proc.info.get("name", "")
                    if n and n not in seen and proc.status() == psutil.STATUS_RUNNING:
                        seen.add(n)
                        apps.append(n.replace(".exe", ""))
                except psutil.NoSuchProcess:
                    continue

            if apps:
                app_list = ", ".join(sorted(apps)[:20])
                return f"Currently running applications include: {app_list}."
            return "I could not detect any running applications."
        except Exception as e:
            logger.error(f"list_open_apps error: {e}")
            return "Sorry, I could not list open applications."

    # ─── VOLUME ──────────────────────────────────

    async def volume_up(self) -> str:
        try:
            await _run_sync(keyboard.send, "volume up")
            logger.info("Volume up")
            return "Volume increased."
        except Exception as e:
            logger.error(f"volume_up error: {e}")
            return "Sorry, I could not increase the volume."

    async def volume_down(self) -> str:
        try:
            await _run_sync(keyboard.send, "volume down")
            logger.info("Volume down")
            return "Volume decreased."
        except Exception as e:
            logger.error(f"volume_down error: {e}")
            return "Sorry, I could not decrease the volume."

    async def volume_mute(self) -> str:
        try:
            await _run_sync(keyboard.send, "volume mute")
            logger.info("Volume muted/unmuted")
            return "Volume toggled mute."
        except Exception as e:
            logger.error(f"volume_mute error: {e}")
            return "Sorry, I could not toggle mute."

    # ─── TIME & DATE ─────────────────────────────

    async def get_time(self) -> str:
        try:
            now = datetime.datetime.now()
            time_str = now.strftime("%I:%M %p")
            return f"The current time is {time_str}."
        except Exception as e:
            logger.error(f"get_time error: {e}")
            return "Sorry, I could not get the current time."

    async def get_date(self) -> str:
        try:
            now = datetime.datetime.now()
            date_str = now.strftime("%A, %B %d, %Y")
            return f"Today is {date_str}."
        except Exception as e:
            logger.error(f"get_date error: {e}")
            return "Sorry, I could not get today's date."

    # ─── SCREENSHOT ──────────────────────────────

    async def take_screenshot(self) -> str:
        try:
            desktop = Path.home() / "Desktop"
            desktop.mkdir(exist_ok=True)
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = desktop / f"screenshot_{ts}.png"

            with mss.mss() as sct:
                shot = sct.grab(sct.monitors[0])
                img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
                img.save(str(save_path))

            logger.info(f"Screenshot saved: {save_path}")
            return f"Screenshot saved to your Desktop as screenshot_{ts}.png."
        except Exception as e:
            logger.error(f"screenshot error: {e}")
            return "Sorry, I could not take a screenshot."

    # ─── SYSTEM ACTIONS ──────────────────────────

    async def lock_pc(self) -> str:
        try:
            ctypes.windll.user32.LockWorkStation()
            logger.info("PC locked")
            return "Your PC is now locked."
        except Exception as e:
            logger.error(f"lock_pc error: {e}")
            return "Sorry, I could not lock your PC."

    async def sleep_pc(self) -> str:
        try:
            await asyncio.sleep(2)
            os.system("rundll32 powrprof.dll,SetSuspendState 0,1,0")
            logger.info("PC going to sleep")
            return "Your PC is going to sleep now."
        except Exception as e:
            logger.error(f"sleep_pc error: {e}")
            return "Sorry, I could not put your PC to sleep."

    async def restart_pc(self) -> str:
        try:
            await asyncio.sleep(2)
            os.system("shutdown /r /t 5")
            logger.info("PC restarting")
            return "Your PC will restart in 5 seconds."
        except Exception as e:
            logger.error(f"restart_pc error: {e}")
            return "Sorry, I could not restart your PC."

    async def shutdown_pc(self) -> str:
        try:
            await asyncio.sleep(2)
            os.system("shutdown /s /t 5")
            logger.info("PC shutting down")
            return "Your PC will shut down in 5 seconds."
        except Exception as e:
            logger.error(f"shutdown_pc error: {e}")
            return "Sorry, I could not shut down your PC."

    # ─── KEYBOARD & MOUSE ────────────────────────

    async def type_text(self, text: str) -> str:
        try:
            await asyncio.sleep(0.5)  # Give focus time to settle
            pyautogui.typewrite(text, interval=0.05)
            logger.info(f"Typed: {text!r}")
            return f"Typed: {text}"
        except Exception as e:
            logger.error(f"type_text error: {e}")
            return f"Sorry, I could not type that text."

    async def press_key(self, keys: str) -> str:
        try:
            await _run_sync(keyboard.send, keys)
            logger.info(f"Key pressed: {keys}")
            return f"Pressed {keys}."
        except Exception as e:
            logger.error(f"press_key error: {e}")
            return f"Sorry, I could not press {keys}."

    async def scroll(self, direction: str = "down", amount: int = 3) -> str:
        try:
            scroll_amount = amount if direction.lower() == "up" else -amount
            pyautogui.scroll(scroll_amount)
            logger.info(f"Scrolled {direction} by {amount}")
            return f"Scrolled {direction}."
        except Exception as e:
            logger.error(f"scroll error: {e}")
            return "Sorry, I could not scroll."

    async def click_button(self, label: str) -> str:
        try:
            from pywinauto import Desktop  # type: ignore
            desktop = Desktop(backend="uia")
            ctrl = desktop.find_elements(
                lambda e: label.lower() in (e.window_text() or "").lower(),
                depth=5,
            )
            if ctrl:
                ctrl[0].click_input()
                return f"Clicked {label}."
            return f"Could not find a button labelled {label}."
        except Exception as e:
            logger.error(f"click_button error: {e}")
            return f"Sorry, I could not click {label}."

    # ─── FILES & FOLDERS ─────────────────────────

    async def open_file(self, file_name: str) -> str:
        try:
            search_dirs = [
                Path.home() / "Desktop",
                Path.home() / "Documents",
                Path.home() / "Downloads",
                Path.home(),
            ]
            for directory in search_dirs:
                matches = list(directory.glob(f"*{file_name}*"))
                if matches:
                    os.startfile(str(matches[0]))
                    logger.info(f"Opened file: {matches[0]}")
                    return f"Opened {matches[0].name}."
            return f"I could not find a file called {file_name} in your common folders."
        except Exception as e:
            logger.error(f"open_file error: {e}")
            return f"Sorry, I could not open {file_name}."

    async def search_file(self, file_name: str) -> str:
        try:
            search_dirs = [
                Path.home() / "Desktop",
                Path.home() / "Documents",
                Path.home() / "Downloads",
                Path.home(),
            ]
            found = []
            for directory in search_dirs:
                found.extend(directory.glob(f"**/*{file_name}*"))

            if found:
                names = [str(f) for f in found[:10]]
                names_str = ", ".join(names)
                return f"Found {len(found)} file(s) matching {file_name}: {names_str}."
            return f"No files found matching {file_name}."
        except Exception as e:
            logger.error(f"search_file error: {e}")
            return f"Sorry, I could not search for {file_name}."

    async def create_folder(self, folder_path: str) -> str:
        try:
            path = Path(folder_path).expanduser()
            path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created folder: {path}")
            return f"Created folder {path.name}."
        except Exception as e:
            logger.error(f"create_folder error: {e}")
            return f"Sorry, I could not create that folder."

    async def list_folder(self, folder_path: str) -> str:
        try:
            # Resolve common names
            aliases = {
                "downloads":  Path.home() / "Downloads",
                "documents":  Path.home() / "Documents",
                "desktop":    Path.home() / "Desktop",
                "pictures":   Path.home() / "Pictures",
                "music":      Path.home() / "Music",
                "videos":     Path.home() / "Videos",
                "":           Path.home() / "Desktop",
            }
            key = folder_path.strip().lower().rstrip("/\\")
            path = aliases.get(key, Path(folder_path).expanduser())

            if not path.exists():
                return f"The folder {folder_path} does not exist."

            items = list(path.iterdir())
            if not items:
                return f"The {path.name} folder is empty."

            names = [item.name for item in items[:30]]
            count = len(items)
            names_str = ", ".join(names)
            suffix = f" and {count - 30} more" if count > 30 else ""
            return f"Your {path.name} folder contains {count} item(s): {names_str}{suffix}."
        except Exception as e:
            logger.error(f"list_folder error: {e}")
            return "Sorry, I could not list that folder."

    # ─── CLIPBOARD ───────────────────────────────

    async def read_clipboard(self) -> str:
        try:
            text = pyperclip.paste()
            if text:
                preview = text[:200]
                return f"Your clipboard contains: {preview}"
            return "Your clipboard is empty."
        except Exception as e:
            logger.error(f"read_clipboard error: {e}")
            return "Sorry, I could not read your clipboard."

    async def write_clipboard(self, text: str) -> str:
        try:
            pyperclip.copy(text)
            logger.info(f"Clipboard written: {text[:50]!r}")
            return f"Copied to clipboard: {text[:50]}"
        except Exception as e:
            logger.error(f"write_clipboard error: {e}")
            return "Sorry, I could not write to your clipboard."