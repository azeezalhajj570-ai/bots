from __future__ import annotations

import logging
import re
from typing import Any

from telegram import Update
from telegram.ext import ContextTypes

from ...config_provider import ConfigProvider
from ...config import Config
from ...core.decisions import Decision
from ...telegram_helpers import is_admin, is_group_chat

log = logging.getLogger(__name__)


class DynamicRemoveFeature:
    key = "dynamic_remove"

    def __init__(self, cfg: Config, provider: ConfigProvider) -> None:
        self.cfg = cfg
        self.provider = provider

    async def collect(self, update: Update, context: ContextTypes.DEFAULT_TYPE, bag: dict[str, Any]) -> None:
        msg = update.message
        chat = update.effective_chat
        user = msg.from_user if msg else None
        if not msg or not chat or not user:
            return
        if not is_group_chat(update):
            return
        if not self.cfg.test_mode and user.is_bot:
            return
        if not self.cfg.test_mode and await is_admin(context, chat.id, user.id):
            return

        text = (msg.text or msg.caption or "").strip()
        if not text:
            return

        rules = await self.provider.list_dynamic_rules(chat.id)
        for rule in rules:
            if not rule.enabled:
                continue
            try:
                if not re.search(rule.pattern, text, re.IGNORECASE):
                    continue
            except re.error:
                log.warning("Invalid dynamic rule regex id=%s chat=%s pattern=%r", rule.id, chat.id, rule.pattern)
                continue

            bag["ban_user_ids"] = [user.id]
            bag["ban_display_names"] = [user.mention_html()]
            bag["dynamic_remove_hit"] = True
            bag["dynamic_remove_rule_id"] = rule.id
            log.info("Dynamic remove hit chat=%s user=%s rule=%s", chat.id, user.id, rule.id)
            return

    async def decide(self, update: Update, context: ContextTypes.DEFAULT_TYPE, bag: dict[str, Any]) -> Decision | None:
        del update
        del context
        if not bag.get("dynamic_remove_hit"):
            return None
        return Decision(delete=True, ban=True, reason="dynamic_remove", score=120)
