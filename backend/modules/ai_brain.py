"""
VoxSense — modules/ai_brain.py
AI Brain using Groq API — Optimized for speed
"""

import json
import os
from groq import AsyncGroq
from loguru import logger
from dotenv import load_dotenv

load_dotenv()


class AIBrain:
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            logger.warning("GROQ_API_KEY not set in .env")
        self.client = AsyncGroq(api_key=api_key)
        self.model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        self._prompt = self._build_system_prompt()
        logger.info(f"AI Brain ready — model: {self.model}")

    async def process(self, text: str, history: list) -> dict:
        raw = ""
        try:
            messages = [{"role": "system", "content": self._prompt}]

            for h in history[-6:]:
                role = h.get("role", "user")
                if role not in ("user", "assistant"):
                    role = "user"
                messages.append({"role": role, "content": h.get("text", "")})

            messages.append({"role": "user", "content": text})

            resp = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=150,
                temperature=0.0,
                stream=False,
            )

            raw = resp.choices[0].message.content.strip()
            raw = raw.replace("```json", "").replace("```", "").strip()

            # Extract JSON if extra text present
            start = raw.find("{")
            end   = raw.rfind("}") + 1
            if start != -1 and end > start:
                raw = raw[start:end]

            result = json.loads(raw)
            logger.info(f"Intent: {result.get('intent')} | Text: {text!r}")
            return result

        except json.JSONDecodeError:
            logger.error(f"JSON parse error — raw: {raw[:200]}")
            return self._fallback()
        except Exception as e:
            logger.error(f"AI brain error: {e}")
            return self._fallback()

    def _build_system_prompt(self) -> str:
        return (
            "You are VoxSense, a voice assistant for blind users on Windows PC.\n"
            "Return ONLY a JSON object. No explanation. No markdown. No extra text.\n\n"
            "Format:\n"
            '{"intent":"<intent>","params":{"app_name":"","search_query":"","contact_name":"",'
            '"message_text":"","file_name":"","folder_path":"","text_to_type":"",'
            '"key_combination":"","direction":"down","url":"","volume_level":""},'
            '"needs_confirmation":false,"confirmation_message":"","response_to_user":"<spoken reply>"}\n\n'
            "INTENTS:\n"
            "open_app,close_app,list_open_apps,read_screen,"
            "volume_up,volume_down,volume_mute,screenshot,"
            "get_time,get_date,"
            "youtube_play(search_query),whatsapp_send(contact_name,message_text),"
            "whatsapp_read(contact_name),instagram_read(contact_name),"
            "file_open(file_name),file_search(file_name),folder_list(folder_path),"
            "create_folder(folder_path),type_text(text_to_type),press_key(key_combination),"
            "scroll(direction:up/down),click_button(app_name),"
            "clipboard_read,clipboard_write(text_to_type),open_url(url),"
            "lock_pc*,sleep_pc*,restart_pc*,shutdown_pc*,"
            "email_read,email_send,"
            "get_weather(search_query=city),get_news(search_query=topic),"
            "get_battery,get_ram,get_wifi,get_cpu,"
            "empty_recycle_bin*,internet_speed,"
            "translate(text_to_type=text,search_query=lang_code),"
            "read_pdf(file_name),"
            "set_reminder(message_text,volume_level=minutes),list_reminders,"
            "spotify_play_pause,spotify_next,spotify_prev,"
            "yt_play_pause,yt_pause,yt_play,yt_next,yt_previous,"
            "yt_volume_up,yt_volume_down,yt_mute,yt_fullscreen,"
            "yt_skip_forward(volume_level=secs),yt_skip_backward(volume_level=secs),"
            "yt_speed_up,yt_speed_down,yt_normal_speed,"
            "yt_what_playing,yt_like,yt_subscribe,"
            "wa_open,wa_close,wa_open_chat(contact_name),"
            "wa_send(contact_name,message_text),wa_read(contact_name),"
            "wa_unread,wa_call(contact_name),wa_video_call(contact_name),"
            "wa_end_call,wa_go_back,wa_help,"
            "unknown\n\n"
            "RULES:\n"
            "- * means needs_confirmation:true\n"
            "- Fill only relevant params, leave others empty\n"
            "- response_to_user must be short and natural spoken English\n"
            "- Return ONLY the JSON object, nothing else"
        )

    def _fallback(self) -> dict:
        return {
            "intent": "unknown",
            "params": {
                "app_name": "", "search_query": "", "contact_name": "",
                "message_text": "", "file_name": "", "folder_path": "",
                "text_to_type": "", "key_combination": "",
                "direction": "down", "url": "", "volume_level": ""
            },
            "needs_confirmation": False,
            "confirmation_message": "",
            "response_to_user": "Sorry, I did not understand. Please try again."
        }