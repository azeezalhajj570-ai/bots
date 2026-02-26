from __future__ import annotations

import logging
from typing import Any

from telegram import Update
from telegram.ext import ContextTypes

from .decisions import Decision
from .executor import Executor
from .feature import Feature

log = logging.getLogger(__name__)


class Router:
    def __init__(self, features: list[Feature], executor: Executor) -> None:
        self.features = features
        self.executor = executor

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        bag: dict[str, Any] = {}

        for feature in self.features:
            await feature.collect(update, context, bag)

        decision = Decision()
        for feature in self.features:
            feature_decision = await feature.decide(update, context, bag)
            if feature_decision is None:
                continue
            decision = self._merge(decision, feature_decision)

        await self.executor.apply(update, context, bag, decision)

    def _merge(self, base: Decision, new: Decision) -> Decision:
        mute_seconds = base.mute_seconds or new.mute_seconds
        if base.mute_seconds and new.mute_seconds:
            mute_seconds = max(base.mute_seconds, new.mute_seconds)

        return Decision(
            delete=base.delete or new.delete,
            warn=base.warn or new.warn,
            mute_seconds=mute_seconds,
            ban=base.ban or new.ban,
            public_reply_text=new.public_reply_text or base.public_reply_text,
            public_reply_buttons=new.public_reply_buttons or base.public_reply_buttons,
            reason=new.reason or base.reason,
            score=max(base.score, new.score),
        )
