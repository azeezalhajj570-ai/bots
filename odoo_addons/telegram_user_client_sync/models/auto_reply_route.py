from odoo import api, fields, models
from odoo.exceptions import ValidationError


class TelegramAutoReplyRoute(models.Model):
    _name = "telegram.auto.reply.route"
    _description = "Telegram Auto Reply Route"
    _order = "account_ref, chat_id, keyword"

    name = fields.Char(compute="_compute_name", store=True)
    account_id = fields.Many2one("telegram.user.account", required=True, ondelete="cascade", index=True)
    account_ref = fields.Char(related="account_id.account_ref", store=True, readonly=True, index=True)
    phone_number = fields.Char(related="account_id.phone_number", store=True, readonly=True, index=True)
    chat_ref_id = fields.Many2one("telegram.user.chat", ondelete="set null")
    chat_id = fields.Char(required=True, index=True, help="Telegram group chat id, e.g. -1001234567890")
    keyword = fields.Char(required=True, index=True)
    response = fields.Text(required=True)
    enabled = fields.Boolean(default=True, index=True)

    _sql_constraints = [
        (
            "uniq_account_phone_chat_keyword",
            "unique(account_id, chat_id, keyword)",
            "The keyword already exists for this account/phone and chat.",
        ),
    ]

    @api.depends("account_ref", "phone_number", "chat_id", "keyword")
    def _compute_name(self):
        for rec in self:
            rec.name = f"[{rec.account_ref} | {rec.phone_number}] {rec.chat_id} :: {rec.keyword}"

    @api.constrains("keyword", "response")
    def _check_not_empty(self):
        for rec in self:
            if not (rec.keyword or "").strip():
                raise ValidationError("Keyword cannot be empty.")
            if not (rec.response or "").strip():
                raise ValidationError("Response cannot be empty.")
            if not (rec.chat_id or "").strip():
                raise ValidationError("Chat ID cannot be empty.")

    @api.onchange("chat_ref_id")
    def _onchange_chat_ref_id(self):
        for rec in self:
            if rec.chat_ref_id:
                rec.chat_id = rec.chat_ref_id.chat_id
