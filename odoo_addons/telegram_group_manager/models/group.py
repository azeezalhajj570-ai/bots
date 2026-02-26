from __future__ import annotations

import json

from odoo import api, fields, models


DEFAULT_SETTINGS = {
    "anti_links": True,
    "anti_bots": True,
    "hide_system": False,
    "warn_in_dm": False,
    "warn_in_group": True,
}


class TgmGroup(models.Model):
    _name = "tgm.group"
    _description = "Telegram Group"

    name = fields.Char(required=True)
    chat_id = fields.Integer(required=True, index=True)
    username = fields.Char()
    active = fields.Boolean(default=True)

    setting_ids = fields.One2many("tgm.group.setting", "group_id", string="Settings")
    rule_ids = fields.One2many("tgm.rule", "group_id", string="Rules")
    route_ids = fields.One2many("tgm.route", "group_id", string="Routes")
    gate_ids = fields.One2many("tgm.gate", "group_id", string="Gates")

    _sql_constraints = [
        ("tgm_group_chat_id_uniq", "unique(chat_id)", "Chat ID must be unique."),
    ]

    @api.model
    def ensure_group(self, chat_id: int) -> "TgmGroup":
        group = self.search([("chat_id", "=", chat_id)], limit=1)
        if group:
            return group
        return self.create({"name": str(chat_id), "chat_id": chat_id})


class TgmGroupSetting(models.Model):
    _name = "tgm.group.setting"
    _description = "Telegram Group Setting"

    group_id = fields.Many2one("tgm.group", required=True, ondelete="cascade", index=True)
    feature_key = fields.Char(required=True, index=True)
    enabled = fields.Boolean(default=True)
    config_json = fields.Text(default="{}")

    _sql_constraints = [
        ("tgm_group_setting_uniq", "unique(group_id, feature_key)", "Feature key must be unique per group."),
    ]

    @api.model
    def get_settings_map(self, group: TgmGroup) -> dict:
        values = dict(DEFAULT_SETTINGS)
        for row in group.setting_ids:
            values[row.feature_key] = bool(row.enabled)
        return values

    @api.model
    def set_setting(self, group: TgmGroup, key: str, enabled: bool, config: dict | None = None) -> "TgmGroupSetting":
        setting = self.search([("group_id", "=", group.id), ("feature_key", "=", key)], limit=1)
        config_json = json.dumps(config or {}, ensure_ascii=False)
        vals = {"enabled": enabled, "config_json": config_json}
        if setting:
            setting.write(vals)
            return setting
        vals.update({"group_id": group.id, "feature_key": key})
        return self.create(vals)


class TgmRule(models.Model):
    _name = "tgm.rule"
    _description = "Telegram Dynamic Remove Rule"
    _order = "id asc"

    group_id = fields.Many2one("tgm.group", required=True, ondelete="cascade", index=True)
    pattern = fields.Char(required=True)
    enabled = fields.Boolean(default=True)


class TgmRoute(models.Model):
    _name = "tgm.route"
    _description = "Telegram Link Route"
    _order = "keyword asc"

    group_id = fields.Many2one("tgm.group", required=True, ondelete="cascade", index=True)
    keyword = fields.Char(required=True)
    destination = fields.Char(required=True)
    gate_group_id = fields.Integer()
    enabled = fields.Boolean(default=True)

    _sql_constraints = [
        ("tgm_route_group_keyword_uniq", "unique(group_id, keyword)", "Keyword must be unique per group."),
    ]


class TgmGate(models.Model):
    _name = "tgm.gate"
    _description = "Telegram Participation Gate"
    _order = "gate_title asc"

    group_id = fields.Many2one("tgm.group", required=True, ondelete="cascade", index=True)
    gate_group_id = fields.Integer(required=True)
    gate_title = fields.Char(required=True)
    join_url = fields.Char(required=True)
    enabled = fields.Boolean(default=True)

    _sql_constraints = [
        ("tgm_gate_group_gate_uniq", "unique(group_id, gate_group_id)", "Gate group must be unique per group."),
    ]


class TgmModLog(models.Model):
    _name = "tgm.mod.log"
    _description = "Telegram Moderation Log"
    _order = "create_date desc"

    group_id = fields.Many2one("tgm.group", ondelete="set null", index=True)
    chat_id = fields.Integer(index=True)
    action = fields.Char(required=True)
    reason = fields.Char()
    user_id = fields.Integer()
    meta_json = fields.Text(default="{}")


class TgmActionEvent(models.Model):
    _name = "tgm.action.event"
    _description = "Telegram Action Event"
    _order = "create_date desc"

    group_id = fields.Many2one("tgm.group", ondelete="set null", index=True)
    chat_id = fields.Integer(index=True)
    event_name = fields.Char(required=True)
    payload_json = fields.Text(default="{}")
