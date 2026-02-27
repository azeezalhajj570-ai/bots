from __future__ import annotations

import logging
import re

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from ..i18n import get_user_lang, tr
from ..keyboards import (
    build_group_settings_home_keyboard,
    build_main_menu_keyboard,
    build_private_settings_keyboard,
)
from ..storage import BotRepository
from ..telegram_helpers import is_admin, is_group_chat

log = logging.getLogger(__name__)


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    lang = get_user_lang(context, update.effective_user.language_code if update.effective_user else None)
    if update.effective_chat and update.effective_chat.type == "private":
        await update.message.reply_text(
            tr(lang, "welcome"),
            reply_markup=build_main_menu_keyboard(lang),
        )
        return

    await update.message.reply_text(
        "Bot is running.\n"
        "Use /settings inside this group.\n\n"
        "Required bot permissions:\n"
        "- Delete messages\n"
        "- Ban/Restrict users"
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    lang = get_user_lang(context, update.effective_user.language_code if update.effective_user else None)
    await update.message.reply_text(tr(lang, "help_text"), disable_web_page_preview=True)


async def support_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    lang = get_user_lang(context, update.effective_user.language_code if update.effective_user else None)
    await update.message.reply_text(tr(lang, "support_text"), disable_web_page_preview=True)


async def contact_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    lang = get_user_lang(context, update.effective_user.language_code if update.effective_user else None)
    await update.message.reply_text(tr(lang, "contact_text"), disable_web_page_preview=True)


def _is_sender_chat_message(update: Update) -> bool:
    if not update.message:
        return False
    return update.message.sender_chat is not None


def _extract_group_usernames(raw: str) -> list[str]:
    link_re = re.compile(r"(?:https?://)?t\.me/([A-Za-z0-9_]{4,})", re.IGNORECASE)
    tokens = [token.strip() for token in raw.replace("\n", " ").split(" ") if token.strip()]
    usernames: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        match = link_re.search(token)
        if match:
            token = f"@{match.group(1)}"

        value = token if token.startswith("@") else f"@{token}"
        value = value.rstrip("/")
        value = value.strip()
        if len(value) < 2:
            continue
        if "/" in value:
            continue
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        usernames.append(value)
    return usernames


async def _send_group_selection(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    db: BotRepository,
    raw: str,
) -> None:
    if not update.message or not update.effective_user:
        return

    user_id = update.effective_user.id
    usernames = _extract_group_usernames(raw)
    if not usernames:
        await update.message.reply_text("Send group usernames like: @group1 @group2")
        return

    options: list[tuple[int, str]] = []
    for username in usernames:
        try:
            chat = await context.bot.get_chat(username)
        except Exception:
            continue
        if chat.type not in ("group", "supergroup"):
            continue
        if not await is_admin(context, chat.id, user_id):
            continue
        title = chat.title or str(chat.id)
        options.append((chat.id, title))
        db.ensure_group(chat.id)

    if not options:
        await update.message.reply_text("No manageable groups found. Make sure I am in the group and you are admin.")
        return

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton(title, callback_data=f"selectgroup:{chat_id}")] for chat_id, title in options]
    )
    await update.message.reply_text("Choose a group to open settings:", reply_markup=keyboard)


