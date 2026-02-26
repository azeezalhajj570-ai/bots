from __future__ import annotations

import argparse
import sqlite3
from typing import Any

import psycopg


def _fetch_all_sqlite(conn: sqlite3.Connection, query: str) -> list[tuple[Any, ...]]:
    cur = conn.execute(query)
    return cur.fetchall()


def migrate(sqlite_path: str, database_url: str) -> None:
    sqlite_conn = sqlite3.connect(sqlite_path)
    pg_conn = psycopg.connect(database_url)

    try:
        with pg_conn.cursor() as cur:
            # group_settings
            for row in _fetch_all_sqlite(
                sqlite_conn,
                """
                SELECT chat_id, anti_links, anti_bots, hide_system, warn_in_dm, warn_in_group
                FROM group_settings
                """,
            ):
                cur.execute(
                    """
                    INSERT INTO group_settings(chat_id, anti_links, anti_bots, hide_system, warn_in_dm, warn_in_group)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT(chat_id) DO UPDATE SET
                      anti_links=EXCLUDED.anti_links,
                      anti_bots=EXCLUDED.anti_bots,
                      hide_system=EXCLUDED.hide_system,
                      warn_in_dm=EXCLUDED.warn_in_dm,
                      warn_in_group=EXCLUDED.warn_in_group
                    """,
                    (
                        int(row[0]),
                        bool(row[1]),
                        bool(row[2]),
                        bool(row[3]),
                        bool(row[4]),
                        bool(row[5]),
                    ),
                )

            # warnings
            for row in _fetch_all_sqlite(sqlite_conn, "SELECT chat_id, user_id, warns FROM warnings"):
                cur.execute(
                    """
                    INSERT INTO warnings(chat_id, user_id, warns)
                    VALUES (%s, %s, %s)
                    ON CONFLICT(chat_id, user_id) DO UPDATE SET warns=EXCLUDED.warns
                    """,
                    (int(row[0]), int(row[1]), int(row[2])),
                )

            # dynamic_remove_rules
            max_rule_id = 0
            for row in _fetch_all_sqlite(
                sqlite_conn,
                "SELECT id, chat_id, pattern, enabled FROM dynamic_remove_rules",
            ):
                rule_id = int(row[0])
                max_rule_id = max(max_rule_id, rule_id)
                cur.execute(
                    """
                    INSERT INTO dynamic_remove_rules(id, chat_id, pattern, enabled)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT(id) DO UPDATE SET
                      chat_id=EXCLUDED.chat_id,
                      pattern=EXCLUDED.pattern,
                      enabled=EXCLUDED.enabled
                    """,
                    (rule_id, int(row[1]), str(row[2]), bool(row[3])),
                )

            if max_rule_id > 0:
                cur.execute(
                    "SELECT setval(pg_get_serial_sequence('dynamic_remove_rules', 'id'), %s, true)",
                    (max_rule_id,),
                )

            # link_routes
            for row in _fetch_all_sqlite(
                sqlite_conn,
                "SELECT chat_id, keyword, destination, gate_group_id, enabled FROM link_routes",
            ):
                cur.execute(
                    """
                    INSERT INTO link_routes(chat_id, keyword, destination, gate_group_id, enabled)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT(chat_id, keyword) DO UPDATE SET
                      destination=EXCLUDED.destination,
                      gate_group_id=EXCLUDED.gate_group_id,
                      enabled=EXCLUDED.enabled
                    """,
                    (
                        int(row[0]),
                        str(row[1]),
                        str(row[2]),
                        int(row[3]) if row[3] is not None else None,
                        bool(row[4]),
                    ),
                )

            # participation_gates
            for row in _fetch_all_sqlite(
                sqlite_conn,
                "SELECT chat_id, gate_group_id, gate_title, join_url, enabled FROM participation_gates",
            ):
                cur.execute(
                    """
                    INSERT INTO participation_gates(chat_id, gate_group_id, gate_title, join_url, enabled)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT(chat_id, gate_group_id) DO UPDATE SET
                      gate_title=EXCLUDED.gate_title,
                      join_url=EXCLUDED.join_url,
                      enabled=EXCLUDED.enabled
                    """,
                    (int(row[0]), int(row[1]), str(row[2]), str(row[3]), bool(row[4])),
                )

        pg_conn.commit()
    finally:
        sqlite_conn.close()
        pg_conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate bot data from SQLite to PostgreSQL.")
    parser.add_argument("--sqlite-path", required=True, help="Path to SQLite database file (bot.db)")
    parser.add_argument("--database-url", required=True, help="PostgreSQL DATABASE_URL")
    args = parser.parse_args()
    migrate(args.sqlite_path, args.database_url)
    print("Migration completed successfully.")


if __name__ == "__main__":
    main()
