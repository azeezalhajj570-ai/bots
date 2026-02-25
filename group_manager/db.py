from __future__ import annotations

import logging
import sqlite3

logger = logging.getLogger(__name__)


class DB:
    def __init__(self, path: str = "bot.db") -> None:
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self._init_schema()
        logger.info("Database opened: %s", path)

    def _init_schema(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS group_settings(
              chat_id INTEGER PRIMARY KEY,
              anti_links INTEGER DEFAULT 1,
              anti_bots  INTEGER DEFAULT 1
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS warnings(
              chat_id INTEGER,
              user_id INTEGER,
              warns INTEGER DEFAULT 0,
              PRIMARY KEY(chat_id, user_id)
            )
            """
        )
        self.conn.commit()
        logger.info("Database schema initialized")

    def ensure_group(self, chat_id: int) -> None:
        self.conn.execute("INSERT OR IGNORE INTO group_settings(chat_id) VALUES (?)", (chat_id,))
        self.conn.commit()

    def get_setting(self, chat_id: int, key: str) -> bool:
        self.ensure_group(chat_id)
        row = self.conn.execute(f"SELECT {key} FROM group_settings WHERE chat_id=?", (chat_id,)).fetchone()
        return bool(row[0]) if row else True

    def toggle_setting(self, chat_id: int, key: str) -> bool:
        current = self.get_setting(chat_id, key)
        new_value = not current
        self.conn.execute(
            f"UPDATE group_settings SET {key}=? WHERE chat_id=?",
            (1 if new_value else 0, chat_id),
        )
        self.conn.commit()
        return new_value

    def add_warn(self, chat_id: int, user_id: int) -> int:
        self.conn.execute(
            "INSERT OR IGNORE INTO warnings(chat_id,user_id,warns) VALUES (?,?,0)",
            (chat_id, user_id),
        )
        self.conn.execute(
            "UPDATE warnings SET warns=warns+1 WHERE chat_id=? AND user_id=?",
            (chat_id, user_id),
        )
        self.conn.commit()
        row = self.conn.execute(
            "SELECT warns FROM warnings WHERE chat_id=? AND user_id=?",
            (chat_id, user_id),
        ).fetchone()
        return int(row[0]) if row else 0

    def reset_warns(self, chat_id: int, user_id: int) -> None:
        self.conn.execute("DELETE FROM warnings WHERE chat_id=? AND user_id=?", (chat_id, user_id))
        self.conn.commit()
