from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

log = logging.getLogger(__name__)


def _normalize_text(text: str) -> str:
    compact = " ".join(text.split())
    if len(compact) <= 500:
        return compact
    return compact[:497] + "..."


async def log_group_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    msg = update.message
    chat = update.effective_chat
    user = update.effective_user
    if not msg or not chat or not user:
        return

    text = msg.text or msg.caption
    if not text:
        return

    log.info(
        "Incoming message chat=%s user=%s msg=%s text=%r",
        chat.id,
        user.id,
        msg.id,
        _normalize_text(text),
    )

