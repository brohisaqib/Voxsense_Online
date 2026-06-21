"""
VoxSense — routes/websocket_route.py
WebSocket endpoint — Optimized, singleton modules
"""

import asyncio
import json
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger

from modules.ai_brain import AIBrain
from modules.pc_controller import PCController
from modules.browser_controller import BrowserController
from modules.screen_reader import ScreenReader
from modules.memory import MemoryManager

router = APIRouter()

# ── Singletons — ek baar bante hain, baar baar nahi ──────────────────────────
_brain   = AIBrain()
_pc      = PCController()
_browser = BrowserController()
_screen  = ScreenReader()

# ── Lazy singletons — sirf zaroorat pe load hote hain ────────────────────────
_yt_ctrl   = None
_wa_ctrl   = None
_sp_ctrl   = None
_wx_svc    = None
_news_svc  = None
_sys_info  = None
_reminder  = None
_pdf       = None
_translator= None


def _yt():
    global _yt_ctrl
    if _yt_ctrl is None:
        from modules.youtube_controller import YouTubeController
        _yt_ctrl = YouTubeController(_browser)
    return _yt_ctrl


def _wa():
    global _wa_ctrl
    if _wa_ctrl is None:
        from modules.whatsapp_desktop import WhatsAppDesktop
        _wa_ctrl = WhatsAppDesktop()
    return _wa_ctrl


def _spotify():
    global _sp_ctrl
    if _sp_ctrl is None:
        from modules.spotify_controller import SpotifyController
        _sp_ctrl = SpotifyController()
    return _sp_ctrl


def _weather():
    global _wx_svc
    if _wx_svc is None:
        from modules.weather import WeatherService
        _wx_svc = WeatherService()
    return _wx_svc


def _news():
    global _news_svc
    if _news_svc is None:
        from modules.news import NewsService
        _news_svc = NewsService()
    return _news_svc


def _sysinfo():
    global _sys_info
    if _sys_info is None:
        from modules.system_info import SystemInfo
        _sys_info = SystemInfo()
    return _sys_info


def _reminders():
    global _reminder
    if _reminder is None:
        from modules.reminder import ReminderService
        _reminder = ReminderService()
    return _reminder


def _pdfreader():
    global _pdf
    if _pdf is None:
        from modules.pdf_reader import PDFReader
        _pdf = PDFReader()
    return _pdf


def _trans():
    global _translator
    if _translator is None:
        from modules.translator import TranslatorService
        _translator = TranslatorService()
    return _translator


# ─── Intent Dispatcher ───────────────────────────────────────────────────────

