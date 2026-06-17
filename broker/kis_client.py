from __future__ import annotations

import importlib.util
import os
import sys
import types
from pathlib import Path
from typing import Any

from config import Settings


class KISClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        runtime_cfg = types.ModuleType("legacy_runtime_config")
        runtime_cfg.APP_KEY = settings.app_key
        runtime_cfg.APP_SECRET = settings.app_secret
        runtime_cfg.ACCOUNT_NO = settings.account_no
        runtime_cfg.BASE_URL = settings.base_url
        runtime_cfg.IS_VIRTUAL = settings.is_virtual
        runtime_cfg.US_EXCHANGE = settings.us_exchange
        runtime_cfg.US_UNIVERSE = settings.us_universe
        runtime_cfg.SCREENING_SOURCE_LIMIT = 120
        sys.modules["legacy_runtime_config"] = runtime_cfg
        os.environ["TRADER_CONFIG_MODULE"] = "legacy_runtime_config"

        legacy_path = Path(__file__).resolve().parents[1] / "files" / "kis_api.py"
        spec = importlib.util.spec_from_file_location("legacy_kis_api", legacy_path)
        if spec is None or spec.loader is None:
            raise RuntimeError("legacy kis_api 로드 실패")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.api = module

    def screening_candidates(self, market: str) -> list[dict[str, Any]]:
        return self.api.get_screening_candidates(market)

    def current_price(self, code: str, market: str) -> dict[str, Any]:
        return self.api.get_current_price_by_market(code, market) or {}

    def premarket_price(self, code: str, market: str) -> dict[str, Any]:
        return self.api.get_premarket_price_snapshot_by_market(code, market) or {}

    def available_cash(self, code: str, price: int, market: str) -> int:
        return int(self.api.get_available_cash_by_market(code, max(1, int(price)), market) or 0)

    def buy_market(self, code: str, qty: int, market: str) -> dict[str, Any]:
        return self.api.buy_market_order_by_market(code, int(qty), market) or {}

    def sell_market(self, code: str, qty: int, market: str) -> dict[str, Any]:
        return self.api.sell_market_order_by_market(code, int(qty), market) or {}

    def balance(self) -> list[dict[str, Any]]:
        return self.api.get_balance() or []

    def today_realized_pnl(self, market: str) -> int:
        return int(self.api.get_today_realized_pnl_by_market(market) or 0)

    def order_fills(self, order_id: str, market: str) -> dict[str, Any]:
        return self.api.get_order_fills_by_market(str(order_id or ""), market) or {}

    def minute_candles(self, code: str, market: str, count: int = 30) -> list[dict[str, Any]]:
        return self.api.get_intraday_minute_candles_by_market(code, market, int(count)) or []
