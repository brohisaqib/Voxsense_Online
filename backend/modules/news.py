"""
VoxSense — modules/news.py
News from Pakistan + World + Tech + Sports in English
"""
import httpx
import xml.etree.ElementTree as ET
from loguru import logger


NEWS_SOURCES = {
    "pakistan": [
        {"name": "Geo News",   "url": "https://www.geo.tv/rss/1"},
        {"name": "ARY News",   "url": "https://arynews.tv/feed/"},
        {"name": "Dawn",       "url": "https://www.dawn.com/feeds/home"},
    ],
    "world": [
        {"name": "BBC World",  "url": "https://feeds.bbci.co.uk/news/world/rss.xml"},
        {"name": "Al Jazeera", "url": "https://www.aljazeera.com/xml/rss/all.xml"},
    ],
    "technology": [
        {"name": "TechCrunch", "url": "https://techcrunch.com/feed/"},
        {"name": "BBC Tech",   "url": "https://feeds.bbci.co.uk/news/technology/rss.xml"},
    ],
    "sports": [
        {"name": "BBC Sport",  "url": "https://feeds.bbci.co.uk/sport/rss.xml"},
        {"name": "ESPN",       "url": "https://www.espn.com/espn/rss/news"},
    ],
}


async def _fetch_feed(url: str, count: int = 3) -> list:
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get(url)
        root = ET.fromstring(resp.text)
        items = root.findall(".//item")[:count]
        headlines = []
        for item in items:
            title = item.find("title")
            if title is not None and title.text:
                headlines.append(title.text.strip())
        return headlines
    except Exception as e:
        logger.error(f"Feed error {url}: {e}")
        return []


class NewsService:

    async def get_headlines(self, category: str = "pakistan", count: int = 5) -> str:
        try:
            sources = NEWS_SOURCES.get(category, NEWS_SOURCES["pakistan"])
            all_headlines = []
            for source in sources:
                headlines = await _fetch_feed(source["url"], count=2)
                for h in headlines:
                    all_headlines.append(f"{source['name']}: {h}")
                if len(all_headlines) >= count:
                    break
            if not all_headlines:
                return "Sorry, no news available right now. Please try again."
            result = f"Top {len(all_headlines[:count])} headlines. " + ". ".join(all_headlines[:count])
            return result
        except Exception as e:
            logger.error(f"News error: {e}")
            return "Sorry, could not fetch news right now."

    async def get_pakistan_news(self) -> str:
        return await self.get_headlines("pakistan")

    async def get_world_news(self) -> str:
        return await self.get_headlines("world")

    async def get_tech_news(self) -> str:
        return await self.get_headlines("technology")

    async def get_sports_news(self) -> str:
        return await self.get_headlines("sports")

    async def get_all_news(self) -> str:
        try:
            categories = {
                "pakistan":   "Pakistan",
                "world":      "World",
                "technology": "Technology",
                "sports":     "Sports"
            }
            results = []
            for cat, label in categories.items():
                sources = NEWS_SOURCES[cat]
                headlines = await _fetch_feed(sources[0]["url"], count=1)
                if headlines:
                    results.append(f"{label}: {headlines[0]}")
            if not results:
                return "No news available right now."
            return "Today top news. " + ". ".join(results)
        except Exception as e:
            logger.error(f"All news error: {e}")
            return "Could not fetch news."