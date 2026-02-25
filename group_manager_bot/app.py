from __future__ import annotations

import logging

from telegram import BotCommand
from telegram.error import BadRequest
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from .config import Config
from .db import DB
from .handlers.anti_bots import make_anti_bots_handler
from .handlers.anti_links import make_anti_links_handler
from .handlers.audit import log_group_messages
from .handlers.callbacks import make_callbacks
from .handlers.commands import make_resetwarns_cmd, make_settings_cmd, start_cmd

log = logging.getLogger(__name__)


def build_app(cfg: Config, db: DB) -> Application:
    async def _error_handler(update, context) -> None:
        error = context.error
        if isinstance(error, BadRequest) and "Message is not modified" in str(error):
            log.debug("Ignored no-op edit: %s", error)
            return
        log.exception("Unhandled bot error", exc_info=error)

    async def _post_init(application: Application) -> None:
        await application.bot.set_my_commands(
            [
                BotCommand("start", "Start the bot"),
                BotCommand("settings", "Open moderation settings"),
                BotCommand("resetwarns", "Reset replied user warnings"),
            ]
        )

    app = Application.builder().token(cfg.bot_token).post_init(_post_init).build()

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("settings", make_settings_cmd(db)))
    app.add_handler(CommandHandler("resetwarns", make_resetwarns_cmd(db)))
    app.add_handler(CallbackQueryHandler(make_callbacks(db)))

    app.add_handler(
        MessageHandler(
            (filters.ChatType.GROUPS | filters.ChatType.PRIVATE) & (filters.TEXT | filters.CAPTION),
            log_group_messages,
        ),
        group=-1,
    )
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, make_anti_bots_handler(db)))
    app.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.ALL, make_anti_links_handler(cfg, db)))
    app.add_error_handler(_error_handler)

    return app
