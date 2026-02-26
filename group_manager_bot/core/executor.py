from __future__ import annotations

import logging
import time
from typing import Any

from telegram import ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from ..storage import BotRepository
from ..telegram_helpers import bot_can_ban, bot_can_delete, is_user_muted
from .decisions import Decision

log = logging.getLogger(__name__)


def _format_mute_duration(seconds: int) -> str:
    if seconds % 3600 == 0:
        return f"{seconds // 3600}h"
    if seconds % 60 == 0:
        return f"{seconds // 60}m"
    return f"{seconds}s"


class Executor:
    def __init__(self, db: BotRepository) -> None:
        self.db = db

    async def _send_warning(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        chat_id: int,
        user_id: int,
        text: str,
    ) -> None:
        send_dm = self.db.get_setting(chat_id, "warn_in_dm")
        send_group = self.db.get_setting(chat_id, "warn_in_group")

        if not send_dm and not send_group:
            send_group = True

        dm_sent = False
        if send_dm:
            try:
                await context.bot.send_message(user_id, text, parse_mode="HTML", disable_web_page_preview=True)
                dm_sent = True
            except Exception:
                dm_sent = False

        if send_group or (send_dm and not dm_sent):
            await context.bot.send_message(chat_id, text, parse_mode="HTML", disable_web_page_preview=True)

    async def apply(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        bag: dict[str, Any],
        decision: Decision,
    ) -> None:
        msg = update.message
        chat = update.effective_chat
        if not msg or not chat:
            return

        chat_id = chat.id
        if decision.public_reply_text:
            reply_markup = None
            if decision.public_reply_buttons:
                rows = [[InlineKeyboardButton(text, url=url)] for text, url in decision.public_reply_buttons]
                reply_markup = InlineKeyboardMarkup(rows)
            await context.bot.send_message(
                chat_id,
                decision.public_reply_text,
                disable_web_page_preview=True,
                reply_markup=reply_markup,
            )

        if decision.ban:
            target_user_ids: list[int] = bag.get("ban_user_ids", [])
            if target_user_ids:
                if not await bot_can_ban(context, chat_id):
                    log.warning("Bot cannot ban in chat=%s. Needs can_restrict_members.", chat_id)
                    return
                for target_user_id in target_user_ids:
                    try:
                        await context.bot.ban_chat_member(chat_id, target_user_id)
                        log.info("Banned bot chat=%s user=%s", chat_id, target_user_id)
                    except Exception as exc:
                        log.error("Failed to ban bot chat=%s user=%s error=%s", chat_id, target_user_id, exc)

        if not decision.delete:
            return

        user = msg.from_user
        if not user:
            return
        user_id = user.id
        display_name = bag.get("display_name") or (f"@{user.username}" if user.username else user.mention_html())
        max_warns = int(bag.get("max_warns", 3))
        mute_seconds = int(decision.mute_seconds or 3600)
        sender_chat = bag.get("sender_chat")

        if not await bot_can_delete(context, chat_id):
            log.warning("Bot cannot delete in chat=%s. Needs admin + delete permission.", chat_id)
            return

        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=msg.id)
            log.info("Link message deleted chat=%s user=%s msg=%s", chat_id, user_id, msg.id)
        except Exception as exc:
            log.error("Delete failed chat=%s msg=%s error=%s", chat_id, msg.id, exc)
            return

        if not decision.warn:
            return

        existing_warns = self.db.get_warns(chat_id, user_id)
        if existing_warns > max_warns:
            self.db.set_warns(chat_id, user_id, max_warns)
            existing_warns = max_warns

        if existing_warns >= max_warns:
            warns = max_warns
            log.info("Warn capped chat=%s user=%s warns=%s", chat_id, user_id, warns)
            if sender_chat:
                await context.bot.send_message(
                    chat_id,
                    f"Link removed {display_name}. Warnings: {warns}/{max_warns}. Cannot mute anonymous sender-chat identity.",
                    parse_mode="HTML",
                )
                return

            if not await is_user_muted(context, chat_id, user_id):
                if not await bot_can_ban(context, chat_id):
                    await self._send_warning(
                        context,
                        chat_id,
                        user_id,
                        f"Link removed {display_name}. Warnings: {warns}/{max_warns}. I cannot mute without Ban/Restrict permission.",
                    )
                    return

                until = int(time.time()) + mute_seconds
                try:
                    await context.bot.restrict_chat_member(
                        chat_id=chat_id,
                        user_id=user_id,
                        permissions=ChatPermissions(can_send_messages=False),
                        until_date=until,
                    )
                    cache = context.application.bot_data.get("cache")
                    if cache:
                        cache.delete(f"user_muted:{chat_id}:{user_id}")
                    await context.bot.send_message(
                        chat_id,
                        f"{display_name} muted for {_format_mute_duration(mute_seconds)} due to repeated links. Warnings: {warns}/{max_warns}",
                        parse_mode="HTML",
                    )
                    log.info("User muted from capped-warn state chat=%s user=%s", chat_id, user_id)
                    return
                except Exception as exc:
                    log.error("Restrict failed chat=%s user=%s error=%s", chat_id, user_id, exc)

            await self._send_warning(
                context,
                chat_id,
                user_id,
                f"Link removed {display_name}. Warnings: {warns}/{max_warns}.",
            )
            return

        warns = self.db.add_warn(chat_id, user_id)
        log.info("Warn added chat=%s user=%s warns=%s", chat_id, user_id, warns)

        if warns < max_warns:
            await self._send_warning(
                context,
                chat_id,
                user_id,
                f"No links allowed {display_name}. Warnings: {warns}/{max_warns}",
            )
            return

        if not await bot_can_ban(context, chat_id):
            await self._send_warning(
                context,
                chat_id,
                user_id,
                f"Link removed {display_name}. Warnings: {warns}/{max_warns}. I cannot mute without Ban/Restrict permission.",
            )
            return

        until = int(time.time()) + mute_seconds
        try:
            await context.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=until,
            )
            cache = context.application.bot_data.get("cache")
            if cache:
                cache.delete(f"user_muted:{chat_id}:{user_id}")
            await context.bot.send_message(
                chat_id,
                f"{display_name} muted for {_format_mute_duration(mute_seconds)} due to repeated links. Warnings: {warns}/{max_warns}",
                parse_mode="HTML",
            )
            log.info("User muted chat=%s user=%s", chat_id, user_id)
        except Exception as exc:
            log.error("Restrict failed chat=%s user=%s error=%s", chat_id, user_id, exc)
            await self._send_warning(
                context,
                chat_id,
                user_id,
                f"Link removed for {display_name}. Could not mute user. Warnings: {warns}/{max_warns}",
            )
