from __future__ import annotations


class PositionSizer:
    @staticmethod
    def size_from_risk(total_asset: int, risk_pct: float, entry_price: int, stop_price: int) -> int:
        entry = max(1, int(entry_price))
        stop = max(1, int(stop_price))
        per_share_risk = max(1, entry - stop)
        allowed_loss = max(0, int(total_asset * risk_pct))
        if allowed_loss <= 0:
            return 0
        return max(0, allowed_loss // per_share_risk)
