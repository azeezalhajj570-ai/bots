from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError

try:
    from pyrogram import Client
    from pyrogram.errors import SessionPasswordNeeded
except Exception:  # pragma: no cover - runtime dependency guard
    Client = None
    SessionPasswordNeeded = Exception


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
    auth_expires_at = fields.Datetime(copy=False)
    last_error = fields.Text(copy=False)

    _sql_constraints = [
        ("uniq_account_ref_phone", "unique(account_ref, phone_number)", "Account ref + phone number must be unique."),
    ]

    @api.depends("account_ref", "phone_number")
    def _compute_name(self):
        for rec in self:
            rec.name = f"{rec.account_ref} | {rec.phone_number}"

    def _ensure_pyrogram(self) -> None:
        if Client is None:
            raise UserError("Pyrogram is not installed in this Odoo environment.")

    def _ensure_event_loop(self) -> None:
        try:
            asyncio.get_event_loop()
        except RuntimeError:
            asyncio.set_event_loop(asyncio.new_event_loop())

    def _session_name(self) -> str:
        self.ensure_one()
        return f"odoo_tg_login_{self.id}"

    def _build_client(self) -> Client:
        self.ensure_one()
        self._ensure_pyrogram()
        self._ensure_event_loop()
        return Client(
            name=self._session_name(),
            api_id=int(self.api_id),
            api_hash=self.api_hash,
        )

    def action_send_code(self):
        for rec in self:
            client = rec._build_client()
            try:
                client.connect()
                sent = client.send_code(rec.phone_number.strip())
                rec.write(
                    {
                        "phone_code_hash": sent.phone_code_hash,
                        "auth_state": "code_sent",
                        "auth_expires_at": fields.Datetime.to_string(datetime.utcnow() + timedelta(minutes=10)),
                        "last_error": False,
                    }
                )
            except Exception as exc:
                rec.write({"auth_state": "error", "last_error": str(exc)})
                raise UserError(f"Failed to send login code: {exc}") from exc
            finally:
                try:
                    client.disconnect()
                except Exception:
                    pass
        return True

    def action_verify_code(self):
        for rec in self:
            if not rec.auth_code:
                raise UserError("Enter the received code first.")
            if not rec.phone_code_hash:
                raise UserError("Send code first.")

            client = rec._build_client()
            try:
                client.connect()
                client.sign_in(
                    phone_number=rec.phone_number.strip(),
                    phone_code_hash=rec.phone_code_hash,
                    phone_code=rec.auth_code.strip(),
                )
                session_string = client.export_session_string()
                rec.write(
                    {
                        "session_string": session_string,
                        "auth_state": "authorized",
                        "auth_code": False,
                        "auth_password": False,
                        "last_error": False,
                    }
                )
            except SessionPasswordNeeded:
                rec.write({"auth_state": "password_required", "last_error": False})
            except Exception as exc:
                rec.write({"auth_state": "error", "last_error": str(exc)})
                raise UserError(f"Failed to verify code: {exc}") from exc
            finally:
                try:
                    client.disconnect()
                except Exception:
                    pass
        return True

    def action_verify_password(self):
        for rec in self:
            if rec.auth_state != "password_required":
                raise UserError("Password step is not active.")
            if not rec.auth_password:
                raise UserError("Enter 2FA password first.")

            client = rec._build_client()
            try:
                client.connect()
                client.check_password(rec.auth_password)
                session_string = client.export_session_string()
                rec.write(
                    {
                        "session_string": session_string,
                        "auth_state": "authorized",
                        "auth_code": False,
                        "auth_password": False,
                        "last_error": False,
                    }
                )
            except Exception as exc:
                rec.write({"auth_state": "error", "last_error": str(exc)})
                raise UserError(f"Failed to verify password: {exc}") from exc
            finally:
                try:
                    client.disconnect()
                except Exception:
                    pass
        return True

