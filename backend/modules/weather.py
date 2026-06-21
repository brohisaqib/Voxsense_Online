"""VoxSense — modules/weather.py"""
import httpx
from loguru import logger


class WeatherService:
    async def get_weather(self, city: str = "Karachi") -> str:
        try:
            url = f"https://wttr.in/{city}?format=3"
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url)
                return f"Weather in {resp.text.strip()}"
        except Exception as e:
            logger.error(f"Weather error: {e}")
            return "Sorry, could not get weather right now."