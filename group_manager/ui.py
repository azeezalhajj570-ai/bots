from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from group_manager.db import DB


def build_settings_keyboard(chat_id: int, db: DB) -> InlineKeyboardMarkup:
    anti_links = db.get_setting(chat_id, "anti_links")
    anti_bots = db.get_setting(chat_id, "anti_bots")

    def status(value: bool) -> str:
        return "ON" if value else "OFF"

    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(f"Anti-links: {status(anti_links)}", callback_data=f"toggle:anti_links:{chat_id}")],
            [InlineKeyboardButton(f"Anti-bots: {status(anti_bots)}", callback_data=f"toggle:anti_bots:{chat_id}")],
            [
                InlineKeyboardButton("Refresh", callback_data=f"refresh:{chat_id}"),
                InlineKeyboardButton("Close", callback_data=f"close:{chat_id}"),
            ],
        ]
    )


def settings_text(chat_id: int, db: DB) -> str:
    anti_links = db.get_setting(chat_id, "anti_links")
    anti_bots = db.get_setting(chat_id, "anti_bots")
    return (
        "Protection settings\n\n"
        f"- Anti-links: {'enabled' if anti_links else 'disabled'}\n"
        f"- Anti-bots: {'enabled' if anti_bots else 'disabled'}\n\n"
        "Use the buttons below to change settings."
    )
