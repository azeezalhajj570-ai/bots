from __future__ import annotations

import logging
from typing import Any

from .cache import Cache
from .integrations.odoo_api_client import OdooApiClient
from .storage import BotRepository, DynamicRule, LinkRoute, ParticipationGate

log = logging.getLogger(__name__)


class ConfigProvider:
    def __init__(
        self,
        db: BotRepository,
        cache: Cache,
        odoo_client: OdooApiClient | None = None,
        ttl_seconds: int = 30,
    ) -> None:
        self.db = db
        self.cache = cache
        self.odoo_client = odoo_client
        self.ttl_seconds = ttl_seconds

    async def get_setting(self, chat_id: int, key: str) -> bool:
        if not self.odoo_client:
            return self.db.get_setting(chat_id, key)

        cache_key = f"cfg:settings:{chat_id}"
        cached = self.cache.get(cache_key)
        if isinstance(cached, dict) and key in cached:
            return bool(cached[key])

        try:
            payload = await self.odoo_client.get_group_settings(chat_id)
            settings = self._parse_settings_payload(payload)
            if settings:
                self.cache.set(cache_key, settings, self.ttl_seconds)
                if key in settings:
                    return bool(settings[key])
        except Exception as exc:
            log.warning("Settings API fallback chat=%s key=%s error=%s", chat_id, key, exc)

        value = self.db.get_setting(chat_id, key)
        if isinstance(cached, dict):
            merged = dict(cached)
            merged[key] = value
            self.cache.set(cache_key, merged, self.ttl_seconds)
        return value

    async def list_dynamic_rules(self, chat_id: int) -> list[DynamicRule]:
        if not self.odoo_client:
            return self.db.list_dynamic_rules(chat_id)

        cache_key = f"cfg:rules:{chat_id}"
        cached = self.cache.get(cache_key)
        if isinstance(cached, list):
            return cached

        try:
            payload = await self.odoo_client.get_rules(chat_id)
            parsed = self._parse_rules_payload(chat_id, payload)
            if parsed:
                self.cache.set(cache_key, parsed, self.ttl_seconds)
                return parsed
        except Exception as exc:
            log.warning("Rules API fallback chat=%s error=%s", chat_id, exc)

        result = self.db.list_dynamic_rules(chat_id)
        self.cache.set(cache_key, result, self.ttl_seconds)
        return result

    async def list_link_routes(self, chat_id: int) -> list[LinkRoute]:
        if not self.odoo_client:
            return self.db.list_link_routes(chat_id)

        cache_key = f"cfg:routes:{chat_id}"
        cached = self.cache.get(cache_key)
        if isinstance(cached, list):
            return cached

        try:
            payload = await self.odoo_client.get_routes(chat_id)
            parsed = self._parse_routes_payload(chat_id, payload)
            if parsed:
                self.cache.set(cache_key, parsed, self.ttl_seconds)
                return parsed
        except Exception as exc:
            log.warning("Routes API fallback chat=%s error=%s", chat_id, exc)

        result = self.db.list_link_routes(chat_id)
        self.cache.set(cache_key, result, self.ttl_seconds)
        return result

    async def list_participation_gates(self, chat_id: int) -> list[ParticipationGate]:
        if not self.odoo_client:
            return self.db.list_participation_gates(chat_id)

        cache_key = f"cfg:gates:{chat_id}"
        cached = self.cache.get(cache_key)
        if isinstance(cached, list):
            return cached

        try:
            payload = await self.odoo_client.get_gates(chat_id)
            parsed = self._parse_gates_payload(chat_id, payload)
            if parsed:
                self.cache.set(cache_key, parsed, self.ttl_seconds)
                return parsed
        except Exception as exc:
            log.warning("Gates API fallback chat=%s error=%s", chat_id, exc)

        result = self.db.list_participation_gates(chat_id)
        self.cache.set(cache_key, result, self.ttl_seconds)
        return result

    @staticmethod
    def _parse_settings_payload(payload: Any) -> dict[str, bool]:
        data = payload.get("data", payload) if isinstance(payload, dict) else payload
        if isinstance(data, dict):
            settings: dict[str, bool] = {}
            for key, value in data.items():
                if isinstance(value, bool):
                    settings[key] = value
                elif isinstance(value, int):
                    settings[key] = value == 1
                elif isinstance(value, str):
                    settings[key] = value.strip().lower() in {"1", "true", "yes", "on"}
            return settings
        return {}

    @staticmethod
    def _extract_list(payload: Any) -> list[dict[str, Any]]:
        data = payload
        if isinstance(payload, dict):
            if isinstance(payload.get("data"), list):
                data = payload["data"]
            elif isinstance(payload.get("items"), list):
                data = payload["items"]
            elif isinstance(payload.get("results"), list):
                data = payload["results"]
        if not isinstance(data, list):
            return []
        return [item for item in data if isinstance(item, dict)]

    def _parse_rules_payload(self, chat_id: int, payload: Any) -> list[DynamicRule]:
        rows = self._extract_list(payload)
        rules: list[DynamicRule] = []
        for row in rows:
            pattern = (row.get("pattern") or "").strip()
            if not pattern:
                continue
            rule_id = int(row.get("id") or 0)
            enabled = bool(row.get("enabled", True))
            rules.append(DynamicRule(id=rule_id, chat_id=chat_id, pattern=pattern, enabled=enabled))
        return rules

    def _parse_routes_payload(self, chat_id: int, payload: Any) -> list[LinkRoute]:
        rows = self._extract_list(payload)
        routes: list[LinkRoute] = []
        for row in rows:
            keyword = (row.get("keyword") or "").strip().lower()
            destination = (row.get("destination") or "").strip()
            if not keyword or not destination:
                continue
            gate_group_id = row.get("gate_group_id")
            routes.append(
                LinkRoute(
                    chat_id=chat_id,
                    keyword=keyword,
                    destination=destination,
                    gate_group_id=int(gate_group_id) if gate_group_id is not None else None,
                    enabled=bool(row.get("enabled", True)),
                )
            )
        return routes

    def _parse_gates_payload(self, chat_id: int, payload: Any) -> list[ParticipationGate]:
        rows = self._extract_list(payload)
        gates: list[ParticipationGate] = []
        for row in rows:
            gate_group_id = row.get("gate_group_id")
            join_url = (row.get("join_url") or "").strip()
            title = (row.get("gate_title") or "").strip()
            if gate_group_id is None or not join_url:
                continue
            gates.append(
                ParticipationGate(
                    chat_id=chat_id,
                    gate_group_id=int(gate_group_id),
                    gate_title=title or str(gate_group_id),
                    join_url=join_url,
                    enabled=bool(row.get("enabled", True)),
                )
            )
        return gates
