from __future__ import annotations

import logging

import psycopg

from .storage import BotRepository, DynamicRule, LinkRoute, ParticipationGate

log = logging.getLogger(__name__)

_SETTING_KEYS = {"anti_links", "anti_bots", "hide_system", "warn_in_dm", "warn_in_group"}


class PostgresDB(BotRepository):
    def __init__(self, database_url: str) -> None:
        self.conn = psycopg.connect(database_url)
        self._init_schema()

    def _init_schema(self) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS group_settings(
                  chat_id BIGINT PRIMARY KEY,
                  anti_links BOOLEAN DEFAULT TRUE,
                  anti_bots BOOLEAN DEFAULT TRUE,
                  hide_system BOOLEAN DEFAULT FALSE,
                  warn_in_dm BOOLEAN DEFAULT FALSE,
                  warn_in_group BOOLEAN DEFAULT TRUE
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS warnings(
                  chat_id BIGINT NOT NULL,
                  user_id BIGINT NOT NULL,
                  warns INTEGER DEFAULT 0,
                  PRIMARY KEY(chat_id, user_id)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS dynamic_remove_rules(
                  id BIGSERIAL PRIMARY KEY,
                  chat_id BIGINT NOT NULL,
                  pattern TEXT NOT NULL,
                  enabled BOOLEAN NOT NULL DEFAULT TRUE
                )
                """
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_dynamic_remove_rules_chat ON dynamic_remove_rules(chat_id)"
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS link_routes(
                  chat_id BIGINT NOT NULL,
                  keyword TEXT NOT NULL,
                  destination TEXT NOT NULL,
                  gate_group_id BIGINT,
                  enabled BOOLEAN NOT NULL DEFAULT TRUE,
                  PRIMARY KEY(chat_id, keyword)
                )
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS idx_link_routes_chat ON link_routes(chat_id)")
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS participation_gates(
                  chat_id BIGINT NOT NULL,
                  gate_group_id BIGINT NOT NULL,
                  gate_title TEXT NOT NULL,
                  join_url TEXT NOT NULL,
                  enabled BOOLEAN NOT NULL DEFAULT TRUE,
                  PRIMARY KEY(chat_id, gate_group_id)
                )
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS idx_participation_gates_chat ON participation_gates(chat_id)")
        self.conn.commit()
        log.info("PostgreSQL schema initialized.")

    def _validate_setting_key(self, key: str) -> str:
        if key not in _SETTING_KEYS:
            raise ValueError(f"Unsupported setting key: {key}")
        return key

    def ensure_group(self, chat_id: int) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                "INSERT INTO group_settings(chat_id) VALUES (%s) ON CONFLICT(chat_id) DO NOTHING",
                (chat_id,),
            )
        self.conn.commit()

    def list_group_chat_ids(self) -> list[int]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT chat_id
                FROM (
                  SELECT chat_id FROM group_settings
                  UNION ALL
                  SELECT chat_id FROM dynamic_remove_rules
                  UNION ALL
                  SELECT chat_id FROM link_routes
                  UNION ALL
                  SELECT chat_id FROM participation_gates
                  UNION ALL
                  SELECT chat_id FROM warnings
                ) AS all_chat_ids
                ORDER BY chat_id ASC
                """
            )
            rows = cur.fetchall()
        return [int(row[0]) for row in rows]

    def get_settings_map(self, chat_id: int) -> dict[str, bool]:
        self.ensure_group(chat_id)
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT anti_links, anti_bots, hide_system, warn_in_dm, warn_in_group
                FROM group_settings
                WHERE chat_id=%s
                """,
                (chat_id,),
            )
            row = cur.fetchone()
        if not row:
            return {
                "anti_links": True,
                "anti_bots": True,
                "hide_system": False,
                "warn_in_dm": False,
                "warn_in_group": True,
            }
        return {
            "anti_links": bool(row[0]),
            "anti_bots": bool(row[1]),
            "hide_system": bool(row[2]),
            "warn_in_dm": bool(row[3]),
            "warn_in_group": bool(row[4]),
        }

    def get_setting(self, chat_id: int, key: str) -> bool:
        column = self._validate_setting_key(key)
        self.ensure_group(chat_id)
        with self.conn.cursor() as cur:
            cur.execute(f"SELECT {column} FROM group_settings WHERE chat_id=%s", (chat_id,))
            row = cur.fetchone()
        return bool(row[0]) if row else True

    def toggle_setting(self, chat_id: int, key: str) -> bool:
        column = self._validate_setting_key(key)
        new_val = not self.get_setting(chat_id, column)
        with self.conn.cursor() as cur:
            cur.execute(f"UPDATE group_settings SET {column}=%s WHERE chat_id=%s", (new_val, chat_id))
        self.conn.commit()
        return new_val

    def add_warn(self, chat_id: int, user_id: int) -> int:
        with self.conn.cursor() as cur:
            cur.execute(
                "INSERT INTO warnings(chat_id, user_id, warns) VALUES (%s, %s, 0) ON CONFLICT(chat_id, user_id) DO NOTHING",
                (chat_id, user_id),
            )
            cur.execute(
                "UPDATE warnings SET warns=warns+1 WHERE chat_id=%s AND user_id=%s",
                (chat_id, user_id),
            )
            cur.execute(
                "SELECT warns FROM warnings WHERE chat_id=%s AND user_id=%s",
                (chat_id, user_id),
            )
            row = cur.fetchone()
        self.conn.commit()
        return int(row[0]) if row else 0

    def get_warns(self, chat_id: int, user_id: int) -> int:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT warns FROM warnings WHERE chat_id=%s AND user_id=%s",
                (chat_id, user_id),
            )
            row = cur.fetchone()
        return int(row[0]) if row else 0

    def set_warns(self, chat_id: int, user_id: int, warns: int) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO warnings(chat_id, user_id, warns)
                VALUES (%s, %s, %s)
                ON CONFLICT(chat_id, user_id)
                DO UPDATE SET warns=EXCLUDED.warns
                """,
                (chat_id, user_id, warns),
            )
        self.conn.commit()

    def reset_warns(self, chat_id: int, user_id: int) -> None:
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM warnings WHERE chat_id=%s AND user_id=%s", (chat_id, user_id))
        self.conn.commit()

    def add_dynamic_rule(self, chat_id: int, pattern: str) -> int:
        with self.conn.cursor() as cur:
            cur.execute(
                "INSERT INTO dynamic_remove_rules(chat_id, pattern, enabled) VALUES (%s, %s, TRUE) RETURNING id",
                (chat_id, pattern),
            )
            row = cur.fetchone()
        self.conn.commit()
        return int(row[0]) if row else 0

    def list_dynamic_rules(self, chat_id: int) -> list[DynamicRule]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, chat_id, pattern, enabled
                FROM dynamic_remove_rules
                WHERE chat_id=%s
                ORDER BY id ASC
                """,
                (chat_id,),
            )
            rows = cur.fetchall()
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
        with self.conn.cursor() as cur:
            cur.execute(
                "DELETE FROM dynamic_remove_rules WHERE chat_id=%s AND id=%s",
                (chat_id, rule_id),
            )
            deleted = cur.rowcount > 0
        self.conn.commit()
        return deleted

    def upsert_link_route(self, chat_id: int, keyword: str, destination: str, gate_group_id: int | None = None) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO link_routes(chat_id, keyword, destination, gate_group_id, enabled)
                VALUES (%s, %s, %s, %s, TRUE)
                ON CONFLICT(chat_id, keyword) DO UPDATE SET
                  destination=EXCLUDED.destination,
                  gate_group_id=EXCLUDED.gate_group_id,
                  enabled=TRUE
                """,
                (chat_id, keyword.lower().strip(), destination.strip(), gate_group_id),
            )
        self.conn.commit()

    def list_link_routes(self, chat_id: int) -> list[LinkRoute]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT chat_id, keyword, destination, gate_group_id, enabled
                FROM link_routes
                WHERE chat_id=%s
                ORDER BY keyword ASC
                """,
                (chat_id,),
            )
            rows = cur.fetchall()
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
        with self.conn.cursor() as cur:
            cur.execute(
                "DELETE FROM link_routes WHERE chat_id=%s AND keyword=%s",
                (chat_id, keyword.lower().strip()),
            )
            deleted = cur.rowcount > 0
        self.conn.commit()
        return deleted

    def upsert_participation_gate(self, chat_id: int, gate_group_id: int, gate_title: str, join_url: str) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO participation_gates(chat_id, gate_group_id, gate_title, join_url, enabled)
                VALUES (%s, %s, %s, %s, TRUE)
                ON CONFLICT(chat_id, gate_group_id) DO UPDATE SET
                  gate_title=EXCLUDED.gate_title,
                  join_url=EXCLUDED.join_url,
                  enabled=TRUE
                """,
                (chat_id, gate_group_id, gate_title, join_url),
            )
        self.conn.commit()

    def list_participation_gates(self, chat_id: int) -> list[ParticipationGate]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT chat_id, gate_group_id, gate_title, join_url, enabled
                FROM participation_gates
                WHERE chat_id=%s
                ORDER BY gate_title ASC
                """,
                (chat_id,),
            )
            rows = cur.fetchall()
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
        with self.conn.cursor() as cur:
            cur.execute(
                "DELETE FROM participation_gates WHERE chat_id=%s AND gate_group_id=%s",
                (chat_id, gate_group_id),
            )
            deleted = cur.rowcount > 0
        self.conn.commit()
        return deleted
