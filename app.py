from __future__ import annotations

import argparse
import datetime as dt
import json
import threading
import time
from pathlib import Path

from broker import AccountSyncService, KISClient, OrderManager
from config import load_settings
from data import MarketDataService
from notify import TelegramNotifier
from portfolio import PortfolioService, PositionStore
from risk import CircuitBreaker, PositionSizer, RiskManager
from storage import Database
from strategy import ExitEngine, Screener, SignalEngine


def _to_int(v, default=0):
    try:
        return int(float(str(v).replace(",", "").strip()))
    except Exception:
        return default


def _parse_hhmm(raw: str, fallback: str) -> dt.time:
    value = str(raw or "").strip() or fallback
    try:
        h, m = value.split(":")
        return dt.time(int(h), int(m))
    except Exception:
        h, m = fallback.split(":")
        return dt.time(int(h), int(m))


class TradingApp:
    def __init__(self, config_module: str = "config"):
        self.settings = load_settings(config_module)
        self.db = Database(self.settings.db_path)
        self.client = KISClient(self.settings)
        self.store = PositionStore(self.db)
        self.portfolio = PortfolioService(self.settings, self.store)
        self.breaker = CircuitBreaker(self.settings.api_error_limit, self.settings.order_fail_limit)
        self.risk = RiskManager(self.settings, self.db, self.breaker)
        self.market_data = MarketDataService(self.client, price_ttl_sec=2)
        self.screener = Screener(self.settings, self.market_data)
        self.signals = SignalEngine(self.settings, self.db, self.screener)
        self.exit_engine = ExitEngine(self.settings)
        self.order_manager = OrderManager(
            self.client,
            self.db,
            self.portfolio,
            self.breaker,
            fee_rate=self.settings.fee_rate,
            sell_tax_rate=self.settings.sell_tax_rate,
            partial_retry_max=self.settings.partial_retry_max,
            partial_retry_sleep_sec=self.settings.partial_retry_sleep_sec,
        )
        self.account_sync = AccountSyncService(self.client, self.portfolio, self.db)
        self.notifier = TelegramNotifier(self.settings)
        self.sizer = PositionSizer()
        self.market = self.settings.default_market
        self.stop_event = threading.Event()
        self.buy_paused = False
        self._closeout_day = ""
        self._closeout_steps_done: set[str] = set()
        self._migrate_legacy_state()
        self._bind_commands()

    def _migrate_legacy_state(self) -> None:
        root = Path(__file__).resolve().parent
        legacy_pnl = root / "files" / ".realized_pnl_state.json"
        legacy_guard = root / "files" / ".daily_trade_guard_state.json"
        today = dt.datetime.now().strftime("%Y-%m-%d")
        if legacy_pnl.exists():
            try:
                raw = json.loads(legacy_pnl.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    for _, v in raw.items():
                        if isinstance(v, dict) and v.get("date") == today:
                            self.db.update_daily_pnl(
                                trade_date=today,
                                realized_pnl=int(v.get("pnl", 0)),
                                unrealized_pnl=0,
                                trade_count=0,
                                loss_streak=0,
                            )
                            break
            except Exception:
                pass
        if legacy_guard.exists():
            try:
                raw = json.loads(legacy_guard.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    payload = {}
                    for key, v in raw.items():
                        if isinstance(v, dict) and v.get("date") == today:
                            payload[key] = {"bought": v.get("bought", []), "sold": v.get("sold", [])}
                    if payload:
                        self.db.set_param("legacy_trade_guard", json.dumps(payload, ensure_ascii=False))
            except Exception:
                pass

    def _bind_commands(self) -> None:
        self.notifier.bind_handler("/status", lambda _: self.command_status())
        self.notifier.bind_handler("/holdings", lambda _: self.command_holdings())
        self.notifier.bind_handler("/risk", lambda _: self.command_risk())
        self.notifier.bind_handler("/pause", lambda _: self.command_pause())
        self.notifier.bind_handler("/resume", lambda _: self.command_resume())
        self.notifier.bind_handler("/sellall", lambda _: self.command_sellall())
        self.notifier.bind_handler("/stop", lambda _: self.command_stop())
        self.notifier.bind_handler("/report", lambda _: self.command_report())
        self.notifier.bind_handler("/sell", self.command_sell)

    def log(self, message: str, level: str = "INFO", source: str = "app", notify: bool = False):
        print(f"[{dt.datetime.now().strftime('%H:%M:%S')}] {message}")
        self.db.log(level, source, message, {})
        if notify:
            self.notifier.send(message)

    def command_status(self) -> str:
        state = "PAUSED" if self.buy_paused or self.breaker.state.paused else "RUNNING"
        return f"상태: {state}, 시장:{self.market}, 보유:{len(self.portfolio.list_positions())}개"

    def command_holdings(self) -> str:
        rows = self.portfolio.list_positions()
        if not rows:
            return "보유 종목이 없습니다."
        lines = ["보유 종목:"]
        for r in rows:
            lines.append(f"- {r['name']}({r['code']}) {r['qty']}주 avg:{r['avg_price']}")
        return "\n".join(lines)

    def command_risk(self) -> str:
        day = self.db.get_daily_pnl(dt.datetime.now().strftime("%Y-%m-%d"))
        return (
            f"리스크 현황\n"
            f"- realized_pnl: {day['realized_pnl']}\n"
            f"- trade_count: {day['trade_count']}\n"
            f"- loss_streak: {day['loss_streak']}\n"
            f"- breaker_paused: {self.breaker.state.paused}"
        )

    def command_pause(self) -> str:
        self.buy_paused = True
        self.risk.register_pause("텔레그램 pause")
        return "신규 매수를 중단했습니다."

    def command_resume(self) -> str:
        self.buy_paused = False
        self.risk.register_resume()
        return "신규 매수를 재개했습니다."

    def command_sell(self, arg: str) -> str:
        parts = arg.split()
        if len(parts) != 2:
            return "사용법: /sell 종목코드 비율(0~1)"
        code = parts[0].strip()
        ratio = float(parts[1])
        pos = self.portfolio.get_position(code)
        if not pos:
            return "해당 종목 보유 없음"
        qty = max(1, int(int(pos["qty"]) * ratio))
        price = _to_int(self.market_data.get_price_detail(code, pos["market"]).get("stck_prpr", pos["avg_price"]), pos["avg_price"])
        ok, info = self.order_manager.submit_sell(pos["market"], code, qty, price, "telegram_sell")
        if not ok:
            return f"매도 실패: {info.get('msg1', 'unknown')}"
        self.risk.register_trade_result(int(info.get("realized_pnl", 0)))
        self.risk.on_sell_filled(code, stop_loss=False)
        filled_qty = int(info.get("filled_qty", qty))
        return f"{code} {filled_qty}주 매도 완료"

    def command_sellall(self) -> str:
        count = 0
        for p in list(self.portfolio.list_positions()):
            price = _to_int(self.market_data.get_price_detail(p["code"], p["market"]).get("stck_prpr", p["avg_price"]), p["avg_price"])
            ok, info = self.order_manager.submit_sell(p["market"], p["code"], int(p["qty"]), price, "sellall")
            if ok:
                count += 1
                self.risk.register_trade_result(int(info.get("realized_pnl", 0)))
                self.risk.on_sell_filled(p["code"], stop_loss=False)
        return f"전량 정리 완료: {count}종목"

    def command_stop(self) -> str:
        self.buy_paused = True
        self.stop_event.set()
        self.risk.register_pause("텔레그램 stop")
        return "봇 긴급 중단"

    def command_report(self) -> str:
        day = self.db.get_daily_pnl(dt.datetime.now().strftime("%Y-%m-%d"))
        return f"당일 리포트: realized={day['realized_pnl']} trades={day['trade_count']} loss_streak={day['loss_streak']}"

    def _total_asset_snapshot(self) -> tuple[int, int, int]:
        positions = self.portfolio.list_positions()
        eval_sum = 0
        for p in positions:
            price = _to_int(self.market_data.get_price_detail(p["code"], p["market"]).get("stck_prpr", p["avg_price"]), p["avg_price"])
            eval_sum += price * int(p["qty"])
        ref_code = positions[0]["code"] if positions else "005930"
        ref_price = positions[0]["avg_price"] if positions else 70000
        cash = self.client.available_cash(ref_code, ref_price, self.market)
        total = eval_sum + cash
        return total, eval_sum, cash

    def _screening_loop(self):
        interval = max(5, self.settings.auto_screen_interval_sec)
        while not self.stop_event.is_set():
            try:
                now = dt.datetime.now()
                open_t = _parse_hhmm(self.settings.market_open, "09:00")
                close_t = _parse_hhmm(self.settings.force_sell_time, "15:20")
                pre_t = _parse_hhmm(self.settings.premarket_start, "08:00")
                if now.weekday() >= 5:
                    time.sleep(interval)
                    continue
                if pre_t <= now.time() < open_t:
                    _ = self.signals.generate_buy_signals(self.market, premarket=True)
                elif open_t <= now.time() < close_t and not self.buy_paused:
                    if now.time() >= _parse_hhmm("15:15", "15:15"):
                        time.sleep(interval)
                        continue
                    signals = self.signals.generate_buy_signals(self.market, premarket=False)
                    for s in signals:
                        total, invested, cash = self._total_asset_snapshot()
                        existing = self.portfolio.get_position(s["code"])
                        existing_amount = 0
                        if existing:
                            existing_amount = int(existing["qty"]) * int(s["price"])
                        qty = self.sizer.size_from_risk(total, self.settings.trade_risk_pct, s["price"], s["stop_price"])
                        qty = int(qty * self.risk.buy_risk_multiplier(total))
                        qty = max(0, min(qty, int(self.settings.buy_max_amount // max(1, s["price"]))))
                        if qty <= 0:
                            continue
                        order_amount = int(s["price"]) * int(qty)
                        estimated_loss = (s["price"] - s["stop_price"]) * qty
                        decision = self.risk.approve_buy(
                            code=s["code"],
                            estimated_loss=estimated_loss,
                            order_amount=order_amount,
                            total_asset=total,
                            invested_amount=invested,
                            cash_amount=cash,
                            current_position_count=len(self.portfolio.list_positions()),
                            current_position_amount=existing_amount,
                        )
                        if not decision.approved:
                            self.db.add_risk_event("buy_reject", "warn", decision.reason, {"code": s["code"]})
                            continue
                        ok, payload = self.order_manager.submit_buy(
                            self.market,
                            s["code"],
                            s["name"],
                            qty,
                            s["price"],
                            retry=2,
                        )
                        if ok:
                            self.risk.on_buy_filled(s["code"])
                            filled_qty = int(payload.get("filled_qty", qty))
                            fill_price = int(payload.get("fill_price", s["price"]))
                            suffix = " (부분체결)" if payload.get("partial") else ""
                            self.notifier.send(
                                f"매수 체결{suffix}: {s['name']}({s['code']}) {filled_qty}주 @ {fill_price}"
                            )
                        else:
                            self.notifier.send(f"매수 실패: {s['name']}({s['code']}) {payload.get('msg1', '')}")
                else:
                    time.sleep(interval)
                    continue
            except Exception as e:
                self.breaker.record_api_error(str(e))
                self.db.add_risk_event("screening_loop_error", "high", str(e), {})
                self.notifier.send(f"API 오류: {e}")
            time.sleep(interval)

    def _position_monitor_loop(self):
        interval = max(1, self.settings.monitor_interval_sec)
        while not self.stop_event.is_set():
            try:
                self.account_sync.sync(self.market)
                for p in list(self.portfolio.list_positions()):
                    detail = self.market_data.get_price_detail(p["code"], p["market"])
                    price = _to_int(detail.get("stck_prpr", p["avg_price"]), p["avg_price"])
                    decision = self.exit_engine.evaluate(p, price)
                    self.portfolio.update_trailing_high(p["code"], int(decision.get("trailing_high", price)))
                    action = decision["action"]
                    if action == "hold":
                        continue
                    qty = int(decision["qty"])
                    ok, info = self.order_manager.submit_sell(p["market"], p["code"], qty, price, action, retry=2)
                    if not ok:
                        continue
                    realized = int(info.get("realized_pnl", 0))
                    filled_qty = int(info.get("filled_qty", qty))
                    fill_price = int(info.get("fill_price", price))
                    self.risk.register_trade_result(realized)
                    self.risk.on_sell_filled(p["code"], stop_loss=(action == "stop_loss"))
                    if action == "target1":
                        self.portfolio.mark_half_sold(p["code"])
                    suffix = " (부분체결)" if info.get("partial") else ""
                    self.notifier.send(
                        f"매도 체결[{action}]{suffix}: {p['name']}({p['code']}) {filled_qty}주 @ {fill_price} / pnl {realized:+,}"
                    )
            except Exception as e:
                self.breaker.record_api_error(str(e))
                self.db.add_risk_event("position_loop_error", "high", str(e), {})
            time.sleep(interval)

    def _risk_loop(self):
        while not self.stop_event.is_set():
            try:
                total, _, _ = self._total_asset_snapshot()
                day = self.db.get_daily_pnl(dt.datetime.now().strftime("%Y-%m-%d"))
                if int(day["realized_pnl"]) <= -int(total * self.settings.daily_max_loss_pct):
                    self.buy_paused = True
                    self.risk.register_pause("일일 손실 제한 도달")
                    self.notifier.send("일일 손실 한도 도달로 신규 매수 중단")
            except Exception as e:
                self.db.add_risk_event("risk_loop_error", "warn", str(e), {})
            time.sleep(5)

    def _closeout_loop(self):
        while not self.stop_event.is_set():
            try:
                now = dt.datetime.now()
                if now.weekday() < 5:
                    today = now.strftime("%Y-%m-%d")
                    if self._closeout_day != today:
                        self._closeout_day = today
                        self._closeout_steps_done.clear()
                    no_buy = _parse_hhmm("15:15", "15:15")
                    if now.time() >= no_buy:
                        self.buy_paused = True

                    def _run_closeout_step(step_key: str, reason: str):
                        if step_key in self._closeout_steps_done:
                            return
                        self._closeout_steps_done.add(step_key)
                        sold = 0
                        for p in list(self.portfolio.list_positions()):
                            price = _to_int(
                                self.market_data.get_price_detail(p["code"], p["market"]).get("stck_prpr", p["avg_price"]),
                                p["avg_price"],
                            )
                            ok, info = self.order_manager.submit_sell(
                                p["market"],
                                p["code"],
                                int(p["qty"]),
                                price,
                                reason,
                            )
                            if ok:
                                sold += 1
                                self.risk.register_trade_result(int(info.get("realized_pnl", 0)))
                                self.risk.on_sell_filled(p["code"], stop_loss=False)
                        remain = len(self.portfolio.list_positions())
                        self.notifier.send(f"장마감 정리[{step_key}] 완료: 매도 {sold}종목 / 잔여 {remain}종목")
                        if remain > 0:
                            self.db.add_risk_event(
                                "closeout_pending",
                                "warn",
                                f"{step_key} 이후 미정리 잔량 존재",
                                {"remaining_count": remain},
                            )

                    hhmm = now.strftime("%H:%M")
                    if hhmm == "15:20":
                        _run_closeout_step("15:20", "market_close_1")
                    elif hhmm == "15:24":
                        _run_closeout_step("15:24", "market_close_2")
                    elif hhmm == "15:28":
                        _run_closeout_step("15:28", "market_close_3")
                    elif hhmm == "15:29" and "15:29" not in self._closeout_steps_done:
                        self._closeout_steps_done.add("15:29")
                        remain = len(self.portfolio.list_positions())
                        if remain > 0:
                            self.notifier.send(f"긴급: 장마감 직전 미체결/잔량 {remain}종목")
                            self.db.add_risk_event(
                                "closeout_emergency",
                                "high",
                                "15:29 기준 미정리 포지션 존재",
                                {"remaining_count": remain},
                            )
            except Exception as e:
                self.db.add_risk_event("closeout_loop_error", "warn", str(e), {})
            time.sleep(2)

    def run(self):
        self.log("봇 시작", notify=True)
        self.notifier.send("장 시작 감시 루프 가동")
        threads = [
            threading.Thread(target=self._screening_loop, daemon=True),
            threading.Thread(target=self._position_monitor_loop, daemon=True),
            threading.Thread(target=self._risk_loop, daemon=True),
            threading.Thread(target=self._closeout_loop, daemon=True),
        ]
        for th in threads:
            th.start()
        try:
            while not self.stop_event.is_set():
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop_event.set()
            self.log("사용자 중단", notify=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config-module", default="config")
    args = parser.parse_args()
    app = TradingApp(config_module=args.config_module)
    app.run()


if __name__ == "__main__":
    main()
