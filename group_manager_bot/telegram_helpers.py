from __future__ import annotations

import logging
from typing import Optional

from telegram import Update
from telegram.constants import ChatMemberStatus
from telegram.ext import ContextTypes

log = logging.getLogger(__name__)


def is_group_chat(update: Update) -> bool:
    return bool(update.effective_chat and update.effective_chat.type in ("group", "supergroup"))


async def get_member_status(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    user_id: int,
) -> Optional[str]:
    try:
        m = await context.bot.get_chat_member(chat_id, user_id)
        return m.status
    except Exception as e:
        log.warning("get_chat_member failed chat=%s user=%s: %s", chat_id, user_id, e)
        return None


async def is_admin(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    user_id: int,
) -> bool:
    status = await get_member_status(context, chat_id, user_id)
    if status is not None:
        normalized = str(status).lower()
        if normalized in {
            str(ChatMemberStatus.ADMINISTRATOR).lower(),
            str(ChatMemberStatus.OWNER).lower(),
            "administrator",
            "owner",
            "creator",
        }:
            return True

    try:
        admins = await context.bot.get_chat_administrators(chat_id)
        return any(admin.user and admin.user.id == user_id for admin in admins)
    except Exception as e:
        log.warning("get_chat_administrators failed chat=%s user=%s: %s", chat_id, user_id, e)
        return False


async def bot_can_delete(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
) -> bool:
    try:
        bot_id = context.bot.id
        bm = await context.bot.get_chat_member(chat_id, bot_id)
        if bm.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
            return False
        return bool(getattr(bm, "can_delete_messages", True))
    except Exception as e:
        log.warning("bot_can_delete check failed: %s", e)
        return False


async def bot_can_ban(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
) -> bool:
    try:
        bot_id = context.bot.id
        bm = await context.bot.get_chat_member(chat_id, bot_id)
        if bm.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
            return False
        return bool(getattr(bm, "can_restrict_members", True))
    except Exception as e:
        log.warning("bot_can_ban check failed: %s", e)
        return False
