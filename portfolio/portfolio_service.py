from __future__ import annotations

from typing import Any

from config import Settings
from portfolio.position_store import PositionStore


class PortfolioService:
    def __init__(self, settings: Settings, store: PositionStore):
        self.settings = settings
        self.store = store

    def list_positions(self) -> list[dict[str, Any]]:
        return self.store.all()

    def get_position(self, code: str) -> dict[str, Any] | None:
        for row in self.store.all():
            if row["code"] == code:
                return row
        return None

    def upsert_position(self, code: str, name: str, qty: int, avg_price: int, market: str) -> None:
        stop_price = int(round(avg_price * (1 - self.settings.stop_loss_rate)))
        target1 = int(round(avg_price * (1 + self.settings.target_rate_1)))
        target2 = int(round(avg_price * (1 + self.settings.target_rate_2)))
        self.store.upsert(
            {
                "code": code,
                "market": market,
                "name": name,
                "qty": int(qty),
                "avg_price": int(avg_price),
                "stop_price": stop_price,
                "target1_price": target1,
                "target2_price": target2,
                "trailing_high": int(avg_price),
                "sold_half": 0,
            }
        )

    def reduce_position(self, code: str, sold_qty: int) -> dict[str, Any] | None:
        row = self.get_position(code)
        if not row:
            return None
        remain = int(row["qty"]) - int(sold_qty)
        if remain <= 0:
            self.store.remove(code)
            return None
        row["qty"] = remain
        self.store.upsert(row)
        return row

    def mark_half_sold(self, code: str) -> None:
        row = self.get_position(code)
        if not row:
            return
        row["sold_half"] = 1
        self.store.upsert(row)

    def update_trailing_high(self, code: str, high_price: int) -> None:
        row = self.get_position(code)
        if not row:
            return
        row["trailing_high"] = max(int(row.get("trailing_high", 0)), int(high_price))
        self.store.upsert(row)

    def apply_synced_balance(self, balances: list[dict[str, Any]], market: str) -> None:
        existing = {p["code"]: p for p in self.list_positions()}
        incoming_codes = set()
        for b in balances:
            code = str(b.get("code", "")).strip()
            qty = int(b.get("qty", 0))
            if not code or qty <= 0:
                continue
            incoming_codes.add(code)
            prev = existing.get(code)
            self.store.upsert(
                {
                    "code": code,
                    "market": market,
                    "name": b.get("name", code),
                    "qty": qty,
                    "avg_price": int(b.get("avg_price", 0)),
                    "stop_price": int(prev["stop_price"]) if prev else int(round(int(b.get("avg_price", 0)) * (1 - self.settings.stop_loss_rate))),
                    "target1_price": int(prev["target1_price"]) if prev else int(round(int(b.get("avg_price", 0)) * (1 + self.settings.target_rate_1))),
                    "target2_price": int(prev["target2_price"]) if prev else int(round(int(b.get("avg_price", 0)) * (1 + self.settings.target_rate_2))),
                    "trailing_high": int(prev["trailing_high"]) if prev else int(b.get("avg_price", 0)),
                    "sold_half": int(prev["sold_half"]) if prev else 0,
                }
            )
        for code in existing:
            if code not in incoming_codes:
                self.store.remove(code)
