from __future__ import annotations

import logging
from typing import Optional

from telegram import Update
from telegram.constants import ChatMemberStatus
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


def is_group_chat(update: Update) -> bool:
    return bool(update.effective_chat and update.effective_chat.type in ("group", "supergroup"))


async def get_member_status(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    user_id: int,
) -> Optional[str]:
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        return member.status
    except Exception as exc:
        logger.warning("get_chat_member failed chat=%s user=%s error=%s", chat_id, user_id, exc)
        return None


async def is_admin(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    user_id: int,
) -> bool:
    status = await get_member_status(context, chat_id, user_id)
    return status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)


async def bot_can_delete(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> bool:
    try:
        bot_member = await context.bot.get_chat_member(chat_id, context.bot.id)
        if bot_member.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
            return False
        return bool(getattr(bot_member, "can_delete_messages", True))
    except Exception as exc:
        logger.warning("bot_can_delete failed chat=%s error=%s", chat_id, exc)
        return False


async def bot_can_ban(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> bool:
    try:
        bot_member = await context.bot.get_chat_member(chat_id, context.bot.id)
        if bot_member.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
            return False
        return bool(getattr(bot_member, "can_restrict_members", True))
    except Exception as exc:
        logger.warning("bot_can_ban failed chat=%s error=%s", chat_id, exc)
        return False
