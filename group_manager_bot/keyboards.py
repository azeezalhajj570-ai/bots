from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from .i18n import tr
from .storage import FeatureSettingsRepo


def _status_label(lang: str, value: bool) -> str:
    return tr(lang, "status_on") if value else tr(lang, "status_off")


def _format_duration(seconds: int) -> str:
    if seconds % 3600 == 0:
        return f"{seconds // 3600}h"
    if seconds % 60 == 0:
        return f"{seconds // 60}m"
    return f"{seconds}s"


def build_group_settings_home_keyboard(chat_id: int, lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(tr(lang, "section_auto"), callback_data=f"sectionauto:{chat_id}")],
            [InlineKeyboardButton(tr(lang, "section_ban"), callback_data=f"sectionban:{chat_id}")],
            [InlineKeyboardButton(tr(lang, "section_adv"), callback_data=f"sectionadv:{chat_id}")],
            [InlineKeyboardButton(tr(lang, "back"), callback_data="groupslist")],
            [InlineKeyboardButton(tr(lang, "close"), callback_data=f"close:{chat_id}")],
        ]
    )


def build_ban_settings_keyboard(db: FeatureSettingsRepo, chat_id: int, lang: str) -> InlineKeyboardMarkup:
    anti_links = db.get_setting(chat_id, "anti_links")
    anti_bots = db.get_setting(chat_id, "anti_bots")
    hide_system = db.get_setting(chat_id, "hide_system")
    warn_in_dm = db.get_setting(chat_id, "warn_in_dm")
    warn_in_group = db.get_setting(chat_id, "warn_in_group")
    temp_ban_before_remove = db.get_setting(chat_id, "temp_ban_before_remove")
    temp_ban_seconds = db.get_int_setting(chat_id, "temp_ban_seconds", 600)

    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(f"{tr(lang, 'anti_links')}: {_status_label(lang, anti_links)}", callback_data=f"toggle:anti_links:{chat_id}")],
            [InlineKeyboardButton(f"{tr(lang, 'anti_bots')}: {_status_label(lang, anti_bots)}", callback_data=f"toggle:anti_bots:{chat_id}")],
            [InlineKeyboardButton(f"{tr(lang, 'hide_join_leave')}: {_status_label(lang, hide_system)}", callback_data=f"toggle:hide_system:{chat_id}")],
            [InlineKeyboardButton(f"{tr(lang, 'warn_dm')}: {_status_label(lang, warn_in_dm)}", callback_data=f"toggle:warn_in_dm:{chat_id}")],
            [InlineKeyboardButton(f"{tr(lang, 'warn_group')}: {_status_label(lang, warn_in_group)}", callback_data=f"toggle:warn_in_group:{chat_id}")],
            [InlineKeyboardButton(f"{tr(lang, 'temp_ban_before_remove')}: {_status_label(lang, temp_ban_before_remove)}", callback_data=f"toggle:temp_ban_before_remove:{chat_id}")],
            [InlineKeyboardButton(f"{tr(lang, 'temp_ban_duration')}: {_format_duration(temp_ban_seconds)}", callback_data=f"tempbansecs:{chat_id}")],
            [InlineKeyboardButton(tr(lang, "add_ban_keywords"), callback_data=f"bankeywordgroup:{chat_id}")],
            [
                InlineKeyboardButton(tr(lang, "refresh"), callback_data=f"sectionban:{chat_id}"),
                InlineKeyboardButton(tr(lang, "back"), callback_data=f"grouphome:{chat_id}"),
            ],
        ]
    )


def build_autoreply_settings_keyboard(chat_id: int, lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(tr(lang, "add_auto_reply"), callback_data=f"routegroup:{chat_id}")],
            [
                InlineKeyboardButton(tr(lang, "refresh"), callback_data=f"sectionauto:{chat_id}"),
                InlineKeyboardButton(tr(lang, "back"), callback_data=f"grouphome:{chat_id}"),
            ],
        ]
    )


def build_advertise_settings_keyboard(chat_id: int, lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(tr(lang, "select_adv_groups"), callback_data=f"advpickgroups:{chat_id}")],
            [
                InlineKeyboardButton(tr(lang, "refresh"), callback_data=f"sectionadv:{chat_id}"),
                InlineKeyboardButton(tr(lang, "back"), callback_data=f"grouphome:{chat_id}"),
            ],
        ]
    )


def ban_settings_text(db: FeatureSettingsRepo, chat_id: int, lang: str) -> str:
    anti_links = db.get_setting(chat_id, "anti_links")
    anti_bots = db.get_setting(chat_id, "anti_bots")
    hide_system = db.get_setting(chat_id, "hide_system")
    warn_in_dm = db.get_setting(chat_id, "warn_in_dm")
    warn_in_group = db.get_setting(chat_id, "warn_in_group")
    temp_ban_before_remove = db.get_setting(chat_id, "temp_ban_before_remove")
    temp_ban_seconds = db.get_int_setting(chat_id, "temp_ban_seconds", 600)
    return (
        tr(
            lang,
            "ban_panel",
            anti_links=tr(lang, "enabled") if anti_links else tr(lang, "disabled"),
            anti_bots=tr(lang, "enabled") if anti_bots else tr(lang, "disabled"),
            hide_system=tr(lang, "enabled") if hide_system else tr(lang, "disabled"),
            warn_in_dm=tr(lang, "enabled") if warn_in_dm else tr(lang, "disabled"),
            warn_in_group=tr(lang, "enabled") if warn_in_group else tr(lang, "disabled"),
            temp_ban_before_remove=tr(lang, "enabled") if temp_ban_before_remove else tr(lang, "disabled"),
            temp_ban_duration=_format_duration(temp_ban_seconds),
        )
    )


def build_main_menu_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(tr(lang, "menu_open_settings"), callback_data="menu:settings")],
            [InlineKeyboardButton(tr(lang, "menu_help"), callback_data="menu:help")],
            [InlineKeyboardButton(tr(lang, "menu_language"), callback_data="menu:lang")],
        ]
    )


def build_private_settings_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(tr(lang, "section_auto"), callback_data="settingsflow:auto")],
            [InlineKeyboardButton(tr(lang, "section_ban"), callback_data="settingsflow:ban")],
            [InlineKeyboardButton(tr(lang, "section_adv"), callback_data="settingsflow:adv")],
            [InlineKeyboardButton(tr(lang, "back"), callback_data="menu:home")],
        ]
    )


def build_home_back_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton(tr(lang, "back_home"), callback_data="menu:home")]])


def build_language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("English", callback_data="lang:en")],
            [InlineKeyboardButton("العربية", callback_data="lang:ar")],
            [InlineKeyboardButton("Back", callback_data="menu:home")],
        ]
    )
