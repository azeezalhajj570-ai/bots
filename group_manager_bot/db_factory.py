from __future__ import annotations

from .config import Config
from .db import DB
from .db_postgres import PostgresDB
from .storage import BotRepository


def create_db(cfg: Config) -> BotRepository:
    if cfg.database_url:
        return PostgresDB(cfg.database_url)
    return DB(cfg.db_path)
