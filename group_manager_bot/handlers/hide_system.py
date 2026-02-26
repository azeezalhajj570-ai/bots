from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

from ..storage import FeatureSettingsRepo
from ..telegram_helpers import bot_can_delete, is_group_chat

log = logging.getLogger(__name__)


def make_hide_system_handler(db: FeatureSettingsRepo):
    async def hide_system_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        msg = update.message
        chat = update.effective_chat
        if not msg or not chat:
            return
        if not is_group_chat(update):
            return
        if not db.get_setting(chat.id, "hide_system"):
            return

        is_join_leave = bool(msg.new_chat_members or msg.left_chat_member)
        if not is_join_leave:
            return

        if not await bot_can_delete(context, chat.id):
            log.warning("Cannot hide system messages chat=%s: missing delete permission", chat.id)
            return
        try:
            await msg.delete()
        except Exception as exc:
            log.error("Failed hiding system message chat=%s msg=%s error=%s", chat.id, msg.id, exc)

    return hide_system_handler

