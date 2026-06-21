"""
VoxSense — modules/tts_service.py
Browser TTS use karta hai — ElevenLabs optional
"""
import os
import base64
import httpx
from loguru import logger
from dotenv import load_dotenv

load_dotenv()


class TTSService:
    def __init__(self):
        self.api_key  = os.getenv("ELEVENLABS_API_KEY", "").strip()
        self.voice_id = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
        self.base_url = "https://api.elevenlabs.io/v1"
        self.enabled  = bool(self.api_key)  # Key hai toh hi use karo

        if self.enabled:
            logger.info(f"ElevenLabs TTS ready — voice: {self.voice_id}")
        else:
            logger.info("ElevenLabs key nahi — browser TTS use hoga")

    async def speak(self, text: str) -> dict:
        # Key nahi hai toh seedha False return karo — no API call
        if not self.enabled:
            return {"success": False}

        if not text or not text.strip():
            return {"success": False}

        try:
            url = f"{self.base_url}/text-to-speech/{self.voice_id}"
            headers = {
                "xi-api-key": self.api_key,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg"
            }
            payload = {
                "text": text[:500],
                "model_id": "eleven_turbo_v2",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75,
                    "style": 0.3,
                    "use_speaker_boost": True
                }
            }

            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(url, headers=headers, json=payload)

            if resp.status_code == 200:
                audio_b64 = base64.b64encode(resp.content).decode("utf-8")
                logger.info(f"ElevenLabs TTS success — {len(text)} chars")
                return {"success": True, "audio_base64": audio_b64, "format": "mp3"}
            else:
                logger.warning(f"ElevenLabs error {resp.status_code} — browser TTS use hoga")
                self.enabled = False  # Baar baar try mat karo
                return {"success": False}

        except Exception as e:
            logger.error(f"TTS error: {e}")
            return {"success": False}

    async def get_voices(self) -> list:
        if not self.enabled:
            return []
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{self.base_url}/voices",
                    headers={"xi-api-key": self.api_key}
                )
            return [{"id": v["voice_id"], "name": v["name"]} 
                    for v in resp.json().get("voices", [])]
        except Exception as e:
            logger.error(f"Get voices error: {e}")
            return []