from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from .storage import FeatureSettingsRepo


def build_settings_keyboard(db: FeatureSettingsRepo, chat_id: int) -> InlineKeyboardMarkup:
    anti_links = db.get_setting(chat_id, "anti_links")
    anti_bots = db.get_setting(chat_id, "anti_bots")
    hide_system = db.get_setting(chat_id, "hide_system")
    warn_in_dm = db.get_setting(chat_id, "warn_in_dm")
    warn_in_group = db.get_setting(chat_id, "warn_in_group")

    def st(v: bool) -> str:
        return "✅ ON" if v else "❌ OFF"

    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(f"منع الروابط: {st(anti_links)}", callback_data=f"toggle:anti_links:{chat_id}")],
            [InlineKeyboardButton(f"منع البوتات: {st(anti_bots)}", callback_data=f"toggle:anti_bots:{chat_id}")],
            [InlineKeyboardButton(f"إخفاء الانضمام/المغادرة: {st(hide_system)}", callback_data=f"toggle:hide_system:{chat_id}")],
            [InlineKeyboardButton(f"إرسال التحذير خاص DM: {st(warn_in_dm)}", callback_data=f"toggle:warn_in_dm:{chat_id}")],
            [InlineKeyboardButton(f"إرسال التحذير في المجموعة: {st(warn_in_group)}", callback_data=f"toggle:warn_in_group:{chat_id}")],
            [
                InlineKeyboardButton("🔄 تحديث", callback_data=f"refresh:{chat_id}"),
                InlineKeyboardButton("✖️ إغلاق", callback_data=f"close:{chat_id}"),
            ],
        ]
    )


def settings_text(db: FeatureSettingsRepo, chat_id: int) -> str:
    anti_links = db.get_setting(chat_id, "anti_links")
    anti_bots = db.get_setting(chat_id, "anti_bots")
    hide_system = db.get_setting(chat_id, "hide_system")
    warn_in_dm = db.get_setting(chat_id, "warn_in_dm")
    warn_in_group = db.get_setting(chat_id, "warn_in_group")
    return (
        "⚙️ **إعدادات الحماية**\n\n"
        f"• منع الروابط: {'مفعل ✅' if anti_links else 'متوقف ❌'}\n"
        f"• منع البوتات: {'مفعل ✅' if anti_bots else 'متوقف ❌'}\n"
        f"• إخفاء الانضمام/المغادرة: {'مفعل ✅' if hide_system else 'متوقف ❌'}\n"
        f"• إرسال التحذير في الخاص: {'مفعل ✅' if warn_in_dm else 'متوقف ❌'}\n"
        f"• إرسال التحذير في المجموعة: {'مفعل ✅' if warn_in_group else 'متوقف ❌'}\n\n"
        "اضغط الأزرار للتغيير."
    )