async def _is_group_admin_or_senderchat(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> tuple[bool, int | None, int | None]:
    if not update.message or not update.effective_chat:
        return False, None, None
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id if update.effective_user else None
    is_sender_chat = _is_sender_chat_message(update)
    is_user_group_admin = bool(user_id and await is_admin(context, chat_id, user_id))
    return is_sender_chat or is_user_group_admin, chat_id, user_id


async def _resolve_private_manageable_group(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    token: str,
) -> int | None:
    if not update.effective_user:
        return None
    usernames = _extract_group_usernames(token)
    if not usernames:
        return None
    username = usernames[0]
    try:
        chat = await context.bot.get_chat(username)
    except Exception:
        return None
    if chat.type not in ("group", "supergroup"):
        return None
    if not await is_admin(context, chat.id, update.effective_user.id):
        return None
    return chat.id


async def _resolve_group_token_any(
    context: ContextTypes.DEFAULT_TYPE,
    token: str,
) -> tuple[int, str, str] | None:
    usernames = _extract_group_usernames(token)
    if not usernames:
        return None
    username = usernames[0]
    try:
        chat = await context.bot.get_chat(username)
    except Exception:
        return None
    if chat.type not in ("group", "supergroup"):
        return None
    title = chat.title or str(chat.id)
    join_url = f"https://t.me/{chat.username}" if chat.username else ""
    return chat.id, title, join_url


def _parse_bulk_routes(raw: str) -> tuple[list[tuple[str, str]], str | None]:
    pairs: list[tuple[str, str]] = []
    for line in raw.splitlines():
        item = line.strip()
        if not item:
            continue
        if ":" not in item:
            return [], item
        keyword, destination = item.split(":", 1)
        key = keyword.strip().lower()
        val = destination.strip()
        if not key or not val:
            return [], item
        pairs.append((key, val))
    return pairs, None


def _parse_bulk_keywords(raw: str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for line in raw.splitlines():
        keyword = line.strip().lower()
        if not keyword:
            continue
        if keyword in seen:
            continue
        seen.add(keyword)
        out.append(keyword)
    return out


async def _resolve_target_group(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    args: list[str],
    usage: str,
) -> tuple[int, list[str]] | None:
    if not update.message or not update.effective_chat:
        return None

    if update.effective_chat.type == "private":
        if not args:
            await update.message.reply_text(usage)
            return None
        chat_id = await _resolve_private_manageable_group(update, context, args[0])
        if chat_id is None:
            await update.message.reply_text("Group not found/manageable. Use @group_username or t.me/group_username.")
            return None
        return chat_id, args[1:]

    if not is_group_chat(update):
        await update.message.reply_text("Use this command in a group or from private with a target group.")
        return None

    allowed, chat_id, _ = await _is_group_admin_or_senderchat(update, context)
    if not allowed:
        await update.message.reply_text("Admins only.")
        return None
    return chat_id, args


def make_settings_cmd(db: BotRepository):
    async def settings_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not update.effective_chat:
            return
        lang = get_user_lang(context, update.effective_user.language_code if update.effective_user else None)

        if update.effective_chat.type == "private":
            if context.args:
                await _send_group_selection(update, context, db, " ".join(context.args))
            else:
                context.user_data["await_group_usernames"] = True
                await update.message.reply_text(
                    tr(lang, "choose_group_settings"),
                    reply_markup=build_private_settings_keyboard(lang),
                )
            return

        if not is_group_chat(update):
            await update.message.reply_text("Use this command inside a group/supergroup.")
            return

        allowed, chat_id, user_id = await _is_group_admin_or_senderchat(update, context)
        member_status = None
        sender_chat_id = update.message.sender_chat.id if update.message.sender_chat else None
        if user_id:
            try:
                member_status = (await context.bot.get_chat_member(chat_id, user_id)).status
            except Exception as exc:
                log.warning("Settings status check failed chat=%s user=%s error=%s", chat_id, user_id, exc)
        if not allowed:
            log.info(
                "Settings denied chat=%s user=%s status=%s sender_chat=%s",
                chat_id,
                user_id,
                member_status,
                sender_chat_id,
            )
            await update.message.reply_text("Settings panel is for group admins only.")
            return

        db.ensure_group(chat_id)
        await update.message.reply_text(
            tr(lang, "group_settings_home_short"),
            reply_markup=build_group_settings_home_keyboard(chat_id, lang),
            disable_web_page_preview=True,
        )

    return settings_cmd


def make_private_settings_input_handler(db: BotRepository):
    async def private_settings_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not update.effective_chat or update.effective_chat.type != "private":
            return
        text = (update.message.text or "").strip()
        normalized = text.lower()
        lang = get_user_lang(context, update.effective_user.language_code if update.effective_user else None)

        if normalized == "cancel":
            context.user_data.pop("addroute_wizard", None)
            context.user_data.pop("ban_keyword_wizard", None)
            context.user_data["await_group_usernames"] = False
            await update.message.reply_text(tr(lang, "cancelled"))
            return

        if not context.user_data.get("await_group_usernames"):
            ban_keyword_wizard = context.user_data.get("ban_keyword_wizard")
            if ban_keyword_wizard:
                keywords = _parse_bulk_keywords(text)
                if not keywords:
                    await update.message.reply_text(tr(lang, "ban_keyword_invalid"))
                    return
                chat_id = int(ban_keyword_wizard["chat_id"])
                for keyword in keywords:
                    db.add_dynamic_rule(chat_id, re.escape(keyword))
                context.user_data.pop("ban_keyword_wizard", None)
                await update.message.reply_text(
                    tr(lang, "ban_keyword_saved", count=len(keywords), chat_id=chat_id),
                    parse_mode="Markdown",
                )
                return

            route_wizard = context.user_data.get("addroute_wizard")
            if route_wizard:
                step = route_wizard.get("step")
                if step == "group":
                    chat_id = await _resolve_private_manageable_group(update, context, text)
                    if chat_id is None:
                        await update.message.reply_text("Group not found/manageable. Send @group_username or t.me/group_username")
                        return
                    db.ensure_group(chat_id)
                    route_wizard["chat_id"] = chat_id
                    route_wizard["step"] = "keyword"
                    context.user_data["addroute_wizard"] = route_wizard
                    await update.message.reply_text(tr(lang, "wizard_keyword_prompt"))
                    return

                if step == "keyword":
                    if not text:
                        await update.message.reply_text("Keyword cannot be empty. Send a keyword.")
                        return
                    if ":" in text:
                        if "\n" in text:
                            bulk_pairs, invalid_line = _parse_bulk_routes(text)
                            if invalid_line is not None:
                                await update.message.reply_text(
                                    tr(lang, "wizard_bulk_invalid_line", line=invalid_line),
                                    parse_mode="Markdown",
                                )
                                return
                            if not bulk_pairs:
                                await update.message.reply_text(
                                    tr(lang, "wizard_bulk_invalid_line", line=text),
                                    parse_mode="Markdown",
                                )
                                return
                            chat_id = int(route_wizard["chat_id"])
                            for keyword, destination in bulk_pairs:
                                db.upsert_link_route(chat_id, keyword, destination, None)
                            context.user_data.pop("addroute_wizard", None)
                            await update.message.reply_text(
                                tr(lang, "wizard_saved_bulk", count=len(bulk_pairs), chat_id=chat_id),
                                parse_mode="Markdown",
                                disable_web_page_preview=True,
                            )
                            return
                        one_pairs, invalid_line = _parse_bulk_routes(text)
                        if invalid_line is not None or not one_pairs:
                            await update.message.reply_text(
                                tr(lang, "wizard_bulk_invalid_line", line=text),
                                parse_mode="Markdown",
                            )
                            return
                        chat_id = int(route_wizard["chat_id"])
                        keyword, destination = one_pairs[0]
                        db.upsert_link_route(chat_id, keyword, destination, None)
                        context.user_data.pop("addroute_wizard", None)
                        await update.message.reply_text(
                            tr(lang, "wizard_saved_single", chat_id=chat_id, keyword=keyword, destination=destination),
                            parse_mode="Markdown",
                            disable_web_page_preview=True,
                        )
                        return
                    route_wizard["keyword"] = text.lower()
                    route_wizard["step"] = "destination"
                    context.user_data["addroute_wizard"] = route_wizard
                    await update.message.reply_text(tr(lang, "wizard_destination_prompt"))
                    return

                if step == "destination":
                    if not text:
                        await update.message.reply_text("Destination cannot be empty. Send URL or message text.")
                        return
                    chat_id = int(route_wizard["chat_id"])
                    if "\n" in text:
                        bulk_pairs, invalid_line = _parse_bulk_routes(text)
                        if invalid_line is not None:
                            await update.message.reply_text(
                                tr(lang, "wizard_bulk_invalid_line", line=invalid_line),
                                parse_mode="Markdown",
                            )
                            return
                        if bulk_pairs:
                            for keyword, destination in bulk_pairs:
                                db.upsert_link_route(chat_id, keyword, destination, None)
                            context.user_data.pop("addroute_wizard", None)
                            await update.message.reply_text(
                                tr(lang, "wizard_saved_bulk", count=len(bulk_pairs), chat_id=chat_id),
                                parse_mode="Markdown",
                                disable_web_page_preview=True,
                            )
                            return
                    destination = text
                    keyword = str(route_wizard["keyword"])
                    db.upsert_link_route(chat_id, keyword, destination, None)
                    context.user_data.pop("addroute_wizard", None)
                    await update.message.reply_text(
                        tr(lang, "wizard_saved_single", chat_id=chat_id, keyword=keyword, destination=destination),
                        parse_mode="Markdown",
                        disable_web_page_preview=True,
                    )
                    return

            if normalized in {"add route", "addroute", "add rule", "addrule"}:
                context.user_data["addroute_wizard"] = {"step": "group"}
                await update.message.reply_text(tr(lang, "wizard_started_group"))
            return

        context.user_data["await_group_usernames"] = False
        await _send_group_selection(update, context, db, text)

    return private_settings_input_handler


def make_resetwarns_cmd(db: BotRepository):
    async def resetwarns_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not update.effective_chat:
            return

        if not is_group_chat(update):
            await update.message.reply_text("Use this command inside the group.")
            return

        allowed, chat_id, user_id = await _is_group_admin_or_senderchat(update, context)
        member_status = None
        sender_chat_id = update.message.sender_chat.id if update.message.sender_chat else None
        if user_id:
            try:
                member_status = (await context.bot.get_chat_member(chat_id, user_id)).status
            except Exception as exc:
                log.warning("Resetwarns status check failed chat=%s user=%s error=%s", chat_id, user_id, exc)
        if not allowed:
            log.info(
                "Resetwarns denied chat=%s user=%s status=%s sender_chat=%s",
                chat_id,
                user_id,
                member_status,
                sender_chat_id,
            )
            await update.message.reply_text("Admins only.")
            return

        if not update.message.reply_to_message or not update.message.reply_to_message.from_user:
            await update.message.reply_text("Reply to the user message, then run /resetwarns.")
            return

        target_id = update.message.reply_to_message.from_user.id
        db.reset_warns(chat_id, target_id)
        log.info("Warns reset chat=%s target=%s by=%s", chat_id, target_id, user_id)
        await update.message.reply_text("Warnings reset.")

    return resetwarns_cmd


def make_addrule_cmd(db: BotRepository):
    async def addrule_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return
        resolved = await _resolve_target_group(
            update,
            context,
            list(context.args),
            "Usage:\n/addrule <regex>\nOR in private:\n/addrule <@group_or_t.me_link> <regex>",
        )
        if resolved is None:
            return
        chat_id, cmd_args = resolved
        if not cmd_args:
            await update.message.reply_text("Missing regex pattern.")
            return
        pattern = " ".join(cmd_args).strip()
        rule_id = db.add_dynamic_rule(chat_id, pattern)
        await update.message.reply_text(f"Rule added for chat `{chat_id}`. id={rule_id}", parse_mode="Markdown")

    return addrule_cmd


def make_delrule_cmd(db: BotRepository):
    async def delrule_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return
        resolved = await _resolve_target_group(
            update,
            context,
            list(context.args),
            "Usage:\n/delrule <id>\nOR in private:\n/delrule <@group_or_t.me_link> <id>",
        )
        if resolved is None:
            return
        chat_id, cmd_args = resolved
        if not cmd_args:
            await update.message.reply_text("Missing rule id.")
            return
        try:
            rule_id = int(cmd_args[0])
        except ValueError:
            await update.message.reply_text("Rule id must be a number.")
            return
        deleted = db.delete_dynamic_rule(chat_id, rule_id)
        await update.message.reply_text("Rule deleted." if deleted else "Rule not found.")

    return delrule_cmd


def make_listrules_cmd(db: BotRepository):
    async def listrules_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return
        resolved = await _resolve_target_group(
            update,
            context,
            list(context.args),
            "Usage:\n/listrules\nOR in private:\n/listrules <@group_or_t.me_link>",
        )
        if resolved is None:
            return
        chat_id, _ = resolved
        rules = db.list_dynamic_rules(chat_id)
        if not rules:
            await update.message.reply_text("No dynamic remove rules.")
            return
        lines = [f"{rule.id}) `{rule.pattern}`" for rule in rules if rule.enabled]
        await update.message.reply_text("Dynamic rules:\n" + "\n".join(lines), parse_mode="Markdown")

    return listrules_cmd


def make_addroute_cmd(db: BotRepository):
    async def addroute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return
        lang = get_user_lang(context, update.effective_user.language_code if update.effective_user else None)
        if update.effective_chat and update.effective_chat.type == "private" and not context.args:
            context.user_data["addroute_wizard"] = {"step": "group"}
            await update.message.reply_text(tr(lang, "wizard_started_group"))
            return
        resolved = await _resolve_target_group(
            update,
            context,
            list(context.args),
            "Usage:\n/addroute <keyword> <url> [gate_group_id]\nOR in private:\n"
            "/addroute <@group_or_t.me_link> <keyword> <url> [gate_group_id]",
        )
        if resolved is None:
            return
        chat_id, cmd_args = resolved
        if len(cmd_args) < 2:
            await update.message.reply_text("Missing keyword/url.")
            return
        keyword = cmd_args[0].strip().lower()
        destination = cmd_args[1].strip()
        gate_group_id = None
        if len(cmd_args) >= 3:
            try:
                gate_group_id = int(cmd_args[2])
            except ValueError:
                await update.message.reply_text("gate_group_id must be a number.")
                return
        db.upsert_link_route(chat_id, keyword, destination, gate_group_id)
        await update.message.reply_text(
            tr(lang, "wizard_saved_single", chat_id=chat_id, keyword=keyword, destination=destination),
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )

    return addroute_cmd


def make_delroute_cmd(db: BotRepository):
    async def delroute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return
        resolved = await _resolve_target_group(
            update,
            context,
            list(context.args),
            "Usage:\n/delroute <keyword>\nOR in private:\n/delroute <@group_or_t.me_link> <keyword>",
        )
        if resolved is None:
            return
        chat_id, cmd_args = resolved
        if not cmd_args:
            await update.message.reply_text("Missing keyword.")
            return
        deleted = db.delete_link_route(chat_id, cmd_args[0])
        await update.message.reply_text("Route deleted." if deleted else "Route not found.")

    return delroute_cmd


def make_listroutes_cmd(db: BotRepository):
    async def listroutes_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return
        resolved = await _resolve_target_group(
            update,
            context,
            list(context.args),
            "Usage:\n/listroutes\nOR in private:\n/listroutes <@group_or_t.me_link>",
        )
        if resolved is None:
            return
        chat_id, _ = resolved
        routes = db.list_link_routes(chat_id)
        if not routes:
            await update.message.reply_text("No routes configured.")
            return
        lines = []
        for route in routes:
            gate = f" gate={route.gate_group_id}" if route.gate_group_id else ""
            lines.append(f"- `{route.keyword}` -> {route.destination}{gate}")
        await update.message.reply_text("Routes:\n" + "\n".join(lines), parse_mode="Markdown")

    return listroutes_cmd


def make_addgate_cmd(db: BotRepository):
    async def addgate_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return
        resolved = await _resolve_target_group(
            update,
            context,
            list(context.args),
            "Usage:\n/addgate <@required_group_or_link> [join_url]\nOR in private:\n"
            "/addgate <@target_group> <@required_group_or_link> [join_url]",
        )
        if resolved is None:
            return
        chat_id, cmd_args = resolved
        if not cmd_args:
            await update.message.reply_text("Missing required group.")
            return

        gate = await _resolve_group_token_any(context, cmd_args[0])
        if gate is None:
            await update.message.reply_text("Required group not found.")
            return
        gate_group_id, gate_title, default_join_url = gate
        join_url = cmd_args[1].strip() if len(cmd_args) >= 2 else default_join_url
        if not join_url:
            await update.message.reply_text("Required group has no public username. Provide join_url explicitly.")
            return

        db.upsert_participation_gate(chat_id, gate_group_id, gate_title, join_url)
        await update.message.reply_text(f"Gate added for chat `{chat_id}` -> {gate_title}", parse_mode="Markdown")

    return addgate_cmd


def make_delgate_cmd(db: BotRepository):
    async def delgate_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return
        resolved = await _resolve_target_group(
            update,
            context,
            list(context.args),
            "Usage:\n/delgate <gate_group_id>\nOR in private:\n/delgate <@target_group> <gate_group_id>",
        )
        if resolved is None:
            return
        chat_id, cmd_args = resolved
        if not cmd_args:
            await update.message.reply_text("Missing gate_group_id.")
            return
        try:
            gate_group_id = int(cmd_args[0])
        except ValueError:
            await update.message.reply_text("gate_group_id must be a number.")
            return
        deleted = db.delete_participation_gate(chat_id, gate_group_id)
        await update.message.reply_text("Gate deleted." if deleted else "Gate not found.")

    return delgate_cmd


def make_listgates_cmd(db: BotRepository):
    async def listgates_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            return
        resolved = await _resolve_target_group(
            update,
            context,
            list(context.args),
            "Usage:\n/listgates\nOR in private:\n/listgates <@target_group>",
        )
        if resolved is None:
            return
        chat_id, _ = resolved
        gates = db.list_participation_gates(chat_id)
        if not gates:
            await update.message.reply_text("No participation gates.")
            return
        lines = [f"- `{gate.gate_group_id}` {gate.gate_title} -> {gate.join_url}" for gate in gates if gate.enabled]
        await update.message.reply_text("Participation gates:\n" + "\n".join(lines), parse_mode="Markdown")

    return listgates_cmd
