from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    tgm_api_token = fields.Char(
        string="Telegram Manager API Token",
        config_parameter="telegram_group_manager.api_token",
        help="Bearer token required by /api/telegram/* endpoints.",
    )
