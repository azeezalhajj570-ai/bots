from __future__ import annotations

from typing import Any

from telegram import Update
from telegram.ext import ContextTypes

from ...config_provider import ConfigProvider
from ...core.decisions import Decision
from ...telegram_helpers import is_admin, is_group_chat, is_member_of_chat


class LinkRoutesFeature:
    key = "link_routes"

    def __init__(self, provider: ConfigProvider) -> None:
        self.provider = provider

    async def collect(self, update: Update, context: ContextTypes.DEFAULT_TYPE, bag: dict[str, Any]) -> None:
        msg = update.message
        chat = update.effective_chat
        user = msg.from_user if msg else None
        if not msg or not chat or not user:
            return
        if not is_group_chat(update):
            return

        text = (msg.text or msg.caption or "").strip().lower()
        if not text or text.startswith("/"):
            return

        routes = await self.provider.list_link_routes(chat.id)
        if not routes:
            return

        for route in routes:
            if not route.enabled or route.keyword not in text:
                continue

            if route.gate_group_id is None:
                allowed = True
            else:
                allowed = await is_admin(context, chat.id, user.id) or await is_member_of_chat(
                    context, route.gate_group_id, user.id
                )

            if not allowed:
                continue

            bag["link_route_hit"] = True
            bag["link_route_destination"] = route.destination
            return

    async def decide(self, update: Update, context: ContextTypes.DEFAULT_TYPE, bag: dict[str, Any]) -> Decision | None:
        del update
        del context
        destination = bag.get("link_route_destination")
        if not destination:
            return None
        return Decision(public_reply_text=destination, reason="link_route", score=40)
