from __future__ import annotations

import logging
import time

from telegram import ChatPermissions, Update
from telegram.ext import ContextTypes

from group_manager.context import get_config, get_db
from group_manager.helpers import bot_can_ban, bot_can_delete, is_admin, is_group_chat

logger = logging.getLogger(__name__)


async def anti_bots_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if not message or not update.effective_chat:
        return

    chat_id = update.effective_chat.id
    db = get_db(context)

    if not db.get_setting(chat_id, "anti_bots"):
        return

    new_members = message.new_chat_members or []
    if not new_members:
        return

    if not await bot_can_ban(context, chat_id):
        logger.warning("Missing ban/restrict permission in chat=%s", chat_id)
        return

    for member in new_members:
        if not member.is_bot:
            continue
        try:
            await context.bot.ban_chat_member(chat_id, member.id)
            await message.reply_text(f"Bot auto-banned: {member.full_name}")
            logger.info("Bot banned chat=%s bot=%s", chat_id, member.id)
        except Exception as exc:
            logger.error("Failed to ban bot chat=%s bot=%s error=%s", chat_id, member.id, exc)


async def anti_links_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if not message or not update.effective_chat or not message.from_user:
        return

    if not is_group_chat(update):
        return

    chat_id = update.effective_chat.id
    user = message.from_user
    db = get_db(context)
    cfg = get_config(context)

    if not db.get_setting(chat_id, "anti_links"):
        return

    text = (message.text or message.caption or "").strip()
    if not text or text.startswith("/") or user.is_bot:
        return

    if await is_admin(context, chat_id, user.id):
        return

    if not cfg.link_re.search(text):
        return

    logger.info("Link detected chat=%s user=%s", chat_id, user.id)

    if not await bot_can_delete(context, chat_id):
        logger.warning("Missing delete permission in chat=%s", chat_id)
        return

    try:
        await message.delete()
    except Exception as exc:
        logger.error("Failed to delete message chat=%s msg=%s error=%s", chat_id, message.id, exc)
        return

    warns = db.add_warn(chat_id, user.id)
    logger.info("Warn added chat=%s user=%s warns=%s", chat_id, user.id, warns)

    if warns < cfg.max_warns:
        await context.bot.send_message(chat_id, f"No links allowed. Warnings: {warns}/{cfg.max_warns}")
        return

    if not await bot_can_ban(context, chat_id):
        await context.bot.send_message(
            chat_id,
            f"Link removed. Warnings: {warns}/{cfg.max_warns}. I cannot mute without ban/restrict permission.",
        )
        return

    until = int(time.time()) + cfg.mute_seconds
    try:
        await context.bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until,
        )
        await context.bot.send_message(chat_id, f"User muted for repeated links. Warnings: {warns}/{cfg.max_warns}")
        logger.info("User muted chat=%s user=%s", chat_id, user.id)
    except Exception as exc:
        logger.error("Failed to mute user chat=%s user=%s error=%s", chat_id, user.id, exc)
        await context.bot.send_message(chat_id, f"Link removed. Could not mute user. Warnings: {warns}/{cfg.max_warns}")
