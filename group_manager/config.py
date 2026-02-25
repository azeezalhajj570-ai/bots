from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    max_warns: int = 3
    mute_seconds: int = 60 * 60
    link_re: re.Pattern[str] = field(
        default_factory=lambda: re.compile(
            r"(https?://|t\.me/|telegram\.me/|joinchat/)",
            re.IGNORECASE,
        )
    )


def load_token() -> str:
    load_dotenv()
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise SystemExit("BOT_TOKEN missing in .env")
    return token