async def dispatch(intent_data: dict, mem: MemoryManager) -> str:
    intent      = intent_data.get("intent", "unknown")
    params      = intent_data.get("params", {})
    ai_response = intent_data.get("response_to_user", "Done.")

    try:

        # ── Time / Date ──────────────────────────────────────
        if intent == "get_time":
            return await _pc.get_time()

        if intent == "get_date":
            return await _pc.get_date()

        # ── Apps ─────────────────────────────────────────────
        if intent == "open_app":
            app_name = params.get("app_name", "")
            if not app_name:
                return "Which application would you like me to open?"
            return await _pc.open_app(app_name)

        if intent == "close_app":
            return await _pc.close_app(params.get("app_name", ""))

        if intent == "list_open_apps":
            return await _pc.list_open_apps()

        # ── Screen ───────────────────────────────────────────
        if intent == "read_screen":
            return await _screen.describe_screen()

        # ── Volume ───────────────────────────────────────────
        if intent == "volume_up":
            return await _pc.volume_up()

        if intent == "volume_down":
            return await _pc.volume_down()

        if intent == "volume_mute":
            return await _pc.volume_mute()

        # ── Screenshot ───────────────────────────────────────
        if intent == "screenshot":
            return await _pc.take_screenshot()

        # ── YouTube Play ─────────────────────────────────────
        if intent == "youtube_play":
            query = params.get("search_query", "")
            if not query:
                return "What would you like me to play on YouTube?"
            return await _browser.youtube_play(query)

        # ── Instagram ────────────────────────────────────────
        if intent == "instagram_read":
            return await _browser.instagram_read_dm(params.get("contact_name", ""))

        # ── Files & Folders ──────────────────────────────────
        if intent == "file_open":
            return await _pc.open_file(params.get("file_name", ""))

        if intent == "file_search":
            return await _pc.search_file(params.get("file_name", ""))

        if intent == "folder_list":
            return await _pc.list_folder(params.get("folder_path", "desktop"))

        if intent == "create_folder":
            return await _pc.create_folder(params.get("folder_path", ""))

        # ── Keyboard / Mouse ─────────────────────────────────
        if intent == "type_text":
            text = params.get("text_to_type", "")
            if not text:
                return "What text would you like me to type?"
            return await _pc.type_text(text)

        if intent == "press_key":
            key = params.get("key_combination", "")
            if not key:
                return "Which key combination should I press?"
            return await _pc.press_key(key)

        if intent == "scroll":
            direction = params.get("direction", "down")
            amount    = int(params.get("amount", 3))
            return await _pc.scroll(direction, amount)

        if intent == "click_button":
            return await _pc.click_button(params.get("app_name", ""))

        # ── Clipboard ────────────────────────────────────────
        if intent == "clipboard_read":
            return await _pc.read_clipboard()

        if intent == "clipboard_write":
            text = params.get("text_to_type", "")
            if not text:
                return "What would you like me to copy to clipboard?"
            return await _pc.write_clipboard(text)

        # ── Browser ──────────────────────────────────────────
        if intent == "open_url":
            url = params.get("url", "")
            if not url:
                return "Which website would you like me to open?"
            return await _browser.open_url(url)

        # ── System ───────────────────────────────────────────
        if intent == "lock_pc":
            return await _pc.lock_pc()

        if intent == "sleep_pc":
            return await _pc.sleep_pc()

        if intent == "restart_pc":
            return await _pc.restart_pc()

        if intent == "shutdown_pc":
            return await _pc.shutdown_pc()

        # ── Email ─────────────────────────────────────────────
        if intent in ("email_read", "email_send"):
            return await _browser.open_url("https://mail.google.com")

        # ── Weather ───────────────────────────────────────────
        if intent == "get_weather":
            city = params.get("search_query", "Karachi")
            if not city:
                city = "Karachi"
            return await _weather().get_weather(city)

        # ── News ──────────────────────────────────────────────
        if intent == "get_news":
            topic = params.get("search_query", "").lower()
            ns = _news()
            if "pakistan" in topic:
                return await ns.get_pakistan_news()
            elif "world" in topic or "international" in topic:
                return await ns.get_world_news()
            elif "tech" in topic:
                return await ns.get_tech_news()
            elif "sport" in topic:
                return await ns.get_sports_news()
            else:
                return await ns.get_all_news()

        # ── System Info ───────────────────────────────────────
        if intent == "get_battery":
            return await _sysinfo().get_battery()

        if intent == "get_ram":
            return await _sysinfo().get_ram()

        if intent == "get_wifi":
            return await _sysinfo().get_wifi()

        if intent == "get_cpu":
            return await _sysinfo().get_cpu()

        if intent == "empty_recycle_bin":
            return await _sysinfo().empty_recycle_bin()

        if intent == "internet_speed":
            return await _sysinfo().check_internet_speed()

        # ── Translation ───────────────────────────────────────
        if intent == "translate":
            text = params.get("text_to_type", "")
            lang = params.get("search_query", "ur")
            if not text:
                return "What text would you like me to translate?"
            return await _trans().translate(text, lang)

        # ── PDF Reader ────────────────────────────────────────
        if intent == "read_pdf":
            file_name = params.get("file_name", "")
            if not file_name:
                return "Which PDF file would you like me to read?"
            return await _pdfreader().read_pdf(file_name)

        # ── Reminders ─────────────────────────────────────────
        if intent == "set_reminder":
            try:
                mins = int(float(params.get("volume_level", 5)))
            except Exception:
                mins = 5
            msg = params.get("message_text", "") or params.get("text_to_type", "reminder")
            if not msg:
                return "What would you like me to remind you about?"
            return await _reminders().set_reminder(msg, mins, msg)

        if intent == "list_reminders":
            return await _reminders().list_reminders()

        # ── Spotify ───────────────────────────────────────────
        if intent == "spotify_play_pause":
            return await _spotify().play_pause()

        if intent == "spotify_next":
            return await _spotify().next_track()

        if intent == "spotify_prev":
            return await _spotify().prev_track()

        # ── YouTube Controller ────────────────────────────────
        if intent == "yt_play_pause":
            return await _yt().play_pause()

        if intent == "yt_pause":
            return await _yt().pause()

        if intent == "yt_play":
            return await _yt().play()

        if intent == "yt_next":
            return await _yt().next_video()

        if intent == "yt_previous":
            return await _yt().previous_video()

        if intent == "yt_volume_up":
            return await _yt().volume_up()

        if intent == "yt_volume_down":
            return await _yt().volume_down()

        if intent == "yt_mute":
            return await _yt().mute()

        if intent == "yt_fullscreen":
            return await _yt().fullscreen()

        if intent == "yt_skip_forward":
            secs = int(params.get("volume_level", 10))
            return await _yt().skip_forward(secs)

        if intent == "yt_skip_backward":
            secs = int(params.get("volume_level", 10))
            return await _yt().skip_backward(secs)

        if intent == "yt_speed_up":
            return await _yt().speed_up()

        if intent == "yt_speed_down":
            return await _yt().speed_down()

        if intent == "yt_normal_speed":
            return await _yt().normal_speed()

        if intent == "yt_what_playing":
            return await _yt().what_is_playing()

        if intent == "yt_like":
            return await _yt().like_video()

        if intent == "yt_subscribe":
            return await _yt().subscribe()

        # ── WhatsApp Desktop ──────────────────────────────────
        if intent == "wa_open":
            return await _wa().open_whatsapp()

        if intent == "wa_close":
            return await _wa().close_whatsapp()

        if intent == "wa_open_chat":
            contact = params.get("contact_name", "")
            if not contact:
                return "Who would you like to open chat with?"
            return await _wa().open_chat(contact)

        if intent == "wa_send":
            contact = params.get("contact_name", "")
            message = params.get("message_text", "")
            if not contact:
                return "Who would you like to message?"
            if not message:
                return "What message would you like to send?"
            return await _wa().send_message(contact, message)

        if intent == "wa_read":
            return await _wa().read_messages(params.get("contact_name", ""))

        if intent == "wa_unread":
            return await _wa().show_unread()

        if intent == "wa_call":
            contact = params.get("contact_name", "")
            if not contact:
                return "Who would you like to call?"
            return await _wa().voice_call(contact)

        if intent == "wa_video_call":
            contact = params.get("contact_name", "")
            if not contact:
                return "Who would you like to video call?"
            return await _wa().video_call(contact)

        if intent == "wa_end_call":
            return await _wa().end_call()

        if intent == "wa_go_back":
            return await _wa().go_back()

        if intent == "wa_help":
            return await _wa().help_commands()

        # ── Unknown ───────────────────────────────────────────
        return ai_response

    except Exception as e:
        logger.error(f"Dispatch error [{intent}]: {e}")
        return "Sorry, something went wrong. Please try again."


