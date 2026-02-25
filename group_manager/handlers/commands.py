from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

from group_manager.context import get_db
from group_manager.helpers import is_admin, is_group_chat
from group_manager.ui import build_settings_keyboard, settings_text

logger = logging.getLogger(__name__)


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    logger.info("/start user=%s chat=%s", update.effective_user.id if update.effective_user else None, update.effective_chat.id if update.effective_chat else None)
    await update.message.reply_text(
        "Bot is running.\n"
        "Use /settings in a group.\n\n"
        "Required bot permissions:\n"
        "- Delete messages\n"
        "- Ban/Restrict users"
    )


async def settings_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_chat or not update.effective_user:
        return

    if not is_group_chat(update):
        await update.message.reply_text("Use this command inside a group or supergroup.")
        return

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if not await is_admin(context, chat_id, user_id):
        await update.message.reply_text("Settings are for admins only.")
        return

    db = get_db(context)
    db.ensure_group(chat_id)
    logger.info("/settings opened chat=%s admin=%s", chat_id, user_id)
    await update.message.reply_text(
        settings_text(chat_id, db),
        reply_markup=build_settings_keyboard(chat_id, db),
        disable_web_page_preview=True,
    )


async def resetwarns_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_chat or not update.effective_user:
        return

    if not is_group_chat(update):
        await update.message.reply_text("Use this command in a group.")
        return

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if not await is_admin(context, chat_id, user_id):
        await update.message.reply_text("Admins only.")
        return

    if not update.message.reply_to_message or not update.message.reply_to_message.from_user:
        await update.message.reply_text("Reply to the user message then run /resetwarns")
        return

    target_id = update.message.reply_to_message.from_user.id
    db = get_db(context)
    db.reset_warns(chat_id, target_id)
    logger.info("Warnings reset chat=%s admin=%s target=%s", chat_id, user_id, target_id)
    await update.message.reply_text("Warnings reset.")
