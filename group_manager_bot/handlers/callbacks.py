from __future__ import annotations

import logging

from telegram import Update
from telegram.constants import ChatMemberStatus
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from ..db import DB
from ..keyboards import build_settings_keyboard, settings_text

log = logging.getLogger(__name__)


async def _safe_edit_settings(query, chat_id: int, db: DB) -> None:
    try:
        await query.edit_message_text(
            settings_text(db, chat_id),
            reply_markup=build_settings_keyboard(db, chat_id),
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )
    except BadRequest as exc:
        if "Message is not modified" in str(exc):
            return
        raise


def make_callbacks(db: DB):
    async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        q = update.callback_query
        if not q or not q.message:
            return

        data = q.data or ""
        parts = data.split(":")
        if len(parts) < 2:
            return await q.answer()

        action = parts[0]
        chat_id = int(parts[-1])

        member = await context.bot.get_chat_member(chat_id, q.from_user.id)
        if member.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
            return await q.answer("للمشرفين فقط.", show_alert=True)

        await q.answer()

        if action == "toggle" and len(parts) == 3:
            key = parts[1]
            if key not in ("anti_links", "anti_bots"):
                return
            new_val = db.toggle_setting(chat_id, key)
            log.info("Setting changed chat=%s %s=%s by user=%s", chat_id, key, new_val, q.from_user.id)
            await _safe_edit_settings(q, chat_id, db)

        elif action == "refresh":
            await _safe_edit_settings(q, chat_id, db)

        elif action == "close":
            try:
                await q.message.delete()
            except Exception:
                pass

    return callbacks
