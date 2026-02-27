from __future__ import annotations

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatMemberStatus
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from ..i18n import get_user_lang, set_user_lang, tr
from ..keyboards import (
    ban_settings_text,
    build_advertise_settings_keyboard,
    build_autoreply_settings_keyboard,
    build_ban_settings_keyboard,
    build_group_settings_home_keyboard,
    build_home_back_keyboard,
    build_language_keyboard,
    build_main_menu_keyboard,
    build_private_settings_keyboard,
)
from ..storage import BotRepository

log = logging.getLogger(__name__)


async def _safe_edit_text(query, text: str, reply_markup=None) -> None:
    try:
        await query.edit_message_text(text, reply_markup=reply_markup, disable_web_page_preview=True)
    except BadRequest as exc:
        if "Message is not modified" in str(exc):
            return
        raise


async def _show_group_settings_home(query, chat_id: int, db: BotRepository, lang: str) -> None:
    routes_count = len(db.list_link_routes(chat_id))
    gates_count = len([gate for gate in db.list_participation_gates(chat_id) if gate.enabled])
    text = tr(lang, "group_settings_home", chat_id=chat_id, routes_count=routes_count, gates_count=gates_count)
    await _safe_edit_text(
        query,
        text,
        reply_markup=build_group_settings_home_keyboard(chat_id, lang),
    )


async def _show_ban_settings(query, chat_id: int, db: BotRepository, lang: str) -> None:
    await _safe_edit_text(
        query,
        ban_settings_text(db, chat_id, lang),
        reply_markup=build_ban_settings_keyboard(db, chat_id, lang),
    )


async def _show_autoreply_settings(query, chat_id: int, db: BotRepository, lang: str) -> None:
    routes = db.list_link_routes(chat_id)
    if not routes:
        content = tr(lang, "auto_empty")
    else:
        lines: list[str] = []
        for route in routes[:20]:
            gate = f" (gate: {route.gate_group_id})" if route.gate_group_id else ""
            lines.append(f"- `{route.keyword}`: {route.destination}{gate}")
        hidden = len(routes) - len(lines)
        tail = tr(lang, "auto_tail", count=hidden) if hidden > 0 else ""
        content = tr(lang, "auto_header", lines="\n".join(lines), tail=tail)

    text = tr(lang, "auto_panel", content=content)
    await _safe_edit_text(
        query,
        text,
        reply_markup=build_autoreply_settings_keyboard(chat_id, lang),
    )


async def _show_advertise_settings(query, chat_id: int, db: BotRepository, lang: str) -> None:
    gates = [gate for gate in db.list_participation_gates(chat_id) if gate.enabled]
    if not gates:
        content = tr(lang, "adv_empty")
    else:
        lines = [f"- `{gate.gate_group_id}` {gate.gate_title} -> {gate.join_url}" for gate in gates[:20]]
        hidden = len(gates) - len(lines)
        tail = tr(lang, "auto_tail", count=hidden) if hidden > 0 else ""
        content = tr(lang, "adv_header", lines="\n".join(lines), tail=tail)

    text = tr(lang, "adv_panel", content=content)
    await _safe_edit_text(
        query,
        text,
        reply_markup=build_advertise_settings_keyboard(chat_id, lang),
    )


def _adv_selection_key(chat_id: int) -> str:
    return f"adv_selection:{chat_id}"


async def _show_adv_group_picker(
    query,
    context: ContextTypes.DEFAULT_TYPE,
    db: BotRepository,
    lang: str,
    target_chat_id: int,
) -> None:
    group_ids = db.list_groups()
    options: list[tuple[int, str]] = []
    for group_id in group_ids:
        if group_id == target_chat_id:
            continue
        try:
            member = await context.bot.get_chat_member(group_id, query.from_user.id)
            if member.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
                continue
            chat = await context.bot.get_chat(group_id)
            if chat.type not in ("group", "supergroup"):
                continue
            options.append((group_id, chat.title or str(group_id)))
        except Exception:
            continue

    if not options:
        await _safe_edit_text(
            query,
            tr(lang, "adv_picker_empty"),
            reply_markup=build_advertise_settings_keyboard(target_chat_id, lang),
        )
        return

    selected = set(context.user_data.get(_adv_selection_key(target_chat_id), []))
    options.sort(key=lambda item: item[1].lower())
    rows = []
    for group_id, title in options:
        marker = "✅" if group_id in selected else "☐"
        rows.append([InlineKeyboardButton(f"{marker} {title[:40]}", callback_data=f"advsel:{target_chat_id}:{group_id}")])
    rows.append(
        [
            InlineKeyboardButton(tr(lang, "save_selection"), callback_data=f"advsave:{target_chat_id}"),
            InlineKeyboardButton(tr(lang, "back"), callback_data=f"sectionadv:{target_chat_id}"),
        ]
    )
    await _safe_edit_text(
        query,
        tr(lang, "adv_picker_title", chat_id=target_chat_id),
        reply_markup=InlineKeyboardMarkup(rows),
    )


