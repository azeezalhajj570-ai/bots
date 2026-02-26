from __future__ import annotations

import logging
from dataclasses import replace

from dotenv import load_dotenv
from telegram import Update

from .app import build_app
from .cache import MemoryCache
from .config import load_config
from .db_factory import create_db
from .logging_config import setup_logging

log = logging.getLogger(__name__)


def main(test_mode: bool = False) -> None:
    load_dotenv()
    setup_logging()

    cfg = load_config()
    if test_mode:
        cfg = replace(cfg, test_mode=True)
    db = create_db(cfg)
    cache = MemoryCache()

    log.info("Starting bot (test_mode=%s)...", cfg.test_mode)
    app = build_app(cfg, db, cache)

    try:
        log.info("Polling started.")
        app.run_polling(allowed_updates=Update.ALL_TYPES)
    except KeyboardInterrupt:
        log.warning("Stopped by user (Ctrl+C).")
