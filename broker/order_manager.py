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

    def _fetch_fill_snapshot(
        self,
        market: str,
        order_id: str,
        code: str,
        prev_qty: int,
        ordered_qty: int,
        side: str,
        attempts: int = 4,
    ) -> dict[str, int | str]:
        """
        체결조회 API를 우선 사용하고, 조회 불가 시 잔고 수량 변화로 fallback 한다.
        """
        order_id = str(order_id or "").strip()
        for _ in range(max(1, attempts)):
            if order_id:
                info = self.client.order_fills(order_id, market)
                filled = int(info.get("filled_qty", 0) or 0)
                ordered = int(info.get("ordered_qty", ordered_qty) or ordered_qty)
                avg = int(info.get("avg_fill_price", 0) or 0)
                status = str(info.get("status", "")).strip().lower()
                if filled > 0:
                    if ordered > 0 and filled >= ordered and status in {"filled", "partial", ""}:
                        status = "filled"
                    elif status not in {"filled", "partial"}:
                        status = "partial"
                    return {
                        "filled_qty": min(max(0, filled), max(0, ordered_qty)),
                        "ordered_qty": max(0, ordered if ordered > 0 else ordered_qty),
                        "avg_fill_price": max(0, avg),
                        "status": status,
                    }
            time.sleep(0.7)

        current = self._balance_qty(market, code)
        if side == "BUY":
            filled = max(0, current - prev_qty)
        else:
            filled = max(0, prev_qty - current)
        if filled <= 0:
            return {"filled_qty": 0, "ordered_qty": max(0, ordered_qty), "avg_fill_price": 0, "status": "none"}
        status = "filled" if filled >= max(0, ordered_qty) else "partial"
        return {
            "filled_qty": min(filled, max(0, ordered_qty)),
            "ordered_qty": max(0, ordered_qty),
            "avg_fill_price": 0,
            "status": status,
        }

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
                fill = self._fetch_fill_snapshot(
                    market=market,
                    order_id=order_id,
                    code=code,
                    prev_qty=prev_qty,
                    ordered_qty=qty,
                    side="BUY",
                )
                filled_qty = int(fill.get("filled_qty", 0) or 0)
                if filled_qty <= 0:
                    self.db.update_order_status(order_id, "accepted", {"response": last, "msg": "fill_not_confirmed"})
                    return False, {"msg1": "주문 접수됨(체결 미확인)", "response": last}

                fill_price = int(fill.get("avg_fill_price", 0) or 0)
                if fill_price <= 0:
                    fill_price = self._extract_fill_price(last, price)
                is_full = filled_qty >= int(qty)
                self.db.update_order_status(order_id, "filled" if is_full else "partial_filled", last)
                self.breaker.record_success()
                self.portfolio.upsert_position(code, name, filled_qty, fill_price, market)
                self.db.add_trade(
                    {
                        "order_id": order_id,
                        "market": market,
                        "code": code,
                        "side": "BUY",
                        "qty": filled_qty,
                        "fill_price": fill_price,
                    }
                )
                return True, {
                    "response": last,
                    "filled_qty": filled_qty,
                    "fill_price": fill_price,
                    "partial": not is_full,
                }
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
                fill = self._fetch_fill_snapshot(
                    market=market,
                    order_id=order_id,
                    code=code,
                    prev_qty=prev_qty,
                    ordered_qty=qty,
                    side="SELL",
                )
                filled_qty = int(fill.get("filled_qty", 0) or 0)
                if filled_qty <= 0:
                    self.db.update_order_status(order_id, "accepted", {"response": last, "msg": "fill_not_confirmed"})
                    return False, {"msg1": "주문 접수됨(체결 미확인)", "response": last}

                fill_price = int(fill.get("avg_fill_price", 0) or 0)
                if fill_price <= 0:
                    fill_price = self._extract_fill_price(last, price)
                is_full = filled_qty >= int(qty)
                self.db.update_order_status(order_id, "filled" if is_full else "partial_filled", last)
                self.breaker.record_success()
                pos = self.portfolio.get_position(code)
                avg = int(pos["avg_price"]) if pos else fill_price
                realized = (fill_price - avg) * filled_qty
                self.portfolio.reduce_position(code, filled_qty)
                self.db.add_trade(
                    {
                        "order_id": order_id,
                        "market": market,
                        "code": code,
                        "side": "SELL",
                        "qty": filled_qty,
                        "fill_price": fill_price,
                        "realized_pnl": realized,
                        "slippage": max(0, int(price) - int(fill_price)),
                    }
                )
                return True, {
                    "response": last,
                    "realized_pnl": realized,
                    "fill_price": fill_price,
                    "filled_qty": filled_qty,
                    "partial": not is_full,
                }
            self.breaker.record_order_failure(last.get("msg1", "sell failed"))
        return False, last
