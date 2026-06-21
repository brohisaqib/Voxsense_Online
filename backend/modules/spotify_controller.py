"""VoxSense — modules/spotify_controller.py"""
import keyboard as kb
from loguru import logger


class SpotifyController:
    async def play_pause(self) -> str:
        try:
            kb.send("space")
            return "Toggled play and pause on Spotify."
        except Exception as e:
            return f"Could not control Spotify. {e}"

    async def next_track(self) -> str:
        try:
            kb.send("ctrl+right")
            return "Skipped to next track."
        except Exception as e:
            return f"Could not skip track. {e}"

    async def prev_track(self) -> str:
        try:
            kb.send("ctrl+left")
            return "Going to previous track."
        except Exception as e:
            return f"Could not go back. {e}"

    async def open_spotify(self) -> str:
        try:
            import subprocess
            subprocess.Popen("spotify", shell=True)
            return "Opening Spotify."
        except Exception as e:
            return f"Could not open Spotify. {e}"