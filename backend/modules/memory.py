"""
VoxSense — modules/memory.py
SQLite-backed conversation history, voice shortcuts, and app aliases.
Database stored at ~/.voxsense/memory.db
"""

import json
import sqlite3
from pathlib import Path
from typing import Optional

import aiosqlite
from loguru import logger


DB_PATH = Path.home() / ".voxsense" / "memory.db"


class MemoryManager:
    """Manages SQLite storage for VoxSense conversation history and shortcuts."""

    def __init__(self):
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = str(DB_PATH)

    async def init_db(self) -> None:
        """Create tables if they do not exist."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS conversations (
                        id      INTEGER PRIMARY KEY AUTOINCREMENT,
                        ts      DATETIME DEFAULT CURRENT_TIMESTAMP,
                        role    TEXT NOT NULL,
                        text    TEXT NOT NULL,
                        intent  TEXT DEFAULT ''
                    )
                """)
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS shortcuts (
                        phrase      TEXT PRIMARY KEY,
                        action_json TEXT NOT NULL,
                        use_count   INTEGER DEFAULT 0,
                        created_ts  DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS app_aliases (
                        alias     TEXT PRIMARY KEY,
                        real_name TEXT NOT NULL
                    )
                """)
                # Index for faster recent queries
                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_conv_ts ON conversations(ts DESC)
                """)
                await db.commit()
            logger.info(f"Memory database ready at {self.db_path}")
        except Exception as e:
            logger.error(f"Memory init_db error: {e}")
            raise

    # ─── CONVERSATIONS ────────────────────────────

    async def save_turn(self, role: str, text: str, intent: str = "") -> None:
        """Save a conversation turn (user or assistant)."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "INSERT INTO conversations (role, text, intent) VALUES (?, ?, ?)",
                    (role, text, intent),
                )
                await db.commit()
        except Exception as e:
            logger.error(f"save_turn error: {e}")

    async def get_recent(self, n: int = 10) -> list[dict]:
        """
        Return the last n conversation turns formatted for the Claude API.
        Returns: [{"role": "user"/"assistant", "content": "..."}, ...]
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    """
                    SELECT role, text FROM conversations
                    ORDER BY ts DESC
                    LIMIT ?
                    """,
                    (n,),
                ) as cursor:
                    rows = await cursor.fetchall()

            # Reverse so oldest first (Claude expects chronological order)
            turns = []
            for row in reversed(rows):
                role = row["role"]
                # Map our roles to Claude API roles
                if role == "user":
                    turns.append({"role": "user", "content": row["text"]})
                elif role in ("assistant", "ai"):
                    turns.append({"role": "assistant", "content": row["text"]})
            return turns
        except Exception as e:
            logger.error(f"get_recent error: {e}")
            return []

    async def clear_history(self) -> None:
        """Delete all conversation history."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("DELETE FROM conversations")
                await db.commit()
            logger.info("Conversation history cleared.")
        except Exception as e:
            logger.error(f"clear_history error: {e}")

    # ─── SHORTCUTS ────────────────────────────────

    async def save_shortcut(self, phrase: str, action_json: dict) -> None:
        """Create or update a voice shortcut."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    INSERT INTO shortcuts (phrase, action_json)
                    VALUES (?, ?)
                    ON CONFLICT(phrase) DO UPDATE SET
                        action_json = excluded.action_json,
                        use_count   = use_count + 1
                    """,
                    (phrase.lower().strip(), json.dumps(action_json)),
                )
                await db.commit()
        except Exception as e:
            logger.error(f"save_shortcut error: {e}")

    async def get_shortcut(self, phrase: str) -> Optional[dict]:
        """Return action JSON for a shortcut phrase, or None if not found."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    "SELECT action_json FROM shortcuts WHERE phrase = ?",
                    (phrase.lower().strip(),),
                ) as cursor:
                    row = await cursor.fetchone()

            if row:
                # Increment use count
                async with aiosqlite.connect(self.db_path) as db:
                    await db.execute(
                        "UPDATE shortcuts SET use_count = use_count + 1 WHERE phrase = ?",
                        (phrase.lower().strip(),),
                    )
                    await db.commit()
                return json.loads(row["action_json"])
            return None
        except Exception as e:
            logger.error(f"get_shortcut error: {e}")
            return None

    async def list_shortcuts(self) -> list[dict]:
        """Return all saved shortcuts."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    "SELECT phrase, use_count FROM shortcuts ORDER BY use_count DESC"
                ) as cursor:
                    rows = await cursor.fetchall()
            return [{"phrase": r["phrase"], "use_count": r["use_count"]} for r in rows]
        except Exception as e:
            logger.error(f"list_shortcuts error: {e}")
            return []

    # ─── APP ALIASES ─────────────────────────────

    async def save_alias(self, alias: str, real_name: str) -> None:
        """Save a user-defined app alias (e.g. "browser" → "chrome")."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    INSERT INTO app_aliases (alias, real_name)
                    VALUES (?, ?)
                    ON CONFLICT(alias) DO UPDATE SET real_name = excluded.real_name
                    """,
                    (alias.lower().strip(), real_name.strip()),
                )
                await db.commit()
        except Exception as e:
            logger.error(f"save_alias error: {e}")

    async def get_alias(self, alias: str) -> Optional[str]:
        """Return the real app name for an alias, or None."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    "SELECT real_name FROM app_aliases WHERE alias = ?",
                    (alias.lower().strip(),),
                ) as cursor:
                    row = await cursor.fetchone()
            return row["real_name"] if row else None
        except Exception as e:
            logger.error(f"get_alias error: {e}")
            return None