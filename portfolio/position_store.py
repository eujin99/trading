from __future__ import annotations

from typing import Any

from storage import Database


class PositionStore:
    def __init__(self, db: Database):
        self.db = db

    def all(self) -> list[dict[str, Any]]:
        return self.db.get_positions()

    def upsert(self, position: dict[str, Any]) -> None:
        self.db.upsert_position(position)

    def remove(self, code: str) -> None:
        self.db.delete_position(code)
