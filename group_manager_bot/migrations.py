from __future__ import annotations

import logging
import re
import sqlite3
from pathlib import Path

log = logging.getLogger(__name__)

_MIGRATION_RE = re.compile(r"^(\d+)_.*\.sql$")


def _ensure_version_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_version(
          version INTEGER PRIMARY KEY,
          applied_at INTEGER NOT NULL
        )
        """
    )


def _current_version(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COALESCE(MAX(version), 0) FROM schema_version").fetchone()
    return int(row[0]) if row else 0


def _migration_files() -> list[tuple[int, Path]]:
    migrations_dir = Path(__file__).with_name("migrations")
    files: list[tuple[int, Path]] = []
    for path in migrations_dir.glob("*.sql"):
        match = _MIGRATION_RE.match(path.name)
        if not match:
            continue
        files.append((int(match.group(1)), path))
    files.sort(key=lambda item: item[0])
    return files


def apply_migrations(conn: sqlite3.Connection) -> None:
    _ensure_version_table(conn)
    current = _current_version(conn)

    for version, path in _migration_files():
        if version <= current:
            continue
        sql = path.read_text(encoding="utf-8")
        conn.executescript(sql)
        conn.execute(
            "INSERT INTO schema_version(version, applied_at) VALUES (?, CAST(strftime('%s','now') AS INTEGER))",
            (version,),
        )
        conn.commit()
        log.info("Applied migration %s (%s)", version, path.name)

