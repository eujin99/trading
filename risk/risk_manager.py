from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from config import Settings
from risk.circuit_breaker import CircuitBreaker
from storage import Database


@dataclass
class RiskDecision:
    approved: bool
    reason: str = ""


class RiskManager:
    def __init__(self, settings: Settings, db: Database, breaker: CircuitBreaker):
        self.settings = settings
        self.db = db
        self.breaker = breaker
        self._today_reentry: dict[str, int] = {}

    def _trade_date(self) -> str:
        return datetime.now().strftime("%Y-%m-%d")

    def _daily_state(self) -> dict[str, Any]:
        return self.db.get_daily_pnl(self._trade_date())

    def register_pause(self, reason: str) -> None:
        self.breaker.pause(reason)
        self.db.add_risk_event("pause", "high", reason, {})

    def register_resume(self) -> None:
        self.breaker.resume()
        self.db.add_risk_event("resume", "info", "신규 매수 재개", {})

    def register_trade_result(self, realized_pnl: int) -> None:
        day = self._daily_state()
        trade_count = int(day["trade_count"]) + 1
        realized_sum = int(day["realized_pnl"]) + int(realized_pnl)
        loss_streak = int(day["loss_streak"]) + 1 if realized_pnl < 0 else 0
        self.db.update_daily_pnl(self._trade_date(), realized_sum, int(day["unrealized_pnl"]), trade_count, loss_streak)
        if loss_streak >= self.settings.max_consecutive_losses:
            self.register_pause("연속 손실 한도 도달")

    def approve_buy(
        self,
        code: str,
        estimated_loss: int,
        total_asset: int,
        invested_amount: int,
        cash_amount: int,
        current_position_count: int,
    ) -> RiskDecision:
        allowed, reason = self.breaker.can_open_new_position()
        if not allowed:
            self.db.add_risk_event("buy_reject", "high", reason, {"code": code})
            return RiskDecision(False, reason)

        day = self._daily_state()
        max_daily_loss = int(total_asset * self.settings.daily_max_loss_pct)
        if int(day["realized_pnl"]) <= -max_daily_loss:
            return RiskDecision(False, "일일 손실 한도 도달")
        if int(day["trade_count"]) >= self.settings.max_daily_trades:
            return RiskDecision(False, "일일 거래 횟수 한도 도달")
        if int(day["loss_streak"]) >= self.settings.max_consecutive_losses:
            return RiskDecision(False, "연속 손실 한도 도달")
        if current_position_count >= self.settings.max_stocks:
            return RiskDecision(False, "최대 동시 보유 종목 수 초과")

        today_key = f"{self._trade_date()}::{code}"
        if self._today_reentry.get(today_key, 0) >= self.settings.reentry_per_day:
            return RiskDecision(False, "동일 종목 재진입 제한")

        cash_ratio = (cash_amount / total_asset) if total_asset > 0 else 0.0
        if cash_ratio < self.settings.min_cash_pct:
            return RiskDecision(False, "현금 비중 하한 미달")

        invest_ratio = (invested_amount / total_asset) if total_asset > 0 else 1.0
        if invest_ratio > self.settings.max_total_invest_pct:
            return RiskDecision(False, "총 투자 비중 상한 초과")

        max_loss_per_trade = int(total_asset * self.settings.trade_risk_pct)
        if estimated_loss > max_loss_per_trade:
            return RiskDecision(False, "1회 거래 리스크 한도 초과")

        return RiskDecision(True, "")

    def on_buy_filled(self, code: str) -> None:
        today_key = f"{self._trade_date()}::{code}"
        self._today_reentry[today_key] = self._today_reentry.get(today_key, 0) + 1
