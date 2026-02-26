from __future__ import annotations

import logging
from typing import Any

from telegram import Update
from telegram.ext import ContextTypes

from ...config import Config
from ...storage import BotRepository
from ...telegram_helpers import is_admin, is_group_chat
from ...core.decisions import Decision

log = logging.getLogger(__name__)


class AntiLinksFeature:
    key = "anti_links"

    def __init__(self, cfg: Config, db: BotRepository) -> None:
        self.cfg = cfg
        self.db = db

    async def collect(self, update: Update, context: ContextTypes.DEFAULT_TYPE, bag: dict[str, Any]) -> None:
        msg = update.message
        chat = update.effective_chat
        user = msg.from_user if msg else None
        if not msg or not chat or not user:
            return
        if not is_group_chat(update):
            return

        text = (msg.text or msg.caption or "").strip()
        if not text:
            return

        chat_id = chat.id
        if not self.cfg.test_mode and not self.db.get_setting(chat_id, "anti_links"):
            return
        if not self.cfg.test_mode and text.startswith("/"):
            return
        if not self.cfg.test_mode and user.is_bot:
            return
        if not self.cfg.test_mode and await is_admin(context, chat_id, user.id):
            return
        if not self.cfg.link_re.search(text):
            return

        bag["anti_links_hit"] = True
        bag["display_name"] = f"@{user.username}" if user.username else user.mention_html()
        bag["max_warns"] = self.cfg.max_warns
        bag["sender_chat"] = msg.sender_chat

        log.info(
            "Link detected chat=%s user=%s msg=%s test_mode=%s",
            chat_id,
            user.id,
            msg.id,
            self.cfg.test_mode,
        )

    async def decide(self, update: Update, context: ContextTypes.DEFAULT_TYPE, bag: dict[str, Any]) -> Decision | None:
        del context
        del update
        if bag.get("participation_blocked"):
            return None
        if not bag.get("anti_links_hit"):
            return None

        return Decision(
            delete=True,
            warn=True,
            mute_seconds=self.cfg.mute_seconds,
            reason="anti_links",
            score=100,
        )
