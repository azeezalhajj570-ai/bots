from __future__ import annotations

from telegram.ext import ContextTypes

from group_manager.config import Config
from group_manager.db import DB


def get_db(context: ContextTypes.DEFAULT_TYPE) -> DB:
    return context.application.bot_data["db"]


def get_config(context: ContextTypes.DEFAULT_TYPE) -> Config:
    return context.application.bot_data["cfg"]
