from __future__ import annotations

import logging

from telegram import Update
from telegram.constants import ChatMemberStatus
from telegram.ext import ContextTypes

from group_manager.context import get_db
from group_manager.ui import build_settings_keyboard, settings_text

logger = logging.getLogger(__name__)


async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.message:
        return

    data = query.data or ""
    parts = data.split(":")
    if len(parts) < 2:
        await query.answer()
        return

    action = parts[0]
    chat_id = int(parts[-1])

    member = await context.bot.get_chat_member(chat_id, query.from_user.id)
    if member.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
        await query.answer("Admins only.", show_alert=True)
        return

    db = get_db(context)
    await query.answer()

    if action == "toggle" and len(parts) == 3:
        key = parts[1]
        if key not in ("anti_links", "anti_bots"):
            return
        new_value = db.toggle_setting(chat_id, key)
        logger.info("Setting changed chat=%s key=%s value=%s by=%s", chat_id, key, new_value, query.from_user.id)
        await query.edit_message_text(
            settings_text(chat_id, db),
            reply_markup=build_settings_keyboard(chat_id, db),
            disable_web_page_preview=True,
        )
        return

    if action == "refresh":
        await query.edit_message_text(
            settings_text(chat_id, db),
            reply_markup=build_settings_keyboard(chat_id, db),
            disable_web_page_preview=True,
        )
        return

    if action == "close":
        try:
            await query.message.delete()
        except Exception as exc:
            logger.warning("Failed to close settings panel chat=%s error=%s", chat_id, exc)
