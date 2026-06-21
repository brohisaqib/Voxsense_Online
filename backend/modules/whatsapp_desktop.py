"""
VoxSense — modules/whatsapp_desktop.py
Complete WhatsApp Desktop voice control for blind users.
Uses native Windows WhatsApp app via deep links + UI automation.
Every action has voice feedback — no visual interaction needed.
"""
import asyncio
import subprocess
import time
import os
from pathlib import Path
from loguru import logger


class WhatsAppDesktop:
    """
    Controls WhatsApp Desktop app via:
    1. Deep links (whatsapp://)
    2. Windows UI Automation (uiautomation)
    3. pywinauto as fallback
    """

    WHATSAPP_PATHS = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "WhatsApp" / "WhatsApp.exe",
        Path(os.environ.get("PROGRAMFILES", "")) / "WindowsApps" / "WhatsApp",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "WhatsApp" / "WhatsApp.exe",
    ]

    def __init__(self):
        self._wa_window = None

    # ── TTS Helper ────────────────────────────────────────────────
    async def _speak(self, text: str):
        """Speak text via Windows TTS immediately."""
        try:
            clean = text.replace("'", "").replace('"', "")
            ps = f"Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; $s.Rate = 0; $s.Speak('{clean}')"
            subprocess.Popen(
                ["powershell", "-Command", ps],
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        except Exception as e:
            logger.error(f"TTS error: {e}")

    # ── Find WhatsApp window ───────────────────────────────────────
    def _find_wa_window(self):
        try:
            import uiautomation as auto
            win = auto.WindowControl(searchDepth=1, Name="WhatsApp")
            if win.Exists(2):
                return win
            # Try partial name
            win2 = auto.WindowControl(searchDepth=1, SubName="WhatsApp")
            if win2.Exists(2):
                return win2
        except Exception as e:
            logger.error(f"Find window error: {e}")
        return None

    # ── Open WhatsApp ─────────────────────────────────────────────
    async def open_whatsapp(self) -> str:
        try:
            await self._speak("Opening WhatsApp")

            # Try deep link first
            try:
                subprocess.Popen(
                    'start whatsapp://',
                    shell=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                await asyncio.sleep(3)
                win = self._find_wa_window()
                if win:
                    win.SetFocus()
                    return "WhatsApp is now open."
            except Exception:
                pass

            # Try launching exe directly
            for path in self.WHATSAPP_PATHS:
                if path.exists():
                    subprocess.Popen(str(path))
                    await asyncio.sleep(3)
                    return "WhatsApp is now open."

            # Try Windows Store app
            subprocess.Popen(
                'start ms-windows-store://pdp/?productid=9NKSQGP7F2NH',
                shell=True
            )
            return "Opening WhatsApp from Store."

        except Exception as e:
            logger.error(f"Open WhatsApp error: {e}")
            return "Could not open WhatsApp. Please make sure it is installed."

    # ── Close WhatsApp ────────────────────────────────────────────
    async def close_whatsapp(self) -> str:
        try:
            await self._speak("Closing WhatsApp")
            import psutil
            for proc in psutil.process_iter(['name']):
                if 'whatsapp' in proc.info['name'].lower():
                    proc.terminate()
            return "WhatsApp has been closed."
        except Exception as e:
            return f"Could not close WhatsApp. {e}"

    # ── Bring WhatsApp to front ────────────────────────────────────
    async def _focus_whatsapp(self) -> bool:
        try:
            win = self._find_wa_window()
            if win:
                win.SetFocus()
                await asyncio.sleep(0.5)
                return True
            # WhatsApp not open — open it
            await self.open_whatsapp()
            await asyncio.sleep(3)
            win = self._find_wa_window()
            if win:
                win.SetFocus()
                return True
            return False
        except Exception as e:
            logger.error(f"Focus error: {e}")
            return False

    # ── Search contact ─────────────────────────────────────────────
    async def _search_contact(self, name: str) -> bool:
        """Search for a contact in WhatsApp search box."""
        try:
            import uiautomation as auto
            win = self._find_wa_window()
            if not win:
                return False

            win.SetFocus()
            await asyncio.sleep(0.3)

            # Press Ctrl+F or click search
            import keyboard as kb
            kb.send("ctrl+f")
            await asyncio.sleep(0.8)

            # Type contact name
            import pyautogui
            pyautogui.hotkey('ctrl', 'a')
            await asyncio.sleep(0.2)
            pyautogui.typewrite(name, interval=0.05)
            await asyncio.sleep(1.5)

            # Press Enter to open first result
            kb.send("enter")
            await asyncio.sleep(1.0)
            return True

        except Exception as e:
            logger.error(f"Search contact error: {e}")
            return False

    # ── Open chat ─────────────────────────────────────────────────
    async def open_chat(self, contact: str) -> str:
        try:
            await self._speak(f"Opening chat with {contact}")
            focused = await self._focus_whatsapp()
            if not focused:
                return "Could not open WhatsApp. Please make sure it is installed."

            found = await self._search_contact(contact)
            if found:
                return f"Chat with {contact} is now open."
            else:
                await self._speak(f"Contact {contact} not found. Please try again.")
                return f"Contact {contact} not found. Please try again."

        except Exception as e:
            logger.error(f"Open chat error: {e}")
            return f"Could not open chat with {contact}."

    # ── Send message ──────────────────────────────────────────────
    async def send_message(self, contact: str, message: str) -> str:
        try:
            await self._speak(f"Sending message to {contact}")

            focused = await self._focus_whatsapp()
            if not focused:
                return "Could not open WhatsApp."

            found = await self._search_contact(contact)
            if not found:
                await self._speak(f"Contact {contact} not found. Please try again.")
                return f"Contact {contact} not found."

            await asyncio.sleep(0.5)

            # Type message in chat input
            import pyautogui
            import keyboard as kb

            # Click message box area
            pyautogui.hotkey('ctrl', 'shift', 'u')  # Some WA versions
            await asyncio.sleep(0.3)
            kb.send("escape")
            await asyncio.sleep(0.3)

            # Type message
            pyautogui.typewrite(message, interval=0.04)
            await asyncio.sleep(0.5)
            kb.send("enter")
            await asyncio.sleep(0.5)

            await self._speak(f"Message sent to {contact}.")
            return f"Message sent to {contact}: {message}"

        except Exception as e:
            logger.error(f"Send message error: {e}")
            await self._speak("Could not send message. Please try again.")
            return f"Could not send message to {contact}."

    # ── Read messages ─────────────────────────────────────────────
    async def read_messages(self, contact: str = "") -> str:
        try:
            if contact:
                await self._speak(f"Reading messages from {contact}")
            else:
                await self._speak("Reading your unread messages")

            focused = await self._focus_whatsapp()
            if not focused:
                return "Could not open WhatsApp."

            if contact:
                found = await self._search_contact(contact)
                if not found:
                    await self._speak(f"Contact {contact} not found.")
                    return f"Contact {contact} not found."
                await asyncio.sleep(1)

            # Extract messages via UI automation
            try:
                import uiautomation as auto
                win = self._find_wa_window()
                if not win:
                    return "WhatsApp window not found."

                # Get all text elements in chat area
                messages = []
                try:
                    # Find message list
                    chat_area = win.ListControl(searchDepth=6)
                    if chat_area.Exists(2):
                        items = chat_area.GetChildren()
                        for item in items[-10:]:  # Last 10 messages
                            txt = item.Name.strip()
                            if txt and len(txt) > 1:
                                messages.append(txt)
                except Exception:
                    pass

                # Fallback — get window text
                if not messages:
                    all_text = win.Name
                    if all_text:
                        messages = [all_text]

                if messages:
                    result = f"Last messages" + (f" from {contact}" if contact else "") + ": " + ". ".join(messages[-5:])
                    await self._speak(result)
                    return result
                else:
                    msg = f"No messages found" + (f" from {contact}" if contact else "")
                    await self._speak(msg)
                    return msg

            except Exception as e:
                logger.error(f"Read messages UI error: {e}")
                return "Could not read messages from WhatsApp window."

        except Exception as e:
            logger.error(f"Read messages error: {e}")
            return f"Could not read messages."

    # ── Show unread ───────────────────────────────────────────────
    async def show_unread(self) -> str:
        try:
            await self._speak("Checking for unread messages")
            focused = await self._focus_whatsapp()
            if not focused:
                return "Could not open WhatsApp."

            try:
                import uiautomation as auto
                win = self._find_wa_window()
                if not win:
                    return "WhatsApp not open."

                # Find unread badge elements
                unread_contacts = []
                try:
                    # Search for notification badges
                    badges = []
                    def find_badges(ctrl, depth=0):
                        if depth > 8:
                            return
                        name = ctrl.Name or ""
                        if "unread" in name.lower() or (name.isdigit() and int(name) > 0):
                            parent = ctrl.GetParentControl()
                            if parent:
                                pname = parent.Name.strip()
                                if pname and pname not in unread_contacts:
                                    unread_contacts.append(pname)
                        for child in ctrl.GetChildren():
                            find_badges(child, depth + 1)

                    find_badges(win)
                except Exception:
                    pass

                if unread_contacts:
                    names = ", ".join(unread_contacts[:5])
                    result = f"You have unread messages from: {names}"
                    await self._speak(result)
                    return result
                else:
                    msg = "No unread messages found."
                    await self._speak(msg)
                    return msg

            except Exception as e:
                logger.error(f"Show unread error: {e}")
                return "Could not check unread messages."

        except Exception as e:
            return f"Error checking unread: {e}"

    # ── Voice call ────────────────────────────────────────────────
    async def voice_call(self, contact: str) -> str:
        try:
            await self._speak(f"Calling {contact} on WhatsApp")

            # Try deep link first
            try:
                import urllib.parse
                encoded = urllib.parse.quote(contact)
                subprocess.Popen(
                    f'start whatsapp://call?phone={encoded}',
                    shell=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                await asyncio.sleep(2)
                await self._speak(f"Calling {contact}. Please wait.")
                return f"Calling {contact} on WhatsApp."
            except Exception:
                pass

            # Fallback — UI automation
            focused = await self._focus_whatsapp()
            if not focused:
                return "Could not open WhatsApp."

            found = await self._search_contact(contact)
            if not found:
                await self._speak(f"Contact {contact} not found.")
                return f"Contact {contact} not found."

            await asyncio.sleep(0.5)

            # Click voice call button
            try:
                import uiautomation as auto
                win = self._find_wa_window()
                if win:
                    call_btn = win.ButtonControl(searchDepth=8, Name="Voice call")
                    if not call_btn.Exists(2):
                        call_btn = win.ButtonControl(searchDepth=8, SubName="call")
                    if call_btn.Exists(2):
                        call_btn.Click()
                        await asyncio.sleep(1)
                        await self._speak(f"Calling {contact}. Please wait.")
                        return f"Calling {contact} on WhatsApp."
            except Exception as e:
                logger.error(f"Call button error: {e}")

            await self._speak(f"Could not find call button for {contact}.")
            return f"Could not place call to {contact}."

        except Exception as e:
            logger.error(f"Voice call error: {e}")
            await self._speak("Could not make the call. Please try again.")
            return f"Could not call {contact}."

    # ── Video call ────────────────────────────────────────────────
    async def video_call(self, contact: str) -> str:
        try:
            await self._speak(f"Starting video call with {contact}")

            focused = await self._focus_whatsapp()
            if not focused:
                return "Could not open WhatsApp."

            found = await self._search_contact(contact)
            if not found:
                await self._speak(f"Contact {contact} not found.")
                return f"Contact {contact} not found."

            await asyncio.sleep(0.5)

            try:
                import uiautomation as auto
                win = self._find_wa_window()
                if win:
                    vid_btn = win.ButtonControl(searchDepth=8, Name="Video call")
                    if not vid_btn.Exists(2):
                        vid_btn = win.ButtonControl(searchDepth=8, SubName="video")
                    if vid_btn.Exists(2):
                        vid_btn.Click()
                        await asyncio.sleep(1)
                        await self._speak(f"Video calling {contact}.")
                        return f"Video calling {contact} on WhatsApp."
            except Exception as e:
                logger.error(f"Video call button error: {e}")

            await self._speak(f"Could not start video call with {contact}.")
            return f"Could not video call {contact}."

        except Exception as e:
            logger.error(f"Video call error: {e}")
            return f"Could not video call {contact}."

    # ── End call ──────────────────────────────────────────────────
    async def end_call(self) -> str:
        try:
            await self._speak("Ending call")

            import keyboard as kb
            # WhatsApp Desktop end call shortcut
            kb.send("ctrl+shift+e")
            await asyncio.sleep(0.5)

            # Try UI button
            try:
                import uiautomation as auto
                win = self._find_wa_window()
                if win:
                    end_btn = win.ButtonControl(searchDepth=8, Name="End call")
                    if not end_btn.Exists(1):
                        end_btn = win.ButtonControl(searchDepth=8, SubName="end")
                    if end_btn.Exists(1):
                        end_btn.Click()
            except Exception:
                pass

            await self._speak("Call ended.")
            return "Call has been ended."

        except Exception as e:
            return f"Could not end call. {e}"

    # ── Go back ───────────────────────────────────────────────────
    async def go_back(self) -> str:
        try:
            import keyboard as kb
            focused = await self._focus_whatsapp()
            if focused:
                kb.send("alt+left")
                await asyncio.sleep(0.3)
                await self._speak("Going back.")
                return "Went back in WhatsApp."
            return "WhatsApp is not open."
        except Exception as e:
            return f"Could not go back. {e}"

    # ── Help ──────────────────────────────────────────────────────
    async def help_commands(self) -> str:
        help_text = (
            "Here are all WhatsApp voice commands. "
            "Say: Open WhatsApp, to launch the app. "
            "Say: Read messages, to hear unread messages. "
            "Say: Read messages from Ali, to hear messages from a specific person. "
            "Say: Send message to Ali hello, to send a message. "
            "Say: Open chat with Sara, to open a chat. "
            "Say: Call Ali, to make a voice call. "
            "Say: Video call Ali, to make a video call. "
            "Say: End call, to hang up. "
            "Say: Show unread messages, to hear who messaged you. "
            "Say: Who messaged me, same as above. "
            "Say: Go back, to navigate back. "
            "Say: Close WhatsApp, to close the app."
        )
        await self._speak(help_text)
        return help_text