from odoo import api, fields, models


class TelegramUserChat(models.Model):
    _name = "telegram.user.chat"
    _description = "Telegram User Chat"
    _order = "title asc, id desc"

    name = fields.Char(compute="_compute_name", store=True)
    account_id = fields.Many2one("telegram.user.account", required=True, ondelete="cascade", index=True)
    chat_id = fields.Char(required=True, index=True, help="Telegram chat id, e.g. -1001234567890")
    title = fields.Char(required=True)
    username = fields.Char(index=True)
    chat_type = fields.Selection(
        [("group", "Group"), ("supergroup", "Supergroup")],
        required=True,
        default="group",
        index=True,
    )

    _sql_constraints = [
        ("uniq_account_chat", "unique(account_id, chat_id)", "Chat already exists for this account."),
    ]

    @api.depends("title", "chat_id")
    def _compute_name(self):
        for rec in self:
            rec.name = f"{rec.title} ({rec.chat_id})"

