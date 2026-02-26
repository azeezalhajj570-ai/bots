from __future__ import annotations

import os
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    bot_token: str
    db_path: str = "bot.db"
    database_url: str | None = None
    max_warns: int = 3
    mute_seconds: int = 60 * 60  # 1 hour
    test_mode: bool = False
    odoo_api_base_url: str | None = None
    odoo_api_token: str | None = None
    odoo_api_timeout_seconds: int = 10
    odoo_cache_ttl_seconds: int = 30
    bot_read_api_enabled: bool = False
    bot_read_api_host: str = "0.0.0.0"
    bot_read_api_port: int = 8080
    bot_read_api_token: str | None = None
    # Detect http(s), t.me, telegram.me, joinchat (NOT @mentions by default)
    link_re: re.Pattern[str] = re.compile(r"(https?://|t\.me/|telegram\.me/|joinchat/)", re.IGNORECASE)


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_config() -> Config:
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise SystemExit("❌ BOT_TOKEN missing in .env")

    db_path = os.getenv("DB_PATH", "bot.db")
    database_url = os.getenv("DATABASE_URL", "").strip() or None
    max_warns = int(os.getenv("MAX_WARNS", "3"))
    mute_seconds = int(os.getenv("MUTE_SECONDS", str(60 * 60)))
    test_mode = _as_bool(os.getenv("TEST_MODE", "0"))
    odoo_api_base_url = os.getenv("ODOO_API_BASE_URL", "").strip() or None
    odoo_api_token = os.getenv("ODOO_API_TOKEN", "").strip() or None
    odoo_api_timeout_seconds = int(os.getenv("ODOO_API_TIMEOUT_SECONDS", "10"))
    odoo_cache_ttl_seconds = int(os.getenv("ODOO_CACHE_TTL_SECONDS", "30"))
    bot_read_api_enabled = _as_bool(os.getenv("BOT_READ_API_ENABLED", "0"))
    bot_read_api_host = os.getenv("BOT_READ_API_HOST", "0.0.0.0").strip() or "0.0.0.0"
    bot_read_api_port = int(os.getenv("BOT_READ_API_PORT", "8080"))
    bot_read_api_token = os.getenv("BOT_READ_API_TOKEN", "").strip() or None
    return Config(
        bot_token=token,
        db_path=db_path,
        database_url=database_url,
        max_warns=max_warns,
        mute_seconds=mute_seconds,
        test_mode=test_mode,
        odoo_api_base_url=odoo_api_base_url,
        odoo_api_token=odoo_api_token,
        odoo_api_timeout_seconds=odoo_api_timeout_seconds,
        odoo_cache_ttl_seconds=odoo_cache_ttl_seconds,
        bot_read_api_enabled=bot_read_api_enabled,
        bot_read_api_host=bot_read_api_host,
        bot_read_api_port=bot_read_api_port,
        bot_read_api_token=bot_read_api_token,
    )