# ─── WebSocket Handler ───────────────────────────────────────────────────────

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    client = websocket.client
    logger.info(f"WebSocket connected: {client}")

    mem = MemoryManager()
    await mem.init_db()

    pending_confirm: Optional[dict] = None

    try:
        while True:
            raw = await websocket.receive_text()

            # ── Parse ─────────────────────────────────────────
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "response": "Invalid message format.",
                    "done": True
                })
                continue

            transcript = data.get("transcript", "").strip()
            if not transcript:
                continue

            logger.info(f"WS received: {transcript!r}")

            # ── Confirmation flow ─────────────────────────────
            if pending_confirm:
                confirm_text = transcript.lower()
                if any(w in confirm_text for w in ("yes", "confirm", "okay", "ok", "sure", "proceed", "do it")):
                    result = await dispatch(pending_confirm, mem)
                    pending_confirm = None
                    await mem.save_turn("assistant", result)
                    await websocket.send_json({
                        "response": result,
                        "intent":   "confirmed",
                        "done":     True
                    })
                else:
                    pending_confirm = None
                    await mem.save_turn("assistant", "Action cancelled.")
                    await websocket.send_json({
                        "response": "Action cancelled.",
                        "done":     True
                    })
                continue

            # ── Save user turn + get history (parallel) ───────
            await mem.save_turn("user", transcript)
            history = await mem.get_recent(6)

            # ── AI process ────────────────────────────────────
            intent_data   = await _brain.process(transcript, history)
            intent        = intent_data.get("intent", "unknown")
            needs_confirm = intent_data.get("needs_confirmation", False)
            confirm_msg   = intent_data.get("confirmation_message", "")

            # ── Confirmation required ─────────────────────────
            if needs_confirm and confirm_msg:
                pending_confirm  = intent_data
                confirm_question = confirm_msg or f"Are you sure you want to {intent.replace('_', ' ')}?"
                await websocket.send_json({
                    "type":    "confirm_request",
                    "message": confirm_question,
                    "done":    False,
                })
                continue

            # ── Execute action ────────────────────────────────
            result = await dispatch(intent_data, mem)
            await mem.save_turn("assistant", result, intent=intent)

            await websocket.send_json({
                "response": result,
                "intent":   intent,
                "done":     True,
            })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {client}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json({
                "type":     "error",
                "response": "Sorry, a server error occurred. Please try again.",
                "done":     True,
            })
        except Exception:
            pass