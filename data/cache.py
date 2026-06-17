from __future__ import annotations

import time
from typing import Any


class TTLCache:
    def __init__(self, ttl_sec: float):
        self.ttl_sec = max(0.0, float(ttl_sec))
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        item = self._store.get(key)
        if not item:
            return None
        ts, value = item
        if self.ttl_sec > 0 and (time.time() - ts) > self.ttl_sec:
            self._store.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        self._store[key] = (time.time(), value)
