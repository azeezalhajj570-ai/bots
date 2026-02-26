from __future__ import annotations

import logging
from typing import Any

from telegram import Update
from telegram.ext import ContextTypes

from ...config_provider import ConfigProvider
from ...config import Config
from ...core.decisions import Decision
from ...telegram_helpers import is_admin, is_group_chat, is_member_of_chat

log = logging.getLogger(__name__)


class ParticipationGateFeature:
    key = "participation_gate"

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
        if user.is_bot:
            return
        if msg.text and msg.text.startswith("/"):
            return
        if not self.cfg.test_mode and await is_admin(context, chat.id, user.id):
            return

        gates = [gate for gate in await self.provider.list_participation_gates(chat.id) if gate.enabled]
        if not gates:
            return

        if self.cfg.test_mode:
            bag["participation_blocked"] = True
            bag["participation_buttons"] = [(gate.gate_title, gate.join_url) for gate in gates]
            log.info("Participation blocked (test_mode) chat=%s user=%s gates=%s", chat.id, user.id, len(gates))
            return

        missing: list[tuple[str, str]] = []
        for gate in gates:
            in_gate = await is_member_of_chat(context, gate.gate_group_id, user.id)
            if not in_gate:
                missing.append((gate.gate_title, gate.join_url))

        if not missing:
            return

        bag["participation_blocked"] = True
        bag["participation_buttons"] = missing
        log.info("Participation blocked chat=%s user=%s missing=%s", chat.id, user.id, len(missing))

    async def decide(self, update: Update, context: ContextTypes.DEFAULT_TYPE, bag: dict[str, Any]) -> Decision | None:
        del update
        del context
        missing = bag.get("participation_buttons")
        if not missing:
            return None

        return Decision(
            delete=True,
            public_reply_text="عذرًا، لازم تنضم للمجموعات المطلوبة أولًا عشان تقدر تشارك هنا.",
            public_reply_buttons=missing,
            reason="participation_gate",
            score=110,
        )
