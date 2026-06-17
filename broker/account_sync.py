from __future__ import annotations

from broker.kis_client import KISClient
from portfolio import PortfolioService
from storage import Database


def _to_int(value) -> int:
    try:
        return int(float(str(value).replace(",", "").strip()))
    except Exception:
        return 0


class AccountSyncService:
    def __init__(self, client: KISClient, portfolio: PortfolioService, db: Database):
        self.client = client
        self.portfolio = portfolio
        self.db = db

    def _parse_balance_row(self, row: dict) -> dict | None:
        code = str(row.get("pdno", "")).strip() or str(row.get("mksc_shrn_iscd", "")).strip()
        qty = _to_int(row.get("hldg_qty", row.get("hold_qty", 0)))
        if not code or qty <= 0:
            return None
        avg_price = _to_int(row.get("pchs_avg_pric", 0))
        if avg_price <= 0:
            avg_price = _to_int(row.get("prpr", 1))
        return {
            "code": code,
            "name": str(row.get("prdt_name", "")).strip() or code,
            "qty": qty,
            "avg_price": max(1, avg_price),
        }

    def sync(self, market: str) -> list[dict]:
        if market != "KR":
            return []
        rows = self.client.balance()
        parsed = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            item = self._parse_balance_row(row)
            if item:
                parsed.append(item)
        self.portfolio.apply_synced_balance(parsed, market)
        self.db.log("INFO", "account_sync", "계좌 동기화 완료", {"market": market, "count": len(parsed)})
        return parsed
