from __future__ import annotations

import logging
import os
from pathlib import Path
import time
from typing import List

from dotenv import load_dotenv
from pyrogram import Client, filters, idle


def _setup_logging() -> logging.Logger:
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("user-client-pyrogram")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    logger.addHandler(console)

    file_handler = logging.FileHandler(log_dir / "user_client_groups.log", encoding="utf-8")
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)
    return logger


def _parse_join_links(raw: str) -> List[str]:
    if not raw.strip():
        return []
    normalized = raw.replace("\n", ",").replace(" ", ",")
    items = [item.strip() for item in normalized.split(",") if item.strip()]
    seen: set[str] = set()
    result: List[str] = []
    for item in items:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(f"Missing required env var: {name}")
    return value


def main() -> None:
    load_dotenv(".env.user")
    log = _setup_logging()

    api_id = int(_require_env("API_ID"))
    api_hash = _require_env("API_HASH")
    session_name = os.getenv("SESSION_NAME", "user_client")
    auto_reply_user_id = int(os.getenv("AUTO_REPLY_USER_ID", "6983225318"))
    auto_reply_text = os.getenv("AUTO_REPLY_TEXT", "هلا والله")
    auto_reply_cooldown = int(os.getenv("AUTO_REPLY_COOLDOWN_SECONDS", "8"))
    join_links = _parse_join_links(os.getenv("JOIN_LINKS", ""))
    last_reply_at: dict[tuple[int, int], float] = {}

    with Client(session_name, api_id=api_id, api_hash=api_hash) as app:
        try:
            count = 0
            for _ in app.get_dialogs():
                count += 1
            log.info("Dialog peer cache synced. dialogs=%s", count)
        except Exception as exc:
            log.warning("Dialog sync failed: %s", exc)

        @app.on_message(filters.group & filters.incoming)
        def _log_group_message(client: Client, message) -> None:
            now = time.time()
            text = message.text or message.caption or ""
            sender_id = message.from_user.id if message.from_user else None
            log.info(
                "group=%s sender=%s msg=%s text=%r",
                message.chat.id,
                sender_id,
                message.id,
                text[:500],
            )
            if sender_id != auto_reply_user_id:
                return

            key = (sender_id, sender_id)
            prev = last_reply_at.get(key, 0.0)
            if auto_reply_cooldown > 0 and (now - prev) < auto_reply_cooldown:
                return

            try:
                client.send_message(sender_id, auto_reply_text)
                last_reply_at[key] = now
                log.info("auto-dm sent target=%s text=%r source_chat=%s", sender_id, auto_reply_text, message.chat.id)
            except Exception as exc:
                log.error("auto-dm failed target=%s source_chat=%s error=%s", sender_id, message.chat.id, exc)

        me = app.get_me()
        print(f"Logged in as: {me.first_name} (@{me.username}) id={me.id}")
        for link in join_links:
            try:
                app.join_chat(link)
                log.info("joined chat from link=%s", link)
            except Exception as exc:
                log.warning("join failed link=%s error=%s", link, exc)
        print("User client is running and logging group messages. Press Ctrl+C to stop.")
        idle()


if __name__ == "__main__":
    main()
