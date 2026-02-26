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
        string="Telegram Manager API Token",
        compute="_compute_tgm_api_token",
        inverse="_inverse_tgm_api_token",
        help="Bearer token required by /api/telegram/* endpoints for the current company.",
    )

    def _compute_tgm_api_token(self):
        for rec in self:
            rec.tgm_api_token = rec.env.company.sudo().tgm_api_token or False

    def _inverse_tgm_api_token(self):
        for rec in self:
            rec.env.company.sudo().write({"tgm_api_token": rec.tgm_api_token or False})
