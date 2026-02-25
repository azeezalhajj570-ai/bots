from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from group_manager.config import Config, load_token
from group_manager.db import DB
from group_manager.handlers.audit import log_group_messages
from group_manager.handlers.callbacks import callbacks
from group_manager.handlers.commands import resetwarns_cmd, settings_cmd, start_cmd
from group_manager.handlers.moderation import anti_bots_handler, anti_links_handler
from group_manager.logging_setup import configure_logging

logger = logging.getLogger(__name__)


def build_application() -> Application:
    configure_logging()
    token = load_token()

    app = Application.builder().token(token).build()

    app.bot_data["db"] = DB()
    app.bot_data["cfg"] = Config()

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("settings", settings_cmd))
    app.add_handler(CommandHandler("resetwarns", resetwarns_cmd))

    app.add_handler(MessageHandler(filters.ChatType.GROUPS & (filters.TEXT | filters.CAPTION), log_group_messages), group=-1)
    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, anti_bots_handler))
    app.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.ALL, anti_links_handler))

    return app


def main() -> None:
    app = build_application()
    logger.info("Bot starting polling")
    try:
        app.run_polling(allowed_updates=Update.ALL_TYPES)
    except KeyboardInterrupt:
        logger.warning("Bot stopped by keyboard interrupt")
