from __future__ import annotations

import asyncio
import logging
import os
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Iterator, Optional

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)
_PENDING_LOGIN_CLIENTS: dict[int, tuple["Client", asyncio.AbstractEventLoop]] = {}
_PENDING_LOGIN_LOCK = threading.Lock()

# Dependency guard: distinguish "not installed" from "installed but import failed"
try:
    from pyrogram import Client
    from pyrogram.errors import PhoneCodeExpired, PhoneCodeInvalid
    from pyrogram.errors import SessionPasswordNeeded
except ImportError as e:  # genuinely missing
    Client = None  # type: ignore[assignment]
    PhoneCodeExpired = Exception  # type: ignore[assignment]
    PhoneCodeInvalid = Exception  # type: ignore[assignment]
    SessionPasswordNeeded = Exception  # type: ignore[assignment]
    _logger.warning("Pyrogram is not installed (ImportError): %s", e)
except Exception as e:  # installed but failing to load for some reason
    Client = None  # type: ignore[assignment]
    PhoneCodeExpired = Exception  # type: ignore[assignment]
    PhoneCodeInvalid = Exception  # type: ignore[assignment]
    SessionPasswordNeeded = Exception  # type: ignore[assignment]
    _logger.exception("Pyrogram failed to import due to runtime error: %s", e)


