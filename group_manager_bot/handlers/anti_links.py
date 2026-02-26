from __future__ import annotations

import logging
import time

from telegram import ChatPermissions, Update
from telegram.ext import ContextTypes

from ..config import Config
from ..storage import BotRepository
from ..telegram_helpers import bot_can_ban, bot_can_delete, is_admin, is_group_chat, is_user_muted

log = logging.getLogger(__name__)


def _format_mute_duration(seconds: int) -> str:
    if seconds % 3600 == 0:
        hours = seconds // 3600
        return f"{hours}h"
    if seconds % 60 == 0:
        minutes = seconds // 60
        return f"{minutes}m"
    return f"{seconds}s"

def make_anti_links_handler(cfg: Config, db: BotRepository):
    async def anti_links_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        msg = update.message
        if not msg or not update.effective_chat or not msg.from_user:
            return

        if not is_group_chat(update):
            return

        chat_id = update.effective_chat.id
        user = msg.from_user
        sender_chat = msg.sender_chat
        display_name = f"@{user.username}" if user.username else user.mention_html()
        text = (msg.text or msg.caption or "").strip()
        if not text:
            return

        if not cfg.test_mode and not db.get_setting(chat_id, "anti_links"):
            return

        if not cfg.test_mode and text.startswith("/"):
            return

        if not cfg.test_mode and user.is_bot:
            return

        if not cfg.test_mode and await is_admin(context, chat_id, user.id):
            return

        if not cfg.link_re.search(text):
            return

        log.info(
            "Link detected chat=%s user=%s msg=%s test_mode=%s",
            chat_id,
            user.id,
            msg.id,
            cfg.test_mode,
        )

        if not await bot_can_delete(context, chat_id):
            log.warning("Bot cannot delete in chat=%s. Needs admin + delete permission.", chat_id)
            return

        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=msg.id)
            log.info("Link message deleted chat=%s user=%s msg=%s", chat_id, user.id, msg.id)
        except Exception as exc:
            log.error("Delete failed chat=%s msg=%s error=%s", chat_id, msg.id, exc)
            return

        existing_warns = db.get_warns(chat_id, user.id)
        if existing_warns > cfg.max_warns:
            db.set_warns(chat_id, user.id, cfg.max_warns)
            existing_warns = cfg.max_warns

        if existing_warns >= cfg.max_warns:
            warns = cfg.max_warns
            log.info("Warn capped chat=%s user=%s warns=%s", chat_id, user.id, warns)
            if sender_chat:
                await context.bot.send_message(
                    chat_id,
                    f"Link removed {display_name}. Warnings: {warns}/{cfg.max_warns}. "
                    "Cannot mute anonymous sender-chat identity.",
                    parse_mode="HTML",
                )
                return

            if not await is_user_muted(context, chat_id, user.id):
                if not await bot_can_ban(context, chat_id):
                    await context.bot.send_message(
                        chat_id,
                        f"Link removed {display_name}. Warnings: {warns}/{cfg.max_warns}. "
                        "I cannot mute without Ban/Restrict permission.",
                        parse_mode="HTML",
                    )
                    return
                until = int(time.time()) + cfg.mute_seconds
                mute_for = _format_mute_duration(cfg.mute_seconds)
                try:
                    await context.bot.restrict_chat_member(
                        chat_id=chat_id,
                        user_id=user.id,
                        permissions=ChatPermissions(can_send_messages=False),
                        until_date=until,
                    )
                    cache = context.application.bot_data.get("cache")
                    if cache:
                        cache.delete(f"user_muted:{chat_id}:{user.id}")
                    await context.bot.send_message(
                        chat_id,
                        f"{display_name} muted for {mute_for} due to repeated links. Warnings: {warns}/{cfg.max_warns}",
                        parse_mode="HTML",
                    )
                    log.info("User muted from capped-warn state chat=%s user=%s", chat_id, user.id)
                    return
                except Exception as exc:
                    log.error("Restrict failed chat=%s user=%s error=%s", chat_id, user.id, exc)

            await context.bot.send_message(
                chat_id,
                f"Link removed {display_name}. Warnings: {warns}/{cfg.max_warns}.",
                parse_mode="HTML",
            )
            return

        warns = db.add_warn(chat_id, user.id)
        log.info("Warn added chat=%s user=%s warns=%s", chat_id, user.id, warns)

        if warns < cfg.max_warns:
            await context.bot.send_message(
                chat_id,
                f"No links allowed {display_name}. Warnings: {warns}/{cfg.max_warns}",
                parse_mode="HTML",
            )
            return

        if not await bot_can_ban(context, chat_id):
            await context.bot.send_message(
                chat_id,
                f"Link removed {display_name}. Warnings: {warns}/{cfg.max_warns}. "
                "I cannot mute without Ban/Restrict permission.",
                parse_mode="HTML",
            )
            return

        until = int(time.time()) + cfg.mute_seconds
        mute_for = _format_mute_duration(cfg.mute_seconds)
        try:
            await context.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user.id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=until,
            )
            cache = context.application.bot_data.get("cache")
            if cache:
                cache.delete(f"user_muted:{chat_id}:{user.id}")
            await context.bot.send_message(
                chat_id,
                f"{display_name} muted for {mute_for} due to repeated links. Warnings: {warns}/{cfg.max_warns}",
                parse_mode="HTML",
            )
            log.info("User muted chat=%s user=%s", chat_id, user.id)
        except Exception as exc:
            log.error("Restrict failed chat=%s user=%s error=%s", chat_id, user.id, exc)
            await context.bot.send_message(
                chat_id,
                f"Link removed for {display_name}. Could not mute user. Warnings: {warns}/{cfg.max_warns}",
                parse_mode="HTML",
            )

    return anti_links_handler
