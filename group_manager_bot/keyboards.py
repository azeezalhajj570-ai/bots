from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from .db import DB


def build_settings_keyboard(db: DB, chat_id: int) -> InlineKeyboardMarkup:
    anti_links = db.get_setting(chat_id, "anti_links")
    anti_bots = db.get_setting(chat_id, "anti_bots")

    def st(v: bool) -> str:
        return "✅ ON" if v else "❌ OFF"

    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(f"منع الروابط: {st(anti_links)}", callback_data=f"toggle:anti_links:{chat_id}")],
            [InlineKeyboardButton(f"منع البوتات: {st(anti_bots)}", callback_data=f"toggle:anti_bots:{chat_id}")],
            [
                InlineKeyboardButton("🔄 تحديث", callback_data=f"refresh:{chat_id}"),
                InlineKeyboardButton("✖️ إغلاق", callback_data=f"close:{chat_id}"),
            ],
        ]
    )


def settings_text(db: DB, chat_id: int) -> str:
    anti_links = db.get_setting(chat_id, "anti_links")
    anti_bots = db.get_setting(chat_id, "anti_bots")
    return (
        "⚙️ **إعدادات الحماية**\n\n"
        f"• منع الروابط: {'مفعل ✅' if anti_links else 'متوقف ❌'}\n"
        f"• منع البوتات: {'مفعل ✅' if anti_bots else 'متوقف ❌'}\n\n"
        "اضغط الأزرار للتغيير."
    )

