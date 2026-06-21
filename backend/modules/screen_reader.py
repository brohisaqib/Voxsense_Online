"""
VoxSense — modules/screen_reader.py
Three-layer screen reading:
  1. NVDA API (primary, if installed)
  2. Win32 / UIA accessibility tree (pywinauto)
  3. OCR fallback via EasyOCR + mss screenshot
"""

import asyncio
from pathlib import Path
from typing import Optional

import mss
from PIL import Image
from loguru import logger


class ScreenReader:
    """Reads current screen content using layered accessibility strategies."""

    def __init__(self):
        self._ocr_reader = None  # Lazy-load EasyOCR (heavy import)
        self._nvda_available = self._check_nvda()

    # ─── NVDA CHECK ──────────────────────────────

    def _check_nvda(self) -> bool:
        try:
            import nvda_controller_client as nvda  # type: ignore  # noqa
            return True
        except ImportError:
            return False
        except Exception:
            return False

    async def speak_via_nvda(self, text: str) -> bool:
        """Speak text through NVDA if available."""
        if not self._nvda_available:
            return False
        try:
            import nvda_controller_client as nvda  # type: ignore
            await asyncio.get_event_loop().run_in_executor(None, nvda.speakText, text)
            return True
        except Exception as e:
            logger.debug(f"NVDA speak error: {e}")
            return False

    # ─── LAYER 1: NVDA focused element ──────────

    async def _read_via_nvda(self) -> Optional[dict]:
        """Use uiautomation to get focused element info."""
        try:
            import uiautomation as auto  # type: ignore
            ctrl = auto.GetFocusedControl()
            if ctrl is None:
                return None

            info = {
                "app":       ctrl.GetTopLevelControl().Name if ctrl.GetTopLevelControl() else "Unknown",
                "title":     ctrl.Name or "",
                "focused":   f"{ctrl.ControlTypeName}: {ctrl.Name}",
                "value":     ctrl.GetValuePattern().Value if ctrl.GetPattern(10002) else "",
                "state":     str(ctrl.CurrentState() if hasattr(ctrl, "CurrentState") else ""),
            }
            return info
        except Exception as e:
            logger.debug(f"NVDA/UIA layer error: {e}")
            return None

    # ─── LAYER 2: Win32 accessibility tree ──────

    async def _read_via_pywinauto(self) -> Optional[dict]:
        """Read accessible info via pywinauto."""
        try:
            from pywinauto import Desktop  # type: ignore
            desktop = Desktop(backend="uia")
            focused = desktop.from_point(*self._get_cursor_pos())
            if focused is None:
                return None

            info = {
                "app":       "",
                "title":     focused.window_text() or "",
                "focused":   f"{focused.friendly_class_name()}: {focused.window_text()}",
                "value":     "",
            }
            # Try to get the top-level window name
            try:
                top = focused.top_level_parent()
                info["app"] = top.window_text() or "Unknown"
            except Exception:
                pass

            return info
        except Exception as e:
            logger.debug(f"pywinauto layer error: {e}")
            return None

    def _get_cursor_pos(self):
        try:
            import ctypes
            class POINT(ctypes.Structure):
                _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
            pt = POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
            return pt.x, pt.y
        except Exception:
            return 0, 0

    # ─── LAYER 3: OCR fallback ───────────────────

    async def _read_via_ocr(self) -> Optional[str]:
        """Capture screen and extract text with EasyOCR."""
        try:
            # Lazy init EasyOCR reader
            if self._ocr_reader is None:
                import easyocr  # type: ignore
                self._ocr_reader = easyocr.Reader(["en"], gpu=False, verbose=False)
                logger.info("EasyOCR initialised.")

            with mss.mss() as sct:
                shot = sct.grab(sct.monitors[0])
                img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")

            import numpy as np  # type: ignore
            img_array = np.array(img)
            results = self._ocr_reader.readtext(img_array, detail=1, paragraph=False)

            # Filter low-confidence results
            high_conf = [r[1] for r in results if r[2] > 0.7]

            if high_conf:
                return " ".join(high_conf[:40])  # Return up to 40 text segments
            return None

        except Exception as e:
            logger.debug(f"OCR layer error: {e}")
            return None

    # ─── PUBLIC: read_screen ─────────────────────

    async def read_screen(self) -> dict:
        """
        Read the current screen using layered strategy.
        Returns a dict with keys: app, title, focused, description.
        """
        result = {
            "app":         "Unknown",
            "title":       "",
            "focused":     "",
            "description": "",
        }

        # Layer 1 — NVDA / UIA
        layer1 = await self._read_via_nvda()
        if layer1:
            result.update(layer1)
            logger.debug(f"Screen read via UIA: {result}")

        # Layer 2 — pywinauto (fills gaps)
        if not result["app"] or result["app"] == "Unknown":
            layer2 = await self._read_via_pywinauto()
            if layer2:
                for k, v in layer2.items():
                    if not result.get(k):
                        result[k] = v

        # Layer 3 — OCR if we still have nothing useful
        if not result["title"] and not result["focused"]:
            ocr_text = await self._read_via_ocr()
            if ocr_text:
                result["description"] = f"Screen text: {ocr_text[:300]}"

        # Build natural description
        parts = []
        if result["app"] and result["app"] != "Unknown":
            parts.append(f"{result['app']} is open.")
        if result["title"]:
            parts.append(f"Title: {result['title']}.")
        if result["focused"]:
            parts.append(f"Focused element: {result['focused']}.")
        if result["description"]:
            parts.append(result["description"])

        if parts:
            result["description"] = " ".join(parts)
        else:
            result["description"] = "I was unable to read the screen. The screen may be locked or no accessible application is in focus."

        logger.info(f"Screen read result: {result['description'][:100]}")
        return result

    async def describe_screen(self) -> str:
        """Convenience method returning just the natural language description."""
        try:
            result = await self.read_screen()
            return result.get("description", "Unable to read screen.")
        except Exception as e:
            logger.error(f"describe_screen error: {e}")
            return "Sorry, I could not read your screen at this time."