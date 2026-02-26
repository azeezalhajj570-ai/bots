from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Decision:
    delete: bool = False
    warn: bool = False
    mute_seconds: int | None = None
    ban: bool = False
    public_reply_text: str | None = None
    public_reply_buttons: list[tuple[str, str]] | None = None
    reason: str = ""
    score: int = 0
