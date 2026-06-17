from __future__ import annotations

import time
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

    def _extract_fill_price(self, payload: dict[str, Any], fallback: int) -> int:
        output = payload.get("output", {}) if isinstance(payload.get("output"), dict) else {}
        candidates = [
            payload.get("avg_prvs"),
            payload.get("ord_unpr"),
            payload.get("stck_prpr"),
            output.get("avg_prvs"),
            output.get("ord_unpr"),
            output.get("stck_prpr"),
        ]
        for value in candidates:
            try:
                parsed = int(float(str(value).replace(",", "").strip()))
                if parsed > 0:
                    return parsed
            except Exception:
                continue
        return int(fallback)

    def _balance_qty(self, market: str, code: str) -> int:
        if market != "KR":
            return int(self.portfolio.get_position(code)["qty"]) if self.portfolio.get_position(code) else 0
        rows = self.client.balance()
        for row in rows:
            if not isinstance(row, dict):
                continue
            row_code = str(row.get("pdno", "")).strip() or str(row.get("mksc_shrn_iscd", "")).strip()
            if row_code != code:
                continue
            try:
                return int(float(str(row.get("hldg_qty", row.get("hold_qty", 0))).replace(",", "").strip()))
            except Exception:
                return 0
        return 0

    def _confirm_buy_fill(self, market: str, code: str, prev_qty: int, ordered_qty: int, attempts: int = 3) -> bool:
        target_qty = prev_qty + max(0, int(ordered_qty))
        for _ in range(max(1, attempts)):
            current = self._balance_qty(market, code)
            if current >= target_qty:
                return True
            time.sleep(0.7)
        return False

    def _confirm_sell_fill(self, market: str, code: str, prev_qty: int, sold_qty: int, attempts: int = 3) -> bool:
        target_qty = max(0, prev_qty - max(0, int(sold_qty)))
        for _ in range(max(1, attempts)):
            current = self._balance_qty(market, code)
            if current <= target_qty:
                return True
            time.sleep(0.7)
        return False

    def submit_buy(self, market: str, code: str, name: str, qty: int, price: int, retry: int = 2) -> tuple[bool, dict]:
        last = {}
        prev_qty = self._balance_qty(market, code)
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
                    "status": "requested" if ok else "failed",
                    "raw_response": last,
                    "requested_at": datetime.now().isoformat(),
                }
            )
            if ok:
                if self._confirm_buy_fill(market, code, prev_qty, qty):
                    fill_price = self._extract_fill_price(last, price)
                    self.db.update_order_status(order_id, "filled", last)
                    self.breaker.record_success()
                    self.portfolio.upsert_position(code, name, qty, fill_price, market)
                    self.db.add_trade(
                        {
                            "order_id": order_id,
                            "market": market,
                            "code": code,
                            "side": "BUY",
                            "qty": qty,
                            "fill_price": fill_price,
                        }
                    )
                    return True, last
                self.db.update_order_status(order_id, "accepted", {"response": last, "msg": "fill_not_confirmed"})
                return False, {"msg1": "주문 접수됨(체결 미확인)", "response": last}
            self.breaker.record_order_failure(last.get("msg1", "buy failed"))
        return False, last

    def submit_sell(self, market: str, code: str, qty: int, price: int, reason: str, retry: int = 2) -> tuple[bool, dict]:
        last = {}
        prev_qty = self._balance_qty(market, code)
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
                    "status": "requested" if ok else "failed",
                    "raw_response": {"reason": reason, "response": last},
                    "requested_at": datetime.now().isoformat(),
                }
            )
            if ok:
                if self._confirm_sell_fill(market, code, prev_qty, qty):
                    fill_price = self._extract_fill_price(last, price)
                    self.db.update_order_status(order_id, "filled", last)
                    self.breaker.record_success()
                    pos = self.portfolio.get_position(code)
                    avg = int(pos["avg_price"]) if pos else fill_price
                    realized = (fill_price - avg) * qty
                    self.portfolio.reduce_position(code, qty)
                    self.db.add_trade(
                        {
                            "order_id": order_id,
                            "market": market,
                            "code": code,
                            "side": "SELL",
                            "qty": qty,
                            "fill_price": fill_price,
                            "realized_pnl": realized,
                            "slippage": max(0, int(price) - int(fill_price)),
                        }
                    )
                    return True, {"response": last, "realized_pnl": realized, "fill_price": fill_price}
                self.db.update_order_status(order_id, "accepted", {"response": last, "msg": "fill_not_confirmed"})
                return False, {"msg1": "주문 접수됨(체결 미확인)", "response": last}
            self.breaker.record_order_failure(last.get("msg1", "sell failed"))
        return False, last
