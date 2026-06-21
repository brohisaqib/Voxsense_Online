"""
VoxSense — modules/youtube_controller.py
Control YouTube in browser via voice commands.
All functions call bring_to_front() so keyboard commands work.
"""
import asyncio
from loguru import logger


class YouTubeController:

    def __init__(self, browser_controller):
        self._browser = browser_controller

    async def _get_page(self):
        return await self._browser._get_page()

    async def _is_youtube(self, page) -> bool:
        try:
            return "youtube.com" in page.url
        except Exception:
            return False

    async def _focus_page(self, page):
        """Bring YouTube page to front and focus video."""
        try:
            await page.bring_to_front()
            await asyncio.sleep(0.3)
        except Exception:
            pass
        try:
            await page.focus("body")
        except Exception:
            pass

    # ── Play / Pause ──────────────────────────────────────────────
    async def play_pause(self) -> str:
        try:
            page = await self._get_page()
            await self._focus_page(page)
            if not await self._is_youtube(page):
                return "YouTube is not open. Please open YouTube first."
            await page.keyboard.press("k")
            await asyncio.sleep(0.5)
            is_paused = await page.evaluate(
                "() => { const v = document.querySelector('video'); return v ? v.paused : null; }"
            )
            if is_paused is None:
                return "Could not detect video state."
            return "Video paused." if is_paused else "Video playing."
        except Exception as e:
            logger.error(f"Play/pause error: {e}")
            return "Sorry, could not play or pause."

    async def pause(self) -> str:
        try:
            page = await self._get_page()
            await self._focus_page(page)
            if not await self._is_youtube(page):
                return "YouTube is not open."
            is_paused = await page.evaluate(
                "() => { const v = document.querySelector('video'); return v ? v.paused : true; }"
            )
            if not is_paused:
                await page.keyboard.press("k")
                return "Video paused."
            return "Video is already paused."
        except Exception as e:
            logger.error(f"Pause error: {e}")
            return "Sorry, could not pause."

    async def play(self) -> str:
        try:
            page = await self._get_page()
            await self._focus_page(page)
            if not await self._is_youtube(page):
                return "YouTube is not open."
            is_paused = await page.evaluate(
                "() => { const v = document.querySelector('video'); return v ? v.paused : false; }"
            )
            if is_paused:
                await page.keyboard.press("k")
                return "Video playing."
            return "Video is already playing."
        except Exception as e:
            logger.error(f"Play error: {e}")
            return "Sorry, could not play."

    # ── Next / Previous ───────────────────────────────────────────
    async def next_video(self) -> str:
        try:
            page = await self._get_page()
            await self._focus_page(page)
            if not await self._is_youtube(page):
                return "YouTube is not open."
            await page.keyboard.press("shift+n")
            await asyncio.sleep(2)
            title = await page.title()
            return f"Next video: {title.replace('- YouTube', '').strip()}"
        except Exception as e:
            logger.error(f"Next video error: {e}")
            return "Sorry, could not skip to next video."

    async def previous_video(self) -> str:
        try:
            page = await self._get_page()
            await self._focus_page(page)
            if not await self._is_youtube(page):
                return "YouTube is not open."
            await page.keyboard.press("shift+p")
            await asyncio.sleep(2)
            title = await page.title()
            return f"Previous video: {title.replace('- YouTube', '').strip()}"
        except Exception as e:
            logger.error(f"Previous video error: {e}")
            return "Sorry, could not go to previous video."

    # ── Volume ────────────────────────────────────────────────────
    async def volume_up(self) -> str:
        try:
            page = await self._get_page()
            await self._focus_page(page)
            if not await self._is_youtube(page):
                return "YouTube is not open."
            for _ in range(5):
                await page.keyboard.press("ArrowUp")
                await asyncio.sleep(0.05)
            return "YouTube volume increased."
        except Exception as e:
            return f"Could not increase volume. {e}"

    async def volume_down(self) -> str:
        try:
            page = await self._get_page()
            await self._focus_page(page)
            if not await self._is_youtube(page):
                return "YouTube is not open."
            for _ in range(5):
                await page.keyboard.press("ArrowDown")
                await asyncio.sleep(0.05)
            return "YouTube volume decreased."
        except Exception as e:
            return f"Could not decrease volume. {e}"

    async def mute(self) -> str:
        try:
            page = await self._get_page()
            await self._focus_page(page)
            if not await self._is_youtube(page):
                return "YouTube is not open."
            await page.keyboard.press("m")
            return "YouTube muted or unmuted."
        except Exception as e:
            return f"Could not mute. {e}"

    # ── Fullscreen ────────────────────────────────────────────────
    async def fullscreen(self) -> str:
        try:
            page = await self._get_page()
            await self._focus_page(page)
            if not await self._is_youtube(page):
                return "YouTube is not open."
            await page.keyboard.press("f")
            return "Fullscreen toggled."
        except Exception as e:
            return f"Could not toggle fullscreen. {e}"

    # ── Skip Forward / Backward ───────────────────────────────────
    async def skip_forward(self, seconds: int = 10) -> str:
        try:
            page = await self._get_page()
            await self._focus_page(page)
            if not await self._is_youtube(page):
                return "YouTube is not open."
            # Each 'l' press = 10 seconds forward
            presses = max(1, seconds // 10)
            for _ in range(presses):
                await page.keyboard.press("l")
                await asyncio.sleep(0.1)
            return f"Skipped forward {presses * 10} seconds."
        except Exception as e:
            return f"Could not skip forward. {e}"

    async def skip_backward(self, seconds: int = 10) -> str:
        try:
            page = await self._get_page()
            await self._focus_page(page)
            if not await self._is_youtube(page):
                return "YouTube is not open."
            # Each 'j' press = 10 seconds backward
            presses = max(1, seconds // 10)
            for _ in range(presses):
                await page.keyboard.press("j")
                await asyncio.sleep(0.1)
            return f"Skipped backward {presses * 10} seconds."
        except Exception as e:
            return f"Could not skip backward. {e}"

    # ── Playback Speed ────────────────────────────────────────────
    async def speed_up(self) -> str:
        try:
            page = await self._get_page()
            await self._focus_page(page)
            if not await self._is_youtube(page):
                return "YouTube is not open."
            current = await page.evaluate(
                "() => document.querySelector('video')?.playbackRate || 1"
            )
            new_speed = min(round(current + 0.25, 2), 2.0)
            await page.evaluate(
                f"() => document.querySelector('video').playbackRate = {new_speed}"
            )
            return f"Playback speed set to {new_speed}x."
        except Exception as e:
            return f"Could not change speed. {e}"

    async def speed_down(self) -> str:
        try:
            page = await self._get_page()
            await self._focus_page(page)
            if not await self._is_youtube(page):
                return "YouTube is not open."
            current = await page.evaluate(
                "() => document.querySelector('video')?.playbackRate || 1"
            )
            new_speed = max(round(current - 0.25, 2), 0.25)
            await page.evaluate(
                f"() => document.querySelector('video').playbackRate = {new_speed}"
            )
            return f"Playback speed set to {new_speed}x."
        except Exception as e:
            return f"Could not change speed. {e}"

    async def normal_speed(self) -> str:
        try:
            page = await self._get_page()
            await self._focus_page(page)
            if not await self._is_youtube(page):
                return "YouTube is not open."
            await page.evaluate(
                "() => document.querySelector('video').playbackRate = 1"
            )
            return "Playback speed set to normal 1x."
        except Exception as e:
            return f"Could not reset speed. {e}"

    # ── What Is Playing ───────────────────────────────────────────
    async def what_is_playing(self) -> str:
        try:
            page = await self._get_page()
            await self._focus_page(page)
            if not await self._is_youtube(page):
                return "YouTube is not open."
            title = await page.title()
            title = title.replace("- YouTube", "").strip()
            current_time = await page.evaluate("""
                () => {
                    const v = document.querySelector('video');
                    if (!v || isNaN(v.duration)) return null;
                    const cm = Math.floor(v.currentTime / 60);
                    const cs = Math.floor(v.currentTime % 60);
                    const dm = Math.floor(v.duration / 60);
                    const ds = Math.floor(v.duration % 60);
                    return `${cm}:${String(cs).padStart(2,'0')} of ${dm}:${String(ds).padStart(2,'0')}`;
                }
            """)
            is_paused = await page.evaluate(
                "() => document.querySelector('video')?.paused ?? true"
            )
            status = "paused" if is_paused else "playing"
            if current_time:
                return f"Currently {status}: {title}. Time: {current_time}."
            return f"Currently {status}: {title}."
        except Exception as e:
            return f"Could not get video info. {e}"

    # ── Like / Subscribe ──────────────────────────────────────────
    async def like_video(self) -> str:
        try:
            page = await self._get_page()
            await self._focus_page(page)
            if not await self._is_youtube(page):
                return "YouTube is not open."
            like_btn = page.locator('button[aria-label*="like this video"], button[aria-label*="Like"]')
            if await like_btn.count() > 0:
                await like_btn.first.click()
                return "Video liked."
            return "Could not find like button."
        except Exception as e:
            return f"Could not like video. {e}"

    async def subscribe(self) -> str:
        try:
            page = await self._get_page()
            await self._focus_page(page)
            if not await self._is_youtube(page):
                return "YouTube is not open."
            sub_btn = page.locator('button[aria-label*="Subscribe"], yt-subscribe-button-view-model button')
            if await sub_btn.count() > 0:
                await sub_btn.first.click()
                return "Subscribed to channel."
            return "Could not find subscribe button."
        except Exception as e:
            return f"Could not subscribe. {e}"

    # ── Go To Time ────────────────────────────────────────────────
    async def go_to_time(self, seconds: int) -> str:
        try:
            page = await self._get_page()
            await self._focus_page(page)
            if not await self._is_youtube(page):
                return "YouTube is not open."
            await page.evaluate(
                f"() => document.querySelector('video').currentTime = {seconds}"
            )
            mins = seconds // 60
            secs = seconds % 60
            return f"Jumped to {mins}:{str(secs).zfill(2)}."
        except Exception as e:
            return f"Could not jump to time. {e}"