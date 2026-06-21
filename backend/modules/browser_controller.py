"""
VoxSense — modules/browser_controller.py
"""
import asyncio
import sys
import subprocess
from loguru import logger

import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())



class BrowserController:
    def __init__(self):
        self._browser = None
        self._page    = None
        self._pw      = None

    async def _get_page(self):
        try:
            if self._browser is None:
                from playwright.async_api import async_playwright
                self._pw = await async_playwright().start()
                self._browser = await self._pw.chromium.launch(
                    headless=False,
                    args=[
                        "--autoplay-policy=no-user-gesture-required",
                        "--disable-features=PreloadMediaEngagementData",
                        "--no-sandbox",
                    ]
                )
                context = await self._browser.new_context(
                    permissions=["microphone"],
                    java_script_enabled=True,
                )
                # Autoplay allow karo
                await context.grant_permissions(["microphone"])
                self._page = await context.new_page()
            return self._page
        except Exception as e:
            logger.error(f"Browser init error: {e}")
            raise

    async def open_url(self, url: str) -> str:
        try:
            # Try Playwright first
            page = await self._get_page()
            await page.goto(url, timeout=15000)
            return f"Opened {url}"
        except Exception as e:
            logger.error(f"URL error: {e}")
            # Fallback — open in default browser
            try:
                subprocess.Popen(
                    f'start "" "{url}"',
                    shell=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                return f"Opened {url} in your browser."
            except Exception as e2:
                return f"Could not open {url}. {e2}"
    async def youtube_play(self, query: str) -> str:
        try:
            import urllib.parse
            page = await self._get_page()

            # Step 1 — Search
            search_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
            await page.goto(search_url, timeout=15000)
            await page.wait_for_timeout(3000)

            # Step 2 — Pehli video ka href JavaScript se lo
            href = await page.evaluate("""
                () => {
                    const links = document.querySelectorAll('a#video-title');
                    for (const a of links) {
                        if (a.href && a.href.includes('/watch?v=')) {
                            return a.href;
                        }
                    }
                    return null;
                }
            """)

            if not href:
                href = await page.evaluate("""
                    () => {
                        const a = document.querySelector('ytd-video-renderer a#thumbnail');
                        return a ? a.href : null;
                    }
                """)

            if not href:
                subprocess.Popen(f'start "" "{search_url}"', shell=True)
                return f"Opening YouTube search for {query}."

            # Step 3 — Video page pe jao
            await page.goto(href, timeout=15000)
            await page.bring_to_front()
            await page.wait_for_timeout(2000)

            # Step 4 — JavaScript se video play karo (autoplay bypass)
            played = await page.evaluate("""
                async () => {
                    const video = document.querySelector('video');
                    if (video) {
                        video.muted = false;
                        try {
                            await video.play();
                            return true;
                        } catch(e) {
                            return false;
                        }
                    }
                    return false;
                }
            """)

            await page.wait_for_timeout(1000)

            # Step 5 — Agar JS play nahi hua toh keyboard se
            if not played:
                await page.click("body")
                await page.wait_for_timeout(500)
                await page.keyboard.press("k")
                await page.wait_for_timeout(500)
                await page.keyboard.press("k")

            # Step 6 — Ad skip
            try:
                await page.wait_for_timeout(1500)
                skip = page.locator(".ytp-skip-ad-button, .ytp-ad-skip-button-container button")
                if await skip.count() > 0:
                    await skip.first.click()
            except Exception:
                pass

            # Step 7 — Title
            try:
                title = await page.title()
                title = title.replace("- YouTube", "").strip()
            except Exception:
                title = query

            return f"Now playing: {title}"

        except Exception as e:
            logger.error(f"YouTube error: {e}")
            try:
                import urllib.parse
                url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
                subprocess.Popen(f'start "" "{url}"', shell=True)
                return f"Opening YouTube for {query}."
            except Exception:
                return "Sorry, could not open YouTube."
    async def whatsapp_send(self, contact: str, message: str) -> str:
        try:
            page = await self._get_page()
            await page.goto("https://web.whatsapp.com", timeout=30000)
            await page.wait_for_selector(
                '[placeholder="Search input textbox"]',
                timeout=30000
            )
            await page.fill('[placeholder="Search input textbox"]', contact)
            await page.wait_for_timeout(2000)
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(1000)
            await page.fill('[placeholder="Type a message"]', message)
            await page.keyboard.press("Enter")
            return f"Message sent to {contact}."
        except Exception as e:
            logger.error(f"WhatsApp send error: {e}")
            return "Sorry, could not send WhatsApp message. Make sure WhatsApp Web is logged in."

    async def whatsapp_read(self, contact: str) -> str:
        try:
            page = await self._get_page()
            await page.goto("https://web.whatsapp.com", timeout=30000)
            await page.wait_for_selector(
                '[placeholder="Search input textbox"]',
                timeout=30000
            )
            await page.fill('[placeholder="Search input textbox"]', contact)
            await page.wait_for_timeout(2000)
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(1500)
            msgs = await page.locator(
                ".message-in .copyable-text"
            ).all_inner_texts()
            if msgs:
                last = msgs[-3:] if len(msgs) >= 3 else msgs
                return f"Last messages from {contact}: " + " | ".join(last)
            return f"No messages found from {contact}."
        except Exception as e:
            logger.error(f"WhatsApp read error: {e}")
            return "Sorry, could not read WhatsApp messages."

    async def instagram_read_dm(self, username: str) -> str:
        try:
            page = await self._get_page()
            await page.goto(
                "https://www.instagram.com/direct/inbox/",
                timeout=15000
            )
            await page.wait_for_timeout(3000)
            text = await page.inner_text("body")
            preview = " ".join(text.split()[:80])
            return f"Instagram inbox opened. {preview}"
        except Exception as e:
            logger.error(f"Instagram error: {e}")
            try:
                subprocess.Popen(
                    'start "" "https://www.instagram.com/direct/inbox/"',
                    shell=True
                )
                return "Opening Instagram inbox in browser."
            except Exception:
                return "Sorry, could not open Instagram."