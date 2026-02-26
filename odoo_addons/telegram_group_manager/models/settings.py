from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    tgm_api_token = fields.Char(
        string="Telegram Manager API Token",
        help="Bearer token required by /api/telegram/* endpoints for this company.",
    )


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    tgm_api_token = fields.Char(
        related="company_id.tgm_api_token",
        readonly=False,
        string="Telegram Manager API Token",
        help="Bearer token required by /api/telegram/* endpoints for the selected company.",
    )
