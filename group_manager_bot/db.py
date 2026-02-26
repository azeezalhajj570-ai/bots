from __future__ import annotations

import logging
import sqlite3

from .migrations import apply_migrations
from .storage import BotRepository, DynamicRule, LinkRoute, ParticipationGate

log = logging.getLogger(__name__)


class DB(BotRepository):
    def __init__(self, path: str = "bot.db") -> None:
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self._init_schema()

    def _init_schema(self) -> None:
        apply_migrations(self.conn)
        self._migrate_group_settings()
        self.conn.commit()
        log.info("Database initialized.")

    def _migrate_group_settings(self) -> None:
        columns = {
            row[1]
            for row in self.conn.execute("PRAGMA table_info(group_settings)").fetchall()
        }
        if "anti_links" not in columns:
            self.conn.execute("ALTER TABLE group_settings ADD COLUMN anti_links INTEGER DEFAULT 1")
            log.info("Migrated database: added group_settings.anti_links")
        if "anti_bots" not in columns:
            self.conn.execute("ALTER TABLE group_settings ADD COLUMN anti_bots INTEGER DEFAULT 1")
            log.info("Migrated database: added group_settings.anti_bots")
        if "hide_system" not in columns:
            self.conn.execute("ALTER TABLE group_settings ADD COLUMN hide_system INTEGER DEFAULT 0")
            log.info("Migrated database: added group_settings.hide_system")
        if "warn_in_dm" not in columns:
            self.conn.execute("ALTER TABLE group_settings ADD COLUMN warn_in_dm INTEGER DEFAULT 0")
            log.info("Migrated database: added group_settings.warn_in_dm")
        if "warn_in_group" not in columns:
            self.conn.execute("ALTER TABLE group_settings ADD COLUMN warn_in_group INTEGER DEFAULT 1")
            log.info("Migrated database: added group_settings.warn_in_group")

    def ensure_group(self, chat_id: int) -> None:
        self.conn.execute("INSERT OR IGNORE INTO group_settings(chat_id) VALUES (?)", (chat_id,))
        self.conn.commit()

    def get_setting(self, chat_id: int, key: str) -> bool:
        self.ensure_group(chat_id)
        row = self.conn.execute(f"SELECT {key} FROM group_settings WHERE chat_id=?", (chat_id,)).fetchone()
        return bool(row[0]) if row else True

    def toggle_setting(self, chat_id: int, key: str) -> bool:
        cur = self.get_setting(chat_id, key)
        new_val = not cur
        self.conn.execute(f"UPDATE group_settings SET {key}=? WHERE chat_id=?", (1 if new_val else 0, chat_id))
        self.conn.commit()
        return new_val

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

    def get_warns(self, chat_id: int, user_id: int) -> int:
        row = self.conn.execute(
            "SELECT warns FROM warnings WHERE chat_id=? AND user_id=?",
            (chat_id, user_id),
        ).fetchone()
        return int(row[0]) if row else 0

    def set_warns(self, chat_id: int, user_id: int, warns: int) -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO warnings(chat_id,user_id,warns) VALUES (?,?,0)",
            (chat_id, user_id),
        )
        self.conn.execute(
            "UPDATE warnings SET warns=? WHERE chat_id=? AND user_id=?",
            (warns, chat_id, user_id),
        )
        self.conn.commit()

    def reset_warns(self, chat_id: int, user_id: int) -> None:
        self.conn.execute("DELETE FROM warnings WHERE chat_id=? AND user_id=?", (chat_id, user_id))
        self.conn.commit()

    def add_dynamic_rule(self, chat_id: int, pattern: str) -> int:
        cursor = self.conn.execute(
            "INSERT INTO dynamic_remove_rules(chat_id, pattern, enabled) VALUES (?,?,1)",
            (chat_id, pattern),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def list_dynamic_rules(self, chat_id: int) -> list[DynamicRule]:
        rows = self.conn.execute(
            "SELECT id, chat_id, pattern, enabled FROM dynamic_remove_rules WHERE chat_id=? ORDER BY id ASC",
            (chat_id,),
        ).fetchall()
        return [
            DynamicRule(
                id=int(row[0]),
                chat_id=int(row[1]),
                pattern=str(row[2]),
                enabled=bool(row[3]),
            )
            for row in rows
        ]

    def delete_dynamic_rule(self, chat_id: int, rule_id: int) -> bool:
        cursor = self.conn.execute(
            "DELETE FROM dynamic_remove_rules WHERE chat_id=? AND id=?",
            (chat_id, rule_id),
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def upsert_link_route(self, chat_id: int, keyword: str, destination: str, gate_group_id: int | None = None) -> None:
        self.conn.execute(
            """
            INSERT INTO link_routes(chat_id, keyword, destination, gate_group_id, enabled)
            VALUES (?, ?, ?, ?, 1)
            ON CONFLICT(chat_id, keyword) DO UPDATE SET
              destination=excluded.destination,
              gate_group_id=excluded.gate_group_id,
              enabled=1
            """,
            (chat_id, keyword.lower().strip(), destination.strip(), gate_group_id),
        )
        self.conn.commit()

    def list_link_routes(self, chat_id: int) -> list[LinkRoute]:
        rows = self.conn.execute(
            """
            SELECT chat_id, keyword, destination, gate_group_id, enabled
            FROM link_routes
            WHERE chat_id=?
            ORDER BY keyword ASC
            """,
            (chat_id,),
        ).fetchall()
        return [
            LinkRoute(
                chat_id=int(row[0]),
                keyword=str(row[1]),
                destination=str(row[2]),
                gate_group_id=int(row[3]) if row[3] is not None else None,
                enabled=bool(row[4]),
            )
            for row in rows
        ]

    def delete_link_route(self, chat_id: int, keyword: str) -> bool:
        cursor = self.conn.execute(
            "DELETE FROM link_routes WHERE chat_id=? AND keyword=?",
            (chat_id, keyword.lower().strip()),
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def upsert_participation_gate(self, chat_id: int, gate_group_id: int, gate_title: str, join_url: str) -> None:
        self.conn.execute(
            """
            INSERT INTO participation_gates(chat_id, gate_group_id, gate_title, join_url, enabled)
            VALUES (?, ?, ?, ?, 1)
            ON CONFLICT(chat_id, gate_group_id) DO UPDATE SET
              gate_title=excluded.gate_title,
              join_url=excluded.join_url,
              enabled=1
            """,
            (chat_id, gate_group_id, gate_title, join_url),
        )
        self.conn.commit()

    def list_participation_gates(self, chat_id: int) -> list[ParticipationGate]:
        rows = self.conn.execute(
            """
            SELECT chat_id, gate_group_id, gate_title, join_url, enabled
            FROM participation_gates
            WHERE chat_id=?
            ORDER BY gate_title ASC
            """,
            (chat_id,),
        ).fetchall()
        return [
            ParticipationGate(
                chat_id=int(row[0]),
                gate_group_id=int(row[1]),
                gate_title=str(row[2]),
                join_url=str(row[3]),
                enabled=bool(row[4]),
            )
            for row in rows
        ]

    def delete_participation_gate(self, chat_id: int, gate_group_id: int) -> bool:
        cursor = self.conn.execute(
            "DELETE FROM participation_gates WHERE chat_id=? AND gate_group_id=?",
            (chat_id, gate_group_id),
        )
        self.conn.commit()
        return cursor.rowcount > 0
