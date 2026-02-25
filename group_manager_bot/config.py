from __future__ import annotations

import os
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    bot_token: str
    db_path: str = "bot.db"
    max_warns: int = 3
    mute_seconds: int = 60 * 60  # 1 hour
    test_mode: bool = False
    # Detect http(s), t.me, telegram.me, joinchat (NOT @mentions by default)
    link_re: re.Pattern[str] = re.compile(r"(https?://|t\.me/|telegram\.me/|joinchat/)", re.IGNORECASE)


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_config() -> Config:
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise SystemExit("❌ BOT_TOKEN missing in .env")

    db_path = os.getenv("DB_PATH", "bot.db")
    max_warns = int(os.getenv("MAX_WARNS", "3"))
    mute_seconds = int(os.getenv("MUTE_SECONDS", str(60 * 60)))
    test_mode = _as_bool(os.getenv("TEST_MODE", "0"))
    return Config(
        bot_token=token,
        db_path=db_path,
        max_warns=max_warns,
        mute_seconds=mute_seconds,
        test_mode=test_mode,
    )
