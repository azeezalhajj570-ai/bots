from __future__ import annotations

import logging

from telegram import BotCommand
from telegram.error import BadRequest, NetworkError, RetryAfter, TimedOut
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from .cache import Cache
from .config import Config
from .core.executor import Executor
from .core.router import Router
from .features.anti_bots.feature import AntiBotsFeature
from .features.anti_links.feature import AntiLinksFeature
from .features.dynamic_remove.feature import DynamicRemoveFeature
from .features.link_routes.feature import LinkRoutesFeature
from .features.participation_gate.feature import ParticipationGateFeature
from .handlers.audit import log_group_messages
from .handlers.callbacks import make_callbacks
from .handlers.commands import (
    make_addgate_cmd,
    make_addroute_cmd,
    make_addrule_cmd,
    contact_cmd,
    make_delgate_cmd,
    make_delroute_cmd,
    make_delrule_cmd,
    help_cmd,
    make_listgates_cmd,
    make_listroutes_cmd,
    make_listrules_cmd,
    make_private_settings_input_handler,
    make_resetwarns_cmd,
    make_settings_cmd,
    start_cmd,
    support_cmd,
)
from .handlers.hide_system import make_hide_system_handler
from .storage import BotRepository

log = logging.getLogger(__name__)


def build_app(cfg: Config, db: BotRepository, cache: Cache) -> Application:
    async def _error_handler(update, context) -> None:
        error = context.error
        if isinstance(error, BadRequest) and "message is not modified" in str(error).lower():
            log.debug("Ignored no-op edit: %s", error)
            return
        if isinstance(error, RetryAfter):
            log.warning("Telegram flood control. Retry after %s seconds.", error.retry_after)
            return
        if isinstance(error, (NetworkError, TimedOut)):
            log.warning("Transient Telegram network error: %s", error)
            return
        log.exception("Unhandled bot error", exc_info=error)

    async def _post_init(application: Application) -> None:
        await application.bot.set_my_commands(
            [
                BotCommand("start", "Start the bot"),
                BotCommand("help", "Show help"),
                BotCommand("support", "Support information"),
                BotCommand("contact", "Contact information"),
                BotCommand("settings", "Open moderation settings"),
                BotCommand("resetwarns", "Reset replied user warnings"),
                BotCommand("addrule", "Add dynamic remove regex"),
                BotCommand("delrule", "Delete dynamic remove rule"),
                BotCommand("listrules", "List dynamic remove rules"),
                BotCommand("addroute", "Add keyword route"),
                BotCommand("delroute", "Delete keyword route"),
                BotCommand("listroutes", "List keyword routes"),
                BotCommand("addgate", "Add required join group"),
                BotCommand("delgate", "Delete required join group"),
                BotCommand("listgates", "List required join groups"),
            ]
        )

    app = Application.builder().token(cfg.bot_token).post_init(_post_init).build()
    app.bot_data["cache"] = cache
    app.bot_data["router"] = Router(
        features=[
            AntiBotsFeature(db),
            ParticipationGateFeature(cfg, db),
            DynamicRemoveFeature(cfg, db),
            LinkRoutesFeature(db),
            AntiLinksFeature(cfg, db),
        ],
        executor=Executor(db),
    )

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("support", support_cmd))
    app.add_handler(CommandHandler("contact", contact_cmd))
    app.add_handler(CommandHandler("settings", make_settings_cmd(db)))
    app.add_handler(CommandHandler("resetwarns", make_resetwarns_cmd(db)))
    app.add_handler(CommandHandler("addrule", make_addrule_cmd(db)))
    app.add_handler(CommandHandler("delrule", make_delrule_cmd(db)))
    app.add_handler(CommandHandler("listrules", make_listrules_cmd(db)))
    app.add_handler(CommandHandler("addroute", make_addroute_cmd(db)))
    app.add_handler(CommandHandler("delroute", make_delroute_cmd(db)))
    app.add_handler(CommandHandler("listroutes", make_listroutes_cmd(db)))
    app.add_handler(CommandHandler("addgate", make_addgate_cmd(db)))
    app.add_handler(CommandHandler("delgate", make_delgate_cmd(db)))
    app.add_handler(CommandHandler("listgates", make_listgates_cmd(db)))
    app.add_handler(CallbackQueryHandler(make_callbacks(db)))

    app.add_handler(
        MessageHandler(
            (filters.ChatType.GROUPS | filters.ChatType.PRIVATE) & (filters.TEXT | filters.CAPTION),
            log_group_messages,
        ),
        group=-1,
    )
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, make_private_settings_input_handler(db)))
    app.add_handler(
        MessageHandler(
            filters.ChatType.GROUPS & (filters.StatusUpdate.NEW_CHAT_MEMBERS | filters.StatusUpdate.LEFT_CHAT_MEMBER),
            make_hide_system_handler(db),
        ),
        group=-1,
    )
    app.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.ALL, app.bot_data["router"].handle_message))
    app.add_error_handler(_error_handler)

    return app
