from __future__ import annotations

from config import Settings


class ExitEngine:
    def __init__(self, settings: Settings):
        self.settings = settings

    def evaluate(self, position: dict, cur_price: int) -> dict | None:
        qty = int(position["qty"])
        stop = int(position["stop_price"])
        target1 = int(position["target1_price"])
        target2 = int(position["target2_price"])
        trailing_high = max(int(position.get("trailing_high", 0)), cur_price)

        if cur_price <= stop:
            return {"action": "stop_loss", "qty": qty, "trailing_high": trailing_high}

        if cur_price >= target2:
            return {"action": "target2", "qty": qty, "trailing_high": trailing_high}

        sold_half = int(position.get("sold_half", 0))
        if cur_price >= target1 and sold_half == 0:
            return {"action": "target1", "qty": max(1, qty // 2), "trailing_high": trailing_high}

        if sold_half:
            trail_stop = int(round(trailing_high * 0.98))
            if cur_price <= trail_stop:
                return {"action": "trailing_stop", "qty": qty, "trailing_high": trailing_high}

        return {"action": "hold", "qty": 0, "trailing_high": trailing_high}
