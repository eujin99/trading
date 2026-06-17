from __future__ import annotations

import importlib.util
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
LEGACY_CONFIG_DIR = ROOT_DIR / "files"


def _as_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _as_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    s = str(value).strip().lower()
    if s in {"1", "true", "y", "yes", "on"}:
        return True
    if s in {"0", "false", "n", "no", "off"}:
        return False
    return default


def _load_legacy_module(module_name: str) -> ModuleType:
    cfg_path = LEGACY_CONFIG_DIR / f"{module_name}.py"
    if not cfg_path.exists():
        raise FileNotFoundError(f"설정 파일을 찾을 수 없습니다: {cfg_path}")
    spec = importlib.util.spec_from_file_location(module_name, cfg_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"설정 모듈 로드 실패: {module_name}")
    module = importlib.util.module_from_spec(spec)
    legacy_path = str(LEGACY_CONFIG_DIR)
    if legacy_path not in sys.path:
        sys.path.insert(0, legacy_path)
    spec.loader.exec_module(module)
    return module


@dataclass
class Settings:
    app_key: str
    app_secret: str
    account_no: str
    is_virtual: bool
    base_url: str
    default_market: str = "KR"
    us_exchange: str = "NAS"
    us_universe: list[str] = field(default_factory=list)
    max_stocks: int = 3
    buy_pct: float = 0.15
    buy_min_amount: int = 300000
    buy_max_amount: int = 1500000
    min_cash_ratio: float = 0.30
    target_rate_1: float = 0.05
    target_rate_2: float = 0.10
    stop_loss_rate: float = 0.03
    post_dca_stop_loss_rate: float = 0.02
    score_threshold: int = 75
    daily_max_loss_pct: float = 0.015
    trade_risk_pct: float = 0.005
    max_daily_trades: int = 5
    max_consecutive_losses: int = 2
    max_position_pct: float = 0.15
    max_total_invest_pct: float = 0.70
    min_cash_pct: float = 0.30
    reentry_per_day: int = 1
    max_spread_pct: float = 0.8
    min_trend_score: float = 55.0
    max_gap_up_pct: float = 8.0
    require_price_above_vwap: bool = True
    loss_streak_risk_multiplier: float = 0.7
    daily_drawdown_risk_multiplier: float = 0.5
    dca_enabled: bool = False
    api_error_limit: int = 3
    order_fail_limit: int = 2
    market_open: str = "09:00"
    force_sell_time: str = "15:20"
    premarket_start: str = "08:00"
    auto_screen_interval_sec: int = 20
    monitor_interval_sec: int = 2
    telegram_enabled: bool = False
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    db_path: str = str(ROOT_DIR / "trading.db")

    @property
    def account_number(self) -> str:
        return self.account_no.split("-")[0]


