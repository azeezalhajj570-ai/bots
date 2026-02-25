from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

from ..db import DB
from ..telegram_helpers import bot_can_ban

log = logging.getLogger(__name__)


def make_anti_bots_handler(db: DB):
    async def anti_bots_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        msg = update.message
        if not msg or not update.effective_chat:
            return

        chat_id = update.effective_chat.id

        if not db.get_setting(chat_id, "anti_bots"):
            return

        new_members = msg.new_chat_members or []
        if not new_members:
            return

        if not await bot_can_ban(context, chat_id):
            log.warning("Bot cannot ban in chat=%s. Needs can_restrict_members.", chat_id)
            return

        for m in new_members:
            if m.is_bot:
                try:
                    await context.bot.ban_chat_member(chat_id, m.id)
                    await msg.reply_text(f"🤖🚫 تم حظر بوت تلقائيًا: {m.mention_html()}", parse_mode="HTML")
                    log.info("Banned bot %s in chat=%s", m.id, chat_id)
                except Exception as e:
                    log.error("Failed banning bot %s in chat=%s: %s", m.id, chat_id, e)

    return anti_bots_handler

