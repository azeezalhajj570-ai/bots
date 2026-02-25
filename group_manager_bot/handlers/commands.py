from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

from ..db import DB
from ..keyboards import build_settings_keyboard, settings_text
from ..telegram_helpers import is_admin, is_group_chat

log = logging.getLogger(__name__)


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    await update.message.reply_text(
        "Bot is running.\n"
        "Use /settings inside the group.\n\n"
        "Required bot permissions:\n"
        "- Delete messages\n"
        "- Ban/Restrict users"
    )


def _is_sender_chat_message(update: Update) -> bool:
    if not update.message:
        return False
    return update.message.sender_chat is not None


def make_settings_cmd(db: DB):
    async def settings_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not update.effective_chat:
            return

        if not is_group_chat(update):
            await update.message.reply_text("Use this command inside a group/supergroup.")
            return

        chat_id = update.effective_chat.id
        user_id = update.effective_user.id if update.effective_user else None

        is_sender_chat = _is_sender_chat_message(update)
        is_user_group_admin = bool(user_id and await is_admin(context, chat_id, user_id))
        member_status = None
        sender_chat_id = update.message.sender_chat.id if update.message.sender_chat else None
        if user_id:
            try:
                member_status = (await context.bot.get_chat_member(chat_id, user_id)).status
            except Exception as exc:
                log.warning("Settings status check failed chat=%s user=%s error=%s", chat_id, user_id, exc)
        if not (is_sender_chat or is_user_group_admin):
            log.info(
                "Settings denied chat=%s user=%s status=%s sender_chat=%s",
                chat_id,
                user_id,
                member_status,
                sender_chat_id,
            )
            await update.message.reply_text("Settings panel is for group admins only.")
            return

        db.ensure_group(chat_id)
        await update.message.reply_text(
            settings_text(db, chat_id),
            reply_markup=build_settings_keyboard(db, chat_id),
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )

    return settings_cmd


def make_resetwarns_cmd(db: DB):
    async def resetwarns_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not update.effective_chat:
            return

        if not is_group_chat(update):
            await update.message.reply_text("Use this command inside the group.")
            return

        chat_id = update.effective_chat.id
        user_id = update.effective_user.id if update.effective_user else None

        is_sender_chat = _is_sender_chat_message(update)
        is_user_group_admin = bool(user_id and await is_admin(context, chat_id, user_id))
        member_status = None
        sender_chat_id = update.message.sender_chat.id if update.message.sender_chat else None
        if user_id:
            try:
                member_status = (await context.bot.get_chat_member(chat_id, user_id)).status
            except Exception as exc:
                log.warning("Resetwarns status check failed chat=%s user=%s error=%s", chat_id, user_id, exc)
        if not (is_sender_chat or is_user_group_admin):
            log.info(
                "Resetwarns denied chat=%s user=%s status=%s sender_chat=%s",
                chat_id,
                user_id,
                member_status,
                sender_chat_id,
            )
            await update.message.reply_text("Admins only.")
            return

        if not update.message.reply_to_message or not update.message.reply_to_message.from_user:
            await update.message.reply_text("Reply to the user message, then run /resetwarns.")
            return

        target_id = update.message.reply_to_message.from_user.id
        db.reset_warns(chat_id, target_id)
        log.info("Warns reset chat=%s target=%s by=%s", chat_id, target_id, user_id)
        await update.message.reply_text("Warnings reset.")

    return resetwarns_cmd
