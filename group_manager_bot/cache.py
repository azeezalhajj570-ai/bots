from __future__ import annotations

import time
from typing import Any, Protocol


class Cache(Protocol):
    def get(self, key: str) -> Any: ...
    def set(self, key: str, value: Any, ttl: int) -> None: ...
    def delete(self, key: str) -> None: ...


class MemoryCache(Cache):
    def __init__(self) -> None:
        self._items: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any:
        item = self._items.get(key)
        if item is None:
            return None
        expires_at, value = item
        if expires_at <= time.time():
            self._items.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any, ttl: int) -> None:
        self._items[key] = (time.time() + ttl, value)

    def delete(self, key: str) -> None:
        self._items.pop(key, None)

