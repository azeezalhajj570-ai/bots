from __future__ import annotations

import json

from odoo import http
from odoo.http import request


class TelegramGroupManagerApi(http.Controller):
    def _response(self, payload: dict, status: int = 200):
        return request.make_json_response(payload, status=status)

    def _parse_payload(self) -> dict:
        payload = request.httprequest.get_json(silent=True)
        return payload if isinstance(payload, dict) else {}

    def _authorized_company(self):
        company_model = request.env["res.company"].sudo()
        token_companies = company_model.search([("tgm_api_token", "!=", False)])
        # Backward-compatible local/dev mode: if no company token configured, allow env company.
        if not token_companies:
            return request.env.company.sudo()
        auth_header = request.httprequest.headers.get("Authorization", "")
        token = auth_header.replace("Bearer", "", 1).strip() if auth_header else ""
        if not token:
            return False
        return company_model.search([("tgm_api_token", "=", token)], limit=1)

    def _ensure_auth(self):
        company = self._authorized_company()
        if company:
            return company, None
        return None, self._response({"ok": False, "error": "unauthorized"}, status=401)

    def _group_by_chat_id(self, chat_id: int, company_id: int):
        return request.env["tgm.group"].sudo().ensure_group(chat_id, company_id=company_id)

    @http.route("/api/telegram/groups", type="http", auth="none", methods=["GET"], csrf=False)
    def get_groups(self, **kwargs):
        company, unauthorized = self._ensure_auth()
        if unauthorized:
            return unauthorized
        groups = request.env["tgm.group"].sudo().search(
            ["|", ("company_id", "=", company.id), ("company_id", "=", False)]
        )
        legacy_groups = groups.filtered(lambda g: not g.company_id)
        if legacy_groups:
            legacy_groups.write({"company_id": company.id})
            groups = request.env["tgm.group"].sudo().search([("company_id", "=", company.id)])
        data = [
            {
                "chat_id": group.chat_id,
                "name": group.name,
                "username": group.username or "",
                "active": bool(group.active),
                "company_id": group.company_id.id,
            }
            for group in groups
        ]
        return self._response({"ok": True, "data": data})

    @http.route("/api/telegram/groups/<int:chat_id>/settings", type="http", auth="none", methods=["GET"], csrf=False)
    def get_group_settings(self, chat_id: int, **kwargs):
        company, unauthorized = self._ensure_auth()
        if unauthorized:
            return unauthorized
        group = self._group_by_chat_id(chat_id, company.id)
        settings_map = request.env["tgm.group.setting"].sudo().get_settings_map(group)
        return self._response({"ok": True, "data": settings_map})

    @http.route("/api/telegram/groups/<int:chat_id>/rules", type="http", auth="none", methods=["GET"], csrf=False)
    def get_rules(self, chat_id: int, **kwargs):
        company, unauthorized = self._ensure_auth()
        if unauthorized:
            return unauthorized
        group = self._group_by_chat_id(chat_id, company.id)
        data = [
            {"id": row.id, "pattern": row.pattern, "enabled": bool(row.enabled)}
            for row in group.rule_ids.sorted("id")
        ]
        return self._response({"ok": True, "data": data})

    @http.route("/api/telegram/groups/<int:chat_id>/routes", type="http", auth="none", methods=["GET"], csrf=False)
    def get_routes(self, chat_id: int, **kwargs):
        company, unauthorized = self._ensure_auth()
        if unauthorized:
            return unauthorized
        group = self._group_by_chat_id(chat_id, company.id)
        data = [
            {
                "keyword": row.keyword,
                "destination": row.destination,
                "gate_group_id": row.gate_group_id if row.gate_group_id else None,
                "enabled": bool(row.enabled),
            }
            for row in group.route_ids.sorted("keyword")
        ]
        return self._response({"ok": True, "data": data})

    @http.route("/api/telegram/groups/<int:chat_id>/gates", type="http", auth="none", methods=["GET"], csrf=False)
    def get_gates(self, chat_id: int, **kwargs):
        company, unauthorized = self._ensure_auth()
        if unauthorized:
            return unauthorized
        group = self._group_by_chat_id(chat_id, company.id)
        data = [
            {
                "gate_group_id": row.gate_group_id,
                "gate_title": row.gate_title,
                "join_url": row.join_url,
                "enabled": bool(row.enabled),
            }
            for row in group.gate_ids.sorted("gate_title")
        ]
        return self._response({"ok": True, "data": data})

    @http.route("/api/telegram/groups/<int:chat_id>/rules", type="http", auth="none", methods=["POST"], csrf=False)
    def post_rule(self, chat_id: int, **kwargs):
        company, unauthorized = self._ensure_auth()
        if unauthorized:
            return unauthorized
        payload = self._parse_payload()
        pattern = str(payload.get("pattern", "")).strip()
        if not pattern:
            return self._response({"ok": False, "error": "pattern_required"}, status=400)
        group = self._group_by_chat_id(chat_id, company.id)
        rule_id = payload.get("id")
        rule_model = request.env["tgm.rule"].sudo()
        rule = rule_model.browse(int(rule_id)) if rule_id else rule_model
        if rule_id and rule.exists() and rule.group_id.id == group.id:
            rule.write({"pattern": pattern, "enabled": bool(payload.get("enabled", True))})
        else:
            rule = rule_model.create(
                {
                    "group_id": group.id,
                    "pattern": pattern,
                    "enabled": bool(payload.get("enabled", True)),
                }
            )
        return self._response({"ok": True, "id": rule.id})

    @http.route(
        "/api/telegram/groups/<int:chat_id>/rules/<int:rule_id>",
        type="http",
        auth="none",
        methods=["DELETE"],
        csrf=False,
    )
    def delete_rule(self, chat_id: int, rule_id: int, **kwargs):
        company, unauthorized = self._ensure_auth()
        if unauthorized:
            return unauthorized
        group = self._group_by_chat_id(chat_id, company.id)
        rule = request.env["tgm.rule"].sudo().search([("id", "=", rule_id), ("group_id", "=", group.id)], limit=1)
        if not rule:
            return self._response({"ok": False, "error": "not_found"}, status=404)
        rule.unlink()
        return self._response({"ok": True})

    @http.route("/api/telegram/groups/<int:chat_id>/routes", type="http", auth="none", methods=["POST"], csrf=False)
    def post_route(self, chat_id: int, **kwargs):
        company, unauthorized = self._ensure_auth()
        if unauthorized:
            return unauthorized
        payload = self._parse_payload()
        keyword = str(payload.get("keyword", "")).strip().lower()
        destination = str(payload.get("destination", "")).strip()
        if not keyword or not destination:
            return self._response({"ok": False, "error": "keyword_destination_required"}, status=400)

        group = self._group_by_chat_id(chat_id, company.id)
        route_model = request.env["tgm.route"].sudo()
        route = route_model.search([("group_id", "=", group.id), ("keyword", "=", keyword)], limit=1)
        values = {
            "destination": destination,
            "gate_group_id": int(payload["gate_group_id"]) if payload.get("gate_group_id") is not None else False,
            "enabled": bool(payload.get("enabled", True)),
        }
        if route:
            route.write(values)
        else:
            values.update({"group_id": group.id, "keyword": keyword})
            route = route_model.create(values)
        return self._response({"ok": True, "keyword": route.keyword})

    @http.route(
        "/api/telegram/groups/<int:chat_id>/routes/<string:keyword>",
        type="http",
        auth="none",
        methods=["DELETE"],
        csrf=False,
    )
    def delete_route(self, chat_id: int, keyword: str, **kwargs):
        company, unauthorized = self._ensure_auth()
        if unauthorized:
            return unauthorized
        group = self._group_by_chat_id(chat_id, company.id)
        normalized = (keyword or "").strip().lower()
        route = request.env["tgm.route"].sudo().search(
            [("group_id", "=", group.id), ("keyword", "=", normalized)],
            limit=1,
        )
        if not route:
            return self._response({"ok": False, "error": "not_found"}, status=404)
        route.unlink()
        return self._response({"ok": True})

    @http.route("/api/telegram/groups/<int:chat_id>/gates", type="http", auth="none", methods=["POST"], csrf=False)
    def post_gate(self, chat_id: int, **kwargs):
        company, unauthorized = self._ensure_auth()
        if unauthorized:
            return unauthorized
        payload = self._parse_payload()
        gate_group_id = payload.get("gate_group_id")
        join_url = str(payload.get("join_url", "")).strip()
        if gate_group_id is None or not join_url:
            return self._response({"ok": False, "error": "gate_group_id_join_url_required"}, status=400)
        gate_title = str(payload.get("gate_title", "")).strip() or str(gate_group_id)
        group = self._group_by_chat_id(chat_id, company.id)
        gate_model = request.env["tgm.gate"].sudo()
        gate = gate_model.search(
            [("group_id", "=", group.id), ("gate_group_id", "=", int(gate_group_id))],
            limit=1,
        )
        values = {
            "gate_title": gate_title,
            "join_url": join_url,
            "enabled": bool(payload.get("enabled", True)),
        }
        if gate:
            gate.write(values)
        else:
            values.update({"group_id": group.id, "gate_group_id": int(gate_group_id)})
            gate = gate_model.create(values)
        return self._response({"ok": True, "gate_group_id": gate.gate_group_id})

    @http.route(
        "/api/telegram/groups/<int:chat_id>/gates/<int:gate_group_id>",
        type="http",
        auth="none",
        methods=["DELETE"],
        csrf=False,
    )
    def delete_gate(self, chat_id: int, gate_group_id: int, **kwargs):
        company, unauthorized = self._ensure_auth()
        if unauthorized:
            return unauthorized
        group = self._group_by_chat_id(chat_id, company.id)
        gate = request.env["tgm.gate"].sudo().search(
            [("group_id", "=", group.id), ("gate_group_id", "=", gate_group_id)],
            limit=1,
        )
        if not gate:
            return self._response({"ok": False, "error": "not_found"}, status=404)
        gate.unlink()
        return self._response({"ok": True})

    @http.route("/api/telegram/logs/mod", type="http", auth="none", methods=["POST"], csrf=False)
    def post_mod_log(self, **kwargs):
        company, unauthorized = self._ensure_auth()
        if unauthorized:
            return unauthorized
        payload = self._parse_payload()
        chat_id = int(payload.get("chat_id") or 0)
        group = (
            request.env["tgm.group"].sudo().search(
                [("chat_id", "=", chat_id), ("company_id", "=", company.id)],
                limit=1,
            )
            if chat_id
            else False
        )
        request.env["tgm.mod.log"].sudo().create(
            {
                "group_id": group.id if group else False,
                "company_id": company.id,
                "chat_id": chat_id or False,
                "action": str(payload.get("action", "")).strip() or "unknown",
                "reason": str(payload.get("reason", "")).strip(),
                "user_id": int(payload.get("user_id")) if payload.get("user_id") is not None else False,
                "meta_json": json.dumps(payload.get("meta", {}), ensure_ascii=False),
            }
        )
        return self._response({"ok": True})

    @http.route("/api/telegram/events/action", type="http", auth="none", methods=["POST"], csrf=False)
    def post_action_event(self, **kwargs):
        company, unauthorized = self._ensure_auth()
        if unauthorized:
            return unauthorized
        payload = self._parse_payload()
        chat_id = int(payload.get("chat_id") or 0)
        group = (
            request.env["tgm.group"].sudo().search(
                [("chat_id", "=", chat_id), ("company_id", "=", company.id)],
                limit=1,
            )
            if chat_id
            else False
        )
        request.env["tgm.action.event"].sudo().create(
            {
                "group_id": group.id if group else False,
                "company_id": company.id,
                "chat_id": chat_id or False,
                "event_name": str(payload.get("event_name", "")).strip() or "unknown",
                "payload_json": json.dumps(payload.get("payload", {}), ensure_ascii=False),
            }
        )
        return self._response({"ok": True})
