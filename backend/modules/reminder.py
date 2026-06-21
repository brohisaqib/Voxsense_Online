"""
VoxSense — modules/reminder.py
Reminder system with Windows notification + Voice alert
"""
import asyncio
from datetime import datetime, timedelta
from loguru import logger


class ReminderService:
    _reminders = []

    async def set_reminder(self, text: str, minutes: int = 5, message: str = "") -> str:
        try:
            if minutes <= 0:
                minutes = 5

            remind_msg = message if message else text
            remind_at  = datetime.now() + timedelta(minutes=minutes)

            self._reminders.append({
                "time":    remind_at,
                "message": remind_msg
            })

            # Fire reminder after delay
            asyncio.create_task(self._fire_reminder(minutes * 60, remind_msg))

            time_str = remind_at.strftime("%I:%M %p")
            return f"Reminder set for {minutes} minutes from now at {time_str}. I will remind you: {remind_msg}"

        except Exception as e:
            logger.error(f"Reminder set error: {e}")
            return f"Could not set reminder. {e}"

    async def _fire_reminder(self, seconds: int, message: str):
        """Wait, then speak + show Windows notification."""
        try:
            await asyncio.sleep(seconds)
            logger.info(f"Reminder firing: {message}")

            # 1 — Windows Toast Notification
            try:
                from win10toast import ToastNotifier
                toaster = ToastNotifier()
                toaster.show_toast(
                    "VoxSense Reminder",
                    message,
                    duration=10,
                    threaded=True
                )
            except ImportError:
                # Fallback — Windows balloon via ctypes
                try:
                    import ctypes
                    ctypes.windll.user32.MessageBoxW(
                        0,
                        message,
                        "VoxSense Reminder",
                        0x40
                    )
                except Exception:
                    pass
            except Exception as e:
                logger.error(f"Notification error: {e}")

            # 2 — Voice Alert via Windows TTS
            try:
                import subprocess
                ps_cmd = f'Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; $s.Rate = 0; $s.Speak("Reminder: {message}")'
                subprocess.Popen(
                    ["powershell", "-Command", ps_cmd],
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            except Exception as e:
                logger.error(f"Voice alert error: {e}")

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Reminder fire error: {e}")

    async def list_reminders(self) -> str:
        try:
            now    = datetime.now()
            active = [r for r in self._reminders if r["time"] > now]

            if not active:
                return "You have no active reminders."

            lines = []
            for r in active[:5]:
                mins = int((r["time"] - now).total_seconds() / 60)
                time_str = r["time"].strftime("%I:%M %p")
                lines.append(f"{r['message']} at {time_str} ({mins} minutes left)")

            return "Your reminders: " + ". Next: ".join(lines)

        except Exception as e:
            return f"Could not list reminders. {e}"