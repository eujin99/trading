from __future__ import annotations

from datetime import datetime
from typing import Any

from broker.kis_client import KISClient
from portfolio import PortfolioService
from risk import CircuitBreaker
from storage import Database


class OrderManager:
    def __init__(self, client: KISClient, db: Database, portfolio: PortfolioService, breaker: CircuitBreaker):
        self.client = client
        self.db = db
        self.portfolio = portfolio
        self.breaker = breaker

    def _extract_order_id(self, payload: dict[str, Any]) -> str:
        return str(payload.get("ODNO") or payload.get("odno") or payload.get("output", {}).get("ODNO", "")).strip()

    def submit_buy(self, market: str, code: str, name: str, qty: int, price: int, retry: int = 2) -> tuple[bool, dict]:
        last = {}
        for _ in range(max(1, retry + 1)):
            last = self.client.buy_market(code, qty, market)
            ok = str(last.get("rt_cd", "")) == "0"
            order_id = self._extract_order_id(last)
            self.db.add_order(
                {
                    "order_id": order_id,
                    "market": market,
                    "code": code,
                    "side": "BUY",
                    "qty": qty,
                    "price": price,
                    "status": "filled" if ok else "failed",
                    "raw_response": last,
                    "requested_at": datetime.now().isoformat(),
                }
            )
            if ok:
                self.breaker.record_success()
                self.portfolio.upsert_position(code, name, qty, price, market)
                self.db.add_trade(
                    {
                        "order_id": order_id,
                        "market": market,
                        "code": code,
                        "side": "BUY",
                        "qty": qty,
                        "fill_price": price,
                    }
                )
                return True, last
            self.breaker.record_order_failure(last.get("msg1", "buy failed"))
        return False, last

    def submit_sell(self, market: str, code: str, qty: int, price: int, reason: str, retry: int = 2) -> tuple[bool, dict]:
        last = {}
        for _ in range(max(1, retry + 1)):
            last = self.client.sell_market(code, qty, market)
            ok = str(last.get("rt_cd", "")) == "0"
            order_id = self._extract_order_id(last)
            self.db.add_order(
                {
                    "order_id": order_id,
                    "market": market,
                    "code": code,
                    "side": "SELL",
                    "qty": qty,
                    "price": price,
                    "status": "filled" if ok else "failed",
                    "raw_response": {"reason": reason, "response": last},
                    "requested_at": datetime.now().isoformat(),
                }
            )
            if ok:
                self.breaker.record_success()
                pos = self.portfolio.get_position(code)
                avg = int(pos["avg_price"]) if pos else price
                realized = (price - avg) * qty
                self.portfolio.reduce_position(code, qty)
                self.db.add_trade(
                    {
                        "order_id": order_id,
                        "market": market,
                        "code": code,
                        "side": "SELL",
                        "qty": qty,
                        "fill_price": price,
                        "realized_pnl": realized,
                        "slippage": 0,
                    }
                )
                return True, {"response": last, "realized_pnl": realized}
            self.breaker.record_order_failure(last.get("msg1", "sell failed"))
        return False, last
