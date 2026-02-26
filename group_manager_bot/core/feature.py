from __future__ import annotations

from typing import Any, Protocol

from telegram import Update
from telegram.ext import ContextTypes

from .decisions import Decision


class Feature(Protocol):
    key: str

    async def collect(self, update: Update, context: ContextTypes.DEFAULT_TYPE, bag: dict[str, Any]) -> None: ...
    async def decide(self, update: Update, context: ContextTypes.DEFAULT_TYPE, bag: dict[str, Any]) -> Decision | None: ...

