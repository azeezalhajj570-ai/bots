from __future__ import annotations

import logging
from typing import Any

from telegram import Update
from telegram.ext import ContextTypes

from ...core.decisions import Decision
from ...storage import FeatureSettingsRepo
from ...telegram_helpers import is_group_chat

log = logging.getLogger(__name__)


class AntiBotsFeature:
    key = "anti_bots"

    def __init__(self, db: FeatureSettingsRepo) -> None:
        self.db = db

    async def collect(self, update: Update, context: ContextTypes.DEFAULT_TYPE, bag: dict[str, Any]) -> None:
        del context
        msg = update.message
        chat = update.effective_chat
        if not msg or not chat:
            return
        if not is_group_chat(update):
            return

        chat_id = chat.id
        if not self.db.get_setting(chat_id, "anti_bots"):
            return

        bot_members = [member for member in (msg.new_chat_members or []) if member.is_bot]
        if not bot_members:
            return

        bag["ban_user_ids"] = [member.id for member in bot_members]
        bag["ban_display_names"] = [member.mention_html() for member in bot_members]
        log.info("Detected joining bots chat=%s ids=%s", chat_id, bag["ban_user_ids"])

    async def decide(self, update: Update, context: ContextTypes.DEFAULT_TYPE, bag: dict[str, Any]) -> Decision | None:
        del update
        del context
        if not bag.get("ban_user_ids"):
            return None
        return Decision(ban=True, reason="anti_bots", score=100)

