from __future__ import annotations

import logging
from typing import Any
from urllib.parse import quote

import httpx

log = logging.getLogger(__name__)


class OdooApiClient:
    def __init__(self, base_url: str, token: str, timeout_seconds: int = 10) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout_seconds = timeout_seconds

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{self.base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(url, headers=self._headers(), params=params)
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            log.error("Odoo API GET failed url=%s error=%s", url, exc)
            raise

    async def _post(self, path: str, payload: dict[str, Any]) -> Any:
        url = f"{self.base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(url, headers=self._headers(), json=payload)
            response.raise_for_status()
            if response.text:
                return response.json()
            return {"ok": True}
        except Exception as exc:
            log.error("Odoo API POST failed url=%s error=%s", url, exc)
            raise

    async def _delete(self, path: str) -> Any:
        url = f"{self.base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.delete(url, headers=self._headers())
            response.raise_for_status()
            if response.text:
                return response.json()
            return {"ok": True}
        except Exception as exc:
            log.error("Odoo API DELETE failed url=%s error=%s", url, exc)
            raise

    async def get_groups(self) -> Any:
        return await self._get("/api/telegram/groups")

    async def get_group_settings(self, chat_id: int) -> Any:
        return await self._get(f"/api/telegram/groups/{chat_id}/settings")

    async def get_rules(self, chat_id: int) -> Any:
        return await self._get(f"/api/telegram/groups/{chat_id}/rules")

    async def get_routes(self, chat_id: int) -> Any:
        return await self._get(f"/api/telegram/groups/{chat_id}/routes")

    async def get_gates(self, chat_id: int) -> Any:
        return await self._get(f"/api/telegram/groups/{chat_id}/gates")

    async def post_mod_log(self, payload: dict[str, Any]) -> Any:
        return await self._post("/api/telegram/logs/mod", payload)

    async def post_action_event(self, payload: dict[str, Any]) -> Any:
        return await self._post("/api/telegram/events/action", payload)

    async def upsert_rule(self, chat_id: int, rule_id: int, pattern: str, enabled: bool = True) -> Any:
        return await self._post(
            f"/api/telegram/groups/{chat_id}/rules",
            {"id": rule_id, "pattern": pattern, "enabled": enabled},
        )

    async def delete_rule(self, chat_id: int, rule_id: int) -> Any:
        return await self._delete(f"/api/telegram/groups/{chat_id}/rules/{rule_id}")

    async def upsert_route(
        self,
        chat_id: int,
        keyword: str,
        destination: str,
        gate_group_id: int | None = None,
        enabled: bool = True,
    ) -> Any:
        return await self._post(
            f"/api/telegram/groups/{chat_id}/routes",
            {
                "keyword": keyword,
                "destination": destination,
                "gate_group_id": gate_group_id,
                "enabled": enabled,
            },
        )

    async def delete_route(self, chat_id: int, keyword: str) -> Any:
        return await self._delete(f"/api/telegram/groups/{chat_id}/routes/{quote(keyword, safe='')}")

    async def upsert_gate(
        self,
        chat_id: int,
        gate_group_id: int,
        gate_title: str,
        join_url: str,
        enabled: bool = True,
    ) -> Any:
        return await self._post(
            f"/api/telegram/groups/{chat_id}/gates",
            {
                "gate_group_id": gate_group_id,
                "gate_title": gate_title,
                "join_url": join_url,
                "enabled": enabled,
            },
        )

    async def delete_gate(self, chat_id: int, gate_group_id: int) -> Any:
        return await self._delete(f"/api/telegram/groups/{chat_id}/gates/{gate_group_id}")