class TelegramUserAccount(models.Model):
    _name = "telegram.user.account"
    _description = "Telegram User Account"
    _order = "id desc"

    name = fields.Char(compute="_compute_name", store=True)
    account_ref = fields.Char(required=True, index=True)
    phone_number = fields.Char(required=True, index=True, help="International format, e.g. +15551234567")
    api_id = fields.Integer(required=True)
    api_hash = fields.Char(required=True)

    session_string = fields.Text(copy=False)
    enabled = fields.Boolean(default=True, index=True)

    auth_state = fields.Selection(
        [
            ("draft", "Draft"),
            ("code_sent", "Code Sent"),
            ("password_required", "Password Required"),
            ("authorized", "Authorized"),
            ("error", "Error"),
        ],
        default="draft",
        required=True,
        index=True,
    )

    auth_code = fields.Char(copy=False)
    auth_password = fields.Char(copy=False)

    phone_code_hash = fields.Char(copy=False)
    login_session_string = fields.Text(copy=False)
    auth_expires_at = fields.Datetime(copy=False)
    code_delivery_type = fields.Char(copy=False, readonly=True)
    code_next_type = fields.Char(copy=False, readonly=True)
    code_timeout_seconds = fields.Integer(copy=False, readonly=True)

    last_error = fields.Text(copy=False)

    _sql_constraints = [
        ("uniq_account_ref_phone", "unique(account_ref, phone_number)", "Account ref + phone number must be unique."),
    ]

    @api.depends("account_ref", "phone_number")
    def _compute_name(self):
        for rec in self:
            rec.name = f"{rec.account_ref} | {rec.phone_number}"

    # -----------------------
    # Helpers
    # -----------------------
    def _ensure_pyrogram(self) -> None:
        if Client is None:
            # If you used the improved guard, the real reason is in logs.
            raise UserError(
                _("Pyrogram is unavailable in this environment. Check Odoo logs for the actual import error.")
            )

    def _session_name(self) -> str:
        self.ensure_one()
        # Unique, stable per record
        return f"odoo_tg_login_{self.id}"

    def _build_client(self) -> "Client":
        self.ensure_one()
        self._ensure_pyrogram()
        self._validate_login_prereqs()
        self._ensure_event_loop()
        return Client(
            name=self._session_name(),
            api_id=self._api_id_int(),
            api_hash=self.api_hash,
        )

    def _get_pending_client(self) -> "tuple[Client, asyncio.AbstractEventLoop] | None":
        self.ensure_one()
        with _PENDING_LOGIN_LOCK:
            return _PENDING_LOGIN_CLIENTS.get(self.id)

    def _set_pending_client(self, client: "Client", loop: asyncio.AbstractEventLoop) -> None:
        self.ensure_one()
        with _PENDING_LOGIN_LOCK:
            old_pair = _PENDING_LOGIN_CLIENTS.get(self.id)
            _PENDING_LOGIN_CLIENTS[self.id] = (client, loop)
        if old_pair and old_pair[0] is not client:
            try:
                old_pair[0].disconnect()
            except Exception:
                _logger.debug("Old pending client disconnect failed for record %s", self.id, exc_info=True)
        _logger.info("Set pending login client for record %s on pid=%s", self.id, os.getpid())

    def _pop_pending_client(self) -> "tuple[Client, asyncio.AbstractEventLoop] | None":
        self.ensure_one()
        with _PENDING_LOGIN_LOCK:
            pair = _PENDING_LOGIN_CLIENTS.pop(self.id, None)
        if pair:
            _logger.info("Popped pending login client for record %s on pid=%s", self.id, os.getpid())
        return pair

    def _disconnect_client(self, pair: "tuple[Client, asyncio.AbstractEventLoop] | None") -> None:
        if not pair:
            return
        client, loop = pair
        try:
            asyncio.set_event_loop(loop)
            client.disconnect()
        except Exception:
            _logger.debug("Pending client disconnect failed", exc_info=True)

    def _ensure_event_loop(self) -> None:
        # Odoo request handlers may run in threads with no default asyncio loop.
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                asyncio.set_event_loop(asyncio.new_event_loop())
        except RuntimeError:
            asyncio.set_event_loop(asyncio.new_event_loop())

    def _validate_login_prereqs(self) -> None:
        self.ensure_one()
        if not self.enabled:
            raise UserError(_("This Telegram user account is disabled."))

        phone = self._normalized_phone()
        if not phone or not phone.startswith("+") or len(phone) < 8:
            raise UserError(_("Phone number must be in international format, e.g. +15551234567."))

        if not self.api_hash:
            raise UserError(_("API ID and API Hash are required."))
        _ = self._api_id_int()

    def _normalized_phone(self) -> str:
        self.ensure_one()
        raw = (self.phone_number or "").strip()
        if not raw:
            return ""
        prefix = "+" if raw.startswith("+") else ""
        digits = "".join(ch for ch in raw if ch.isdigit())
        return f"{prefix}{digits}" if prefix else digits

    def _api_id_int(self) -> int:
        self.ensure_one()
        try:
            value = int(self.api_id)
        except Exception as exc:
            raise UserError(_("API ID must be an integer.")) from exc
        if value <= 0:
            raise UserError(_("API ID must be a positive integer."))
        return value

    def _now_utc(self) -> datetime:
        # Odoo stores datetimes in UTC by default; keep logic in UTC
        return datetime.utcnow()

    def _is_expired(self) -> bool:
        self.ensure_one()
        if not self.auth_expires_at:
            return False
        # fields.Datetime is string in DB, but in record is datetime (usually)
        expires = self.auth_expires_at
        if isinstance(expires, str):
            expires = fields.Datetime.from_string(expires)
        return expires is not None and expires < fields.Datetime.from_string(fields.Datetime.to_string(self._now_utc()))

    def _clear_auth_fields(self) -> None:
        self.ensure_one()
        self.write(
            {
                "auth_code": False,
                "auth_password": False,
                "phone_code_hash": False,
                "login_session_string": False,
                "auth_expires_at": False,
                "code_delivery_type": False,
                "code_next_type": False,
                "code_timeout_seconds": False,
            }
        )

    @contextmanager
    def _client(self, use_login_session: bool = False) -> Iterator["Client"]:
        """
        Context manager to ensure connect/disconnect is always paired.
        Uses Pyrogram sync API.
        """
        self.ensure_one()
        self._ensure_pyrogram()
        self._validate_login_prereqs()
        self._ensure_event_loop()

        if use_login_session and self.login_session_string:
            client = Client(
                name=f"{self._session_name()}_tmp",
                api_id=self._api_id_int(),
                api_hash=self.api_hash,
                session_string=self.login_session_string,
                in_memory=True,
            )
        else:
            client = Client(
                name=self._session_name(),
                api_id=self._api_id_int(),
                api_hash=self.api_hash,
            )

        try:
            client.connect()
            yield client
        finally:
            try:
                client.disconnect()
            except Exception:
                # Don't raise on disconnect failures
                _logger.debug("Pyrogram client disconnect failed for record %s", self.id, exc_info=True)

    def _set_error(self, exc: Exception, user_prefix: str) -> None:
        """
        Store error details on the record and raise a user-friendly message.
        Full traceback stays in logs.
        """
        self.ensure_one()
        msg = f"{type(exc).__name__}: {exc}"
        self.write({"auth_state": "error", "last_error": msg})
        _logger.exception("%s (record %s): %s", user_prefix, self.id, msg)
        raise UserError(_("%s: %s") % (user_prefix, exc)) from exc

    def _telegram_error_text(self, exc: Exception) -> str:
        self.ensure_one()
        parts = [f"{type(exc).__name__}: {exc}"]
        for attr in ("CODE", "ID", "MESSAGE", "VALUE"):
            if hasattr(exc, attr):
                parts.append(f"{attr}={getattr(exc, attr)}")
        return " | ".join(parts)

    # -----------------------
    # Actions
    # -----------------------
    def action_send_code(self):
        """
        Sends login code to phone_number.
        """
        for rec in self:
            rec._validate_login_prereqs()

            # Reset any previous attempt state
            rec.write(
                {
                    "auth_code": False,
                    "auth_password": False,
                    "session_string": False,
                    "last_error": False,
                }
            )

            try:
                old = rec._pop_pending_client()
                rec._disconnect_client(old)

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                client = rec._build_client()
                client.connect()
                phone = rec._normalized_phone()
                sent = client.send_code(phone)
                rec._set_pending_client(client, loop)

                rec.write(
                    {
                        "phone_code_hash": sent.phone_code_hash,
                        "login_session_string": False,
                        "auth_state": "code_sent",
                        "auth_expires_at": fields.Datetime.to_string(rec._now_utc() + timedelta(minutes=10)),
                        "code_delivery_type": str(getattr(sent, "type", "") or ""),
                        "code_next_type": str(getattr(sent, "next_type", "") or ""),
                        "code_timeout_seconds": int(getattr(sent, "timeout", 0) or 0),
                        "last_error": False,
                    }
                )
                _logger.info("Code sent for record %s on pid=%s", rec.id, os.getpid())
            except Exception as exc:
                rec._disconnect_client(rec._pop_pending_client())
                rec._set_error(exc, "Failed to send login code")
        return True

    def action_resend_code(self):
        for rec in self:
            rec._validate_login_prereqs()
            if not rec.phone_code_hash:
                raise UserError(_("No previous code hash found. Click Send Code first."))

            pair = rec._get_pending_client()
            if pair is None:
                _logger.warning(
                    "Pending login context missing for record %s; fallback to fresh send_code on pid=%s",
                    rec.id,
                    os.getpid(),
                )
                rec.action_send_code()
                return True
            client, loop = pair
            try:
                asyncio.set_event_loop(loop)
                sent = client.resend_code(rec._normalized_phone(), rec.phone_code_hash)
                rec.write(
                    {
                        "phone_code_hash": sent.phone_code_hash,
                        "auth_state": "code_sent",
                        "auth_expires_at": fields.Datetime.to_string(rec._now_utc() + timedelta(minutes=10)),
                        "code_delivery_type": str(getattr(sent, "type", "") or ""),
                        "code_next_type": str(getattr(sent, "next_type", "") or ""),
                        "code_timeout_seconds": int(getattr(sent, "timeout", 0) or 0),
                        "last_error": False,
                    }
                )
                _logger.info("Code resent for record %s on pid=%s", rec.id, os.getpid())
            except Exception as exc:
                rec._set_error(exc, "Failed to resend login code")
        return True

    def action_verify_code(self):
        """
        Verifies the SMS/Telegram code; if 2FA enabled, moves to password_required.
        """
        for rec in self:
            rec._validate_login_prereqs()

            code = (rec.auth_code or "").strip()
            numeric = "".join(ch for ch in code if ch.isdigit())
            if numeric:
                code = numeric
            if not code:
                raise UserError(_("Enter the received code first."))
            if not rec.phone_code_hash:
                raise UserError(_("Send code first."))
            if rec._is_expired():
                rec.write({"auth_state": "draft", "last_error": _("Code expired. Please send code again.")})
                raise UserError(_("Code expired. Please send code again."))

            try:
                client = rec._get_pending_client()
                if client is None:
                    rec.write(
                        {
                            "auth_state": "draft",
                            "auth_code": False,
                            "phone_code_hash": False,
                            "login_session_string": False,
                            "auth_expires_at": False,
                            "last_error": _(
                                "Pending login context not found (likely different Odoo worker/process). "
                                "Click Send Code and Verify Code in the same worker/session."
                            ),
                        }
                    )
                    raise UserError(
                        _(
                            "Pending login context not found. "
                            "This happens when Odoo uses multiple workers. "
                            "Use a single worker for login flow, then retry Send Code."
                        )
                    )

                pending_client, pending_loop = client
                asyncio.set_event_loop(pending_loop)
                pending_client.sign_in(
                    phone_number=rec._normalized_phone(),
                    phone_code_hash=rec.phone_code_hash,
                    phone_code=code,
                )

                session_string = pending_client.export_session_string()
                rec.write(
                    {
                        "session_string": session_string,
                        "auth_state": "authorized",
                        "auth_code": False,
                        "auth_password": False,
                        "phone_code_hash": False,
                        "login_session_string": False,
                        "auth_expires_at": False,
                        "last_error": False,
                    }
                )
                rec._disconnect_client(rec._pop_pending_client())
            except SessionPasswordNeeded:
                # 2FA enabled
                rec.write(
                    {
                        "auth_state": "password_required",
                        "auth_password": False,
                        "last_error": False,
                    }
                )
            except PhoneCodeExpired as exc:
                tg_error = rec._telegram_error_text(exc)
                _logger.warning("Telegram verify_code expired (record %s): %s", rec.id, tg_error)
                rec.write(
                    {
                        "auth_state": "draft",
                        "auth_code": False,
                        "phone_code_hash": False,
                        "login_session_string": False,
                        "auth_expires_at": False,
                        "last_error": tg_error,
                    }
                )
                rec._disconnect_client(rec._pop_pending_client())
                raise UserError(_("Telegram returned code expired. Check last_error and click Send Code again."))
            except PhoneCodeInvalid as exc:
                tg_error = rec._telegram_error_text(exc)
                _logger.warning("Telegram verify_code invalid (record %s): %s", rec.id, tg_error)
                rec.write(
                    {
                        "auth_state": "code_sent",
                        "auth_code": False,
                        "last_error": tg_error,
                    }
                )
                raise UserError(_("Telegram returned invalid code. Check last_error and enter latest code."))
            except Exception as exc:
                rec._disconnect_client(rec._pop_pending_client())
                rec._set_error(exc, "Failed to verify code")
        return True

    def action_verify_password(self):
        """
        Verifies 2FA password when required.
        """
        for rec in self:
            rec._validate_login_prereqs()

            if rec.auth_state != "password_required":
                raise UserError(_("Password step is not active."))

            password = (rec.auth_password or "").strip()
            if not password:
                raise UserError(_("Enter 2FA password first."))

            try:
                client = rec._get_pending_client()
                if client is None:
                    raise UserError(
                        _(
                            "Pending login context not found. "
                            "Click Send Code again, then Verify Code and Verify Password in the same worker/session."
                        )
                    )

                pending_client, pending_loop = client
                asyncio.set_event_loop(pending_loop)
                pending_client.check_password(password)

                session_string = pending_client.export_session_string()
                rec.write(
                    {
                        "session_string": session_string,
                        "auth_state": "authorized",
                        "auth_code": False,
                        "auth_password": False,
                        "phone_code_hash": False,
                        "login_session_string": False,
                        "auth_expires_at": False,
                        "last_error": False,
                    }
                )
                rec._disconnect_client(rec._pop_pending_client())
            except Exception as exc:
                rec._disconnect_client(rec._pop_pending_client())
                rec._set_error(exc, "Failed to verify password")
        return True

    def action_reset_auth(self):
        """
        Optional helper button: resets auth state to draft and clears transient fields.
        """
        for rec in self:
            rec.write({"auth_state": "draft", "last_error": False})
            rec._clear_auth_fields()
            rec._disconnect_client(rec._pop_pending_client())
        return True