def load_settings(module_name: str | None = None) -> Settings:
    selected = module_name or os.getenv("TRADER_CONFIG_MODULE", "config")
    module = _load_legacy_module(selected)

    default_base_url = (
        "https://openapivts.koreainvestment.com:29443"
        if _as_bool(getattr(module, "IS_VIRTUAL", True), True)
        else "https://openapi.koreainvestment.com:9443"
    )
    min_cash_ratio = _as_float(getattr(module, "MIN_CASH_RATIO", 0.30), 0.30)
    min_cash_pct = _as_float(getattr(module, "MIN_CASH_PCT", min_cash_ratio), min_cash_ratio)
    max_total_invest = _as_float(
        getattr(module, "MAX_TOTAL_INVEST_PCT", max(0.0, 1.0 - min_cash_pct)),
        max(0.0, 1.0 - min_cash_pct),
    )

    return Settings(
        app_key=str(getattr(module, "APP_KEY", "")),
        app_secret=str(getattr(module, "APP_SECRET", "")),
        account_no=str(getattr(module, "ACCOUNT_NO", "")),
        is_virtual=_as_bool(getattr(module, "IS_VIRTUAL", True), True),
        base_url=str(getattr(module, "BASE_URL", default_base_url)),
        default_market=str(getattr(module, "DEFAULT_MARKET", "KR")).upper(),
        us_exchange=str(getattr(module, "US_EXCHANGE", "NAS")).upper(),
        us_universe=list(getattr(module, "US_UNIVERSE", [])),
        max_stocks=_as_int(getattr(module, "MAX_STOCKS", 3), 3),
        buy_pct=_as_float(getattr(module, "BUY_PCT", 0.15), 0.15),
        buy_min_amount=_as_int(getattr(module, "BUY_MIN_AMOUNT", 300000), 300000),
        buy_max_amount=_as_int(getattr(module, "BUY_MAX_AMOUNT", 1500000), 1500000),
        min_cash_ratio=min_cash_ratio,
        target_rate_1=_as_float(getattr(module, "TARGET_RATE_1", 0.05), 0.05),
        target_rate_2=_as_float(getattr(module, "TARGET_RATE_2", 0.10), 0.10),
        stop_loss_rate=_as_float(getattr(module, "STOP_LOSS_RATE", 0.03), 0.03),
        post_dca_stop_loss_rate=_as_float(getattr(module, "POST_DCA_STOP_LOSS_RATE", 0.02), 0.02),
        score_threshold=_as_int(getattr(module, "SCORE_THRESHOLD", 75), 75),
        max_spread_pct=_as_float(getattr(module, "MAX_SPREAD_PCT", 0.8), 0.8),
        min_trend_score=_as_float(getattr(module, "MIN_TREND_SCORE", 55.0), 55.0),
        max_gap_up_pct=_as_float(getattr(module, "MAX_GAP_UP_PCT", 8.0), 8.0),
        require_price_above_vwap=_as_bool(getattr(module, "REQUIRE_PRICE_ABOVE_VWAP", True), True),
        loss_streak_risk_multiplier=_as_float(getattr(module, "LOSS_STREAK_RISK_MULTIPLIER", 0.7), 0.7),
        daily_drawdown_risk_multiplier=_as_float(
            getattr(module, "DAILY_DRAWDOWN_RISK_MULTIPLIER", 0.5),
            0.5,
        ),
        daily_max_loss_pct=_as_float(getattr(module, "DAILY_MAX_LOSS_PCT", 0.015), 0.015),
        trade_risk_pct=_as_float(getattr(module, "TRADE_RISK_PCT", 0.005), 0.005),
        max_daily_trades=_as_int(getattr(module, "MAX_DAILY_TRADES", 5), 5),
        max_consecutive_losses=_as_int(getattr(module, "MAX_CONSECUTIVE_LOSSES", 2), 2),
        max_position_pct=_as_float(getattr(module, "MAX_POSITION_PCT", 0.15), 0.15),
        max_total_invest_pct=max_total_invest,
        min_cash_pct=min_cash_pct,
        reentry_per_day=_as_int(getattr(module, "REENTRY_PER_DAY", 1), 1),
        dca_enabled=_as_bool(getattr(module, "DCA_ENABLED", False), False),
        api_error_limit=_as_int(getattr(module, "API_ERROR_LIMIT", 3), 3),
        order_fail_limit=_as_int(getattr(module, "ORDER_FAIL_LIMIT", 2), 2),
        market_open=str(getattr(module, "MARKET_OPEN", "09:00")),
        force_sell_time=str(getattr(module, "FORCE_SELL_TIME", "15:20")),
        premarket_start=str(getattr(module, "PREMARKET_START", "08:00")),
        auto_screen_interval_sec=_as_int(getattr(module, "AUTO_SCREEN_INTERVAL_SEC", 20), 20),
        monitor_interval_sec=max(1, _as_int(getattr(module, "PORTFOLIO_SCORE_INTERVAL_SEC", 2), 2)),
        telegram_enabled=_as_bool(getattr(module, "TELEGRAM_NOTIFY_ENABLED", False), False),
        telegram_bot_token=str(getattr(module, "TELEGRAM_BOT_TOKEN", "")),
        telegram_chat_id=str(getattr(module, "TELEGRAM_CHAT_ID", "")),
    )
