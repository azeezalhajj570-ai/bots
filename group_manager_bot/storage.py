from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class DynamicRule:
    id: int
    chat_id: int
    pattern: str
    enabled: bool = True


@dataclass(frozen=True)
class LinkRoute:
    chat_id: int
    keyword: str
    destination: str
    gate_group_id: int | None = None
    enabled: bool = True


@dataclass(frozen=True)
class ParticipationGate:
    chat_id: int
    gate_group_id: int
    gate_title: str
    join_url: str
    enabled: bool = True


class FeatureSettingsRepo(Protocol):
    def ensure_group(self, chat_id: int) -> None: ...
    def get_setting(self, chat_id: int, key: str) -> bool: ...
    def toggle_setting(self, chat_id: int, key: str) -> bool: ...


class WarnsRepo(Protocol):
    def add_warn(self, chat_id: int, user_id: int) -> int: ...
    def get_warns(self, chat_id: int, user_id: int) -> int: ...
    def set_warns(self, chat_id: int, user_id: int, warns: int) -> None: ...
    def reset_warns(self, chat_id: int, user_id: int) -> None: ...


class DynamicRulesRepo(Protocol):
    def add_dynamic_rule(self, chat_id: int, pattern: str) -> int: ...
    def list_dynamic_rules(self, chat_id: int) -> list[DynamicRule]: ...
    def delete_dynamic_rule(self, chat_id: int, rule_id: int) -> bool: ...


class LinkRoutesRepo(Protocol):
    def upsert_link_route(self, chat_id: int, keyword: str, destination: str, gate_group_id: int | None = None) -> None: ...
    def list_link_routes(self, chat_id: int) -> list[LinkRoute]: ...
    def delete_link_route(self, chat_id: int, keyword: str) -> bool: ...


class ParticipationGatesRepo(Protocol):
    def upsert_participation_gate(self, chat_id: int, gate_group_id: int, gate_title: str, join_url: str) -> None: ...
    def list_participation_gates(self, chat_id: int) -> list[ParticipationGate]: ...
    def delete_participation_gate(self, chat_id: int, gate_group_id: int) -> bool: ...


class BotRepository(
    FeatureSettingsRepo,
    WarnsRepo,
    DynamicRulesRepo,
    LinkRoutesRepo,
    ParticipationGatesRepo,
    Protocol,
):
    pass
