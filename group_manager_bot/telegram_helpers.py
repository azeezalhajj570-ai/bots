from __future__ import annotations

import logging
from typing import Optional

from telegram import Update
from telegram.constants import ChatMemberStatus
from telegram.ext import ContextTypes

from .cache import Cache

log = logging.getLogger(__name__)

MEMBER_STATUS_TTL = 20
ADMINS_LIST_TTL = 30
BOT_PERMS_TTL = 20
USER_MUTED_TTL = 20
MEMBERSHIP_TTL = 30


def is_group_chat(update: Update) -> bool:
    return bool(update.effective_chat and update.effective_chat.type in ("group", "supergroup"))


def _cache(context: ContextTypes.DEFAULT_TYPE) -> Optional[Cache]:
    return context.application.bot_data.get("cache")


async def get_member_status(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    user_id: int,
) -> Optional[str]:
    cache = _cache(context)
    cache_key = f"member_status:{chat_id}:{user_id}"
    if cache:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

    try:
        m = await context.bot.get_chat_member(chat_id, user_id)
        if cache:
            cache.set(cache_key, m.status, MEMBER_STATUS_TTL)
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

    cache = _cache(context)
    cache_key = f"admins:{chat_id}"
    if cache:
        cached_admin_ids = cache.get(cache_key)
        if cached_admin_ids is not None:
            return user_id in cached_admin_ids

    try:
        admins = await context.bot.get_chat_administrators(chat_id)
        admin_ids = {admin.user.id for admin in admins if admin.user}
        if cache:
            cache.set(cache_key, admin_ids, ADMINS_LIST_TTL)
        return user_id in admin_ids
    except Exception as e:
        log.warning("get_chat_administrators failed chat=%s user=%s: %s", chat_id, user_id, e)
        return False


async def bot_can_delete(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
) -> bool:
    cache = _cache(context)
    cache_key = f"bot_can_delete:{chat_id}"
    if cache:
        cached = cache.get(cache_key)
        if cached is not None:
            return bool(cached)

    try:
        bot_id = context.bot.id
        bm = await context.bot.get_chat_member(chat_id, bot_id)
        if bm.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
            if cache:
                cache.set(cache_key, False, BOT_PERMS_TTL)
            return False
        can_delete = bool(getattr(bm, "can_delete_messages", True))
        if cache:
            cache.set(cache_key, can_delete, BOT_PERMS_TTL)
        return can_delete
    except Exception as e:
        log.warning("bot_can_delete check failed: %s", e)
        return False


async def bot_can_ban(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
) -> bool:
    cache = _cache(context)
    cache_key = f"bot_can_ban:{chat_id}"
    if cache:
        cached = cache.get(cache_key)
        if cached is not None:
            return bool(cached)

    try:
        bot_id = context.bot.id
        bm = await context.bot.get_chat_member(chat_id, bot_id)
        if bm.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
            if cache:
                cache.set(cache_key, False, BOT_PERMS_TTL)
            return False
        can_ban = bool(getattr(bm, "can_restrict_members", True))
        if cache:
            cache.set(cache_key, can_ban, BOT_PERMS_TTL)
        return can_ban
    except Exception as e:
        log.warning("bot_can_ban check failed: %s", e)
        return False


async def is_user_muted(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    user_id: int,
) -> bool:
    cache = _cache(context)
    cache_key = f"user_muted:{chat_id}:{user_id}"
    if cache:
        cached = cache.get(cache_key)
        if cached is not None:
            return bool(cached)

    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
    except Exception as exc:
        log.warning("Mute-state check failed chat=%s user=%s error=%s", chat_id, user_id, exc)
        return False

    status = str(member.status).lower()
    can_send = getattr(member, "can_send_messages", True)
    muted = status == "restricted" and can_send is False
    if cache:
        cache.set(cache_key, muted, USER_MUTED_TTL)
    return muted


async def is_member_of_chat(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    user_id: int,
) -> bool:
    cache = _cache(context)
    cache_key = f"membership:{chat_id}:{user_id}"
    if cache:
        cached = cache.get(cache_key)
        if cached is not None:
            return bool(cached)

    status = await get_member_status(context, chat_id, user_id)
    normalized = str(status).lower() if status is not None else ""
    is_member = normalized in {
        "member",
        "administrator",
        "owner",
        "creator",
        "restricted",
        str(ChatMemberStatus.MEMBER).lower(),
        str(ChatMemberStatus.ADMINISTRATOR).lower(),
        str(ChatMemberStatus.OWNER).lower(),
        str(ChatMemberStatus.RESTRICTED).lower(),
    }
    if cache:
        cache.set(cache_key, is_member, MEMBERSHIP_TTL)
    return is_member
