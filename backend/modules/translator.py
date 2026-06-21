"""VoxSense — modules/translator.py"""
import httpx
from loguru import logger


class TranslatorService:
    async def translate(self, text: str, target_lang: str = "ur") -> str:
        try:
            url = "https://translate.googleapis.com/translate_a/single"
            params = {
                "client": "gtx",
                "sl": "auto",
                "tl": target_lang,
                "dt": "t",
                "q": text
            }
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url, params=params)
            data = resp.json()
            translated = "".join([item[0] for item in data[0] if item[0]])
            return f"Translation: {translated}"
        except Exception as e:
            logger.error(f"Translation error: {e}")
            return "Sorry, could not translate right now."