async def _show_manageable_groups(
    query,
    context: ContextTypes.DEFAULT_TYPE,
    db: BotRepository,
    callback_prefix: str,
    title: str,
    lang: str,
) -> None:
    group_ids = db.list_groups()
    options: list[tuple[int, str]] = []
    for chat_id in group_ids:
        try:
            member = await context.bot.get_chat_member(chat_id, query.from_user.id)
            if member.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
                continue
            chat = await context.bot.get_chat(chat_id)
            if chat.type not in ("group", "supergroup"):
                continue
            options.append((chat_id, chat.title or str(chat_id)))
        except Exception:
            continue

    if not options:
        await _safe_edit_text(
            query,
            tr(lang, "no_manageable_groups"),
            reply_markup=build_home_back_keyboard(lang),
        )
        return

    options.sort(key=lambda item: item[1].lower())
    rows = [[InlineKeyboardButton(group_title[:50], callback_data=f"{callback_prefix}:{chat_id}")] for chat_id, group_title in options]
    rows.append([InlineKeyboardButton(tr(lang, "back"), callback_data="menu:home")])
    await _safe_edit_text(query, title, reply_markup=InlineKeyboardMarkup(rows))


def make_callbacks(db: BotRepository):
    async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        q = update.callback_query
        if not q or not q.message:
            return

        data = q.data or ""
        lang = get_user_lang(context, q.from_user.language_code if q.from_user else None)

        if data == "menu:home":
            await q.answer()
            await _safe_edit_text(
                q,
                tr(lang, "welcome"),
                reply_markup=build_main_menu_keyboard(lang),
            )
            return

        if data == "menu:lang":
            await q.answer()
            await _safe_edit_text(q, tr(lang, "language_title"), reply_markup=build_language_keyboard())
            return

        if data.startswith("lang:"):
            new_lang = set_user_lang(context, data.split(":")[1])
            await q.answer()
            await _safe_edit_text(
                q,
                f"{tr(new_lang, 'language_saved')}\n\n{tr(new_lang, 'welcome')}",
                reply_markup=build_main_menu_keyboard(new_lang),
            )
            return

        if data == "menu:settings":
            await q.answer()
            await _safe_edit_text(q, tr(lang, "settings_menu"), reply_markup=build_private_settings_keyboard(lang))
            return

        if data == "settings:choose_groups":
            context.user_data["await_group_usernames"] = False
            context.user_data.pop("addroute_wizard", None)
            context.user_data.pop("ban_keyword_wizard", None)
            await q.answer()
            await _show_manageable_groups(
                q,
                context,
                db,
                callback_prefix="selectgroup",
                title=tr(lang, "choose_group_settings"),
                lang=lang,
            )
            return

        if data.startswith("settingsflow:"):
            section = data.split(":", 1)[1]
            if section not in ("auto", "ban", "adv"):
                await q.answer()
                return
            context.user_data["await_group_usernames"] = False
            context.user_data.pop("addroute_wizard", None)
            context.user_data.pop("ban_keyword_wizard", None)
            await q.answer()
            await _show_manageable_groups(
                q,
                context,
                db,
                callback_prefix=f"opensection:{section}",
                title=tr(lang, "choose_group_settings"),
                lang=lang,
            )
            return

        if data == "groupslist":
            context.user_data["await_group_usernames"] = False
            context.user_data.pop("addroute_wizard", None)
            context.user_data.pop("ban_keyword_wizard", None)
            await q.answer()
            await _show_manageable_groups(
                q,
                context,
                db,
                callback_prefix="selectgroup",
                title=tr(lang, "choose_group_settings"),
                lang=lang,
            )
            return

        if data == "menu:routes" or data == "settings:route_wizard":
            context.user_data["await_group_usernames"] = False
            context.user_data.pop("addroute_wizard", None)
            context.user_data.pop("ban_keyword_wizard", None)
            await q.answer()
            await _show_manageable_groups(
                q,
                context,
                db,
                callback_prefix="routegroup",
                title=tr(lang, "choose_group_route"),
                lang=lang,
            )
            return

        if data == "menu:help":
            await q.answer()
            await _safe_edit_text(
                q,
                tr(lang, "main_commands"),
                reply_markup=build_home_back_keyboard(lang),
            )
            return

        parts = data.split(":")
        if len(parts) < 2:
            return await q.answer()

        action = parts[0]
        try:
            chat_id = int(parts[-1])
        except ValueError:
            return await q.answer()

        member = await context.bot.get_chat_member(chat_id, q.from_user.id)
        if member.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
            return await q.answer(tr(lang, "admins_only"), show_alert=True)

        await q.answer()

        if action in ("selectgroup", "grouphome"):
            db.ensure_group(chat_id)
            await _show_group_settings_home(q, chat_id, db, lang)
            return

        if action == "opensection" and len(parts) == 3:
            section = parts[1]
            db.ensure_group(chat_id)
            if section == "auto":
                await _show_autoreply_settings(q, chat_id, db, lang)
                return
            if section == "ban":
                await _show_ban_settings(q, chat_id, db, lang)
                return
            if section == "adv":
                await _show_advertise_settings(q, chat_id, db, lang)
                return

        if action == "sectionban":
            await _show_ban_settings(q, chat_id, db, lang)
            return

        if action == "sectionauto":
            await _show_autoreply_settings(q, chat_id, db, lang)
            return

        if action == "sectionadv":
            await _show_advertise_settings(q, chat_id, db, lang)
            return

        if action == "advpickgroups":
            context.user_data.setdefault(_adv_selection_key(chat_id), [])
            await _show_adv_group_picker(q, context, db, lang, chat_id)
            return

        if action == "advsel" and len(parts) == 3:
            try:
                target_chat_id = int(parts[1])
            except ValueError:
                return
            selection_key = _adv_selection_key(target_chat_id)
            selected = set(context.user_data.get(selection_key, []))
            if chat_id in selected:
                selected.remove(chat_id)
            else:
                selected.add(chat_id)
            context.user_data[selection_key] = list(selected)
            await _show_adv_group_picker(q, context, db, lang, target_chat_id)
            return

        if action == "advsave":
            target_chat_id = chat_id
            selection_key = _adv_selection_key(target_chat_id)
            selected = set(context.user_data.get(selection_key, []))
            added = 0
            skipped = 0
            for gate_group_id in selected:
                try:
                    gate_chat = await context.bot.get_chat(gate_group_id)
                except Exception:
                    skipped += 1
                    continue
                join_url = f"https://t.me/{gate_chat.username}" if gate_chat.username else ""
                if not join_url:
                    skipped += 1
                    continue
                gate_title = gate_chat.title or str(gate_group_id)
                db.upsert_participation_gate(target_chat_id, gate_group_id, gate_title, join_url)
                added += 1
            context.user_data.pop(selection_key, None)
            await q.answer(tr(lang, "adv_saved_result", added=added, skipped=skipped))
            await _show_advertise_settings(q, target_chat_id, db, lang)
            return

        if action == "toggle" and len(parts) == 3:
            key = parts[1]
            if key not in ("anti_links", "anti_bots", "hide_system", "warn_in_dm", "warn_in_group", "temp_ban_before_remove"):
                return
            new_val = db.toggle_setting(chat_id, key)
            log.info("Setting changed chat=%s %s=%s by user=%s", chat_id, key, new_val, q.from_user.id)
            await _show_ban_settings(q, chat_id, db, lang)
            return

        if action == "tempbansecs":
            current = db.get_int_setting(chat_id, "temp_ban_seconds", 600)
            options = (300, 600, 1800, 3600, 21600, 86400)
            try:
                idx = options.index(current)
                next_value = options[(idx + 1) % len(options)]
            except ValueError:
                next_value = options[0]
            db.set_int_setting(chat_id, "temp_ban_seconds", next_value)
            await _show_ban_settings(q, chat_id, db, lang)
            return

        if action == "bankeywordgroup":
            db.ensure_group(chat_id)
            context.user_data["ban_keyword_wizard"] = {"chat_id": chat_id}
            context.user_data["await_group_usernames"] = False
            context.user_data.pop("addroute_wizard", None)
            await _safe_edit_text(
                q,
                tr(lang, "ban_keyword_prompt"),
                reply_markup=build_home_back_keyboard(lang),
            )
            return

        if action == "routegroup":
            db.ensure_group(chat_id)
            context.user_data["addroute_wizard"] = {"step": "keyword", "chat_id": chat_id}
            context.user_data["await_group_usernames"] = False
            context.user_data.pop("ban_keyword_wizard", None)
            await _safe_edit_text(
                q,
                tr(lang, "wizard_started"),
                reply_markup=build_home_back_keyboard(lang),
            )
            return

        if action == "close":
            try:
                await q.message.delete()
            except Exception:
                pass

    return callbacks
