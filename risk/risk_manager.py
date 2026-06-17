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

    def _trade_date(self) -> str:
        return datetime.now().strftime("%Y-%m-%d")

    def _daily_state(self) -> dict[str, Any]:
        return self.db.get_daily_pnl(self._trade_date())

    def buy_risk_multiplier(self, total_asset: int) -> float:
        """
        손실 누적 시 신규 진입 수량을 자동 축소한다.
        - 연속 손실 1회 이상: LOSS_STREAK_RISK_MULTIPLIER 적용
        - 일일 손실의 50% 이상 도달: DAILY_DRAWDOWN_RISK_MULTIPLIER 적용
        """
        day = self._daily_state()
        multiplier = 1.0

        if int(day.get("loss_streak", 0)) >= 1:
            multiplier *= max(0.1, float(self.settings.loss_streak_risk_multiplier))

        if total_asset > 0:
            drawdown_trigger = -int(total_asset * self.settings.daily_max_loss_pct * 0.5)
            if int(day.get("realized_pnl", 0)) <= drawdown_trigger:
                multiplier *= max(0.1, float(self.settings.daily_drawdown_risk_multiplier))

        return max(0.1, min(1.0, multiplier))

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
        order_amount: int,
        total_asset: int,
        invested_amount: int,
        cash_amount: int,
        current_position_count: int,
        current_position_amount: int = 0,
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

        guard = self.db.get_symbol_guard(self._trade_date(), code)
        if int(guard.get("stopped_out", 0)) > 0:
            return RiskDecision(False, "당일 손절 종목 재진입 금지")
        if int(guard.get("buy_count", 0)) >= self.settings.reentry_per_day:
            return RiskDecision(False, "동일 종목 재진입 제한")

        post_cash = cash_amount - max(0, int(order_amount))
        post_invested = invested_amount + max(0, int(order_amount))
        post_position = current_position_amount + max(0, int(order_amount))
        post_cash_ratio = (post_cash / total_asset) if total_asset > 0 else 0.0
        if post_cash_ratio < self.settings.min_cash_pct:
            return RiskDecision(False, "매수 후 현금 비중 하한 미달")

        post_invest_ratio = (post_invested / total_asset) if total_asset > 0 else 1.0
        if post_invest_ratio > self.settings.max_total_invest_pct:
            return RiskDecision(False, "매수 후 총 투자 비중 상한 초과")

        post_position_ratio = (post_position / total_asset) if total_asset > 0 else 1.0
        if post_position_ratio > self.settings.max_position_pct:
            return RiskDecision(False, "종목당 최대 비중 상한 초과")

        max_loss_per_trade = int(total_asset * self.settings.trade_risk_pct)
        if estimated_loss > max_loss_per_trade:
            return RiskDecision(False, "1회 거래 리스크 한도 초과")

        return RiskDecision(True, "")

    def on_buy_filled(self, code: str) -> None:
        guard = self.db.get_symbol_guard(self._trade_date(), code)
        self.db.update_symbol_guard(
            trade_date=self._trade_date(),
            code=code,
            buy_count=int(guard.get("buy_count", 0)) + 1,
            sell_count=int(guard.get("sell_count", 0)),
            stopped_out=int(guard.get("stopped_out", 0)),
        )

    def on_sell_filled(self, code: str, stop_loss: bool = False) -> None:
        guard = self.db.get_symbol_guard(self._trade_date(), code)
        self.db.update_symbol_guard(
            trade_date=self._trade_date(),
            code=code,
            buy_count=int(guard.get("buy_count", 0)),
            sell_count=int(guard.get("sell_count", 0)) + 1,
            stopped_out=1 if stop_loss else int(guard.get("stopped_out", 0)),
        )
