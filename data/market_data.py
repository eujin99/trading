from __future__ import annotations

from broker import KISClient
from data.cache import TTLCache


class MarketDataService:
    def __init__(self, client: KISClient, price_ttl_sec: int = 2):
        self.client = client
        self.price_cache = TTLCache(price_ttl_sec)
        self.minute_cache = TTLCache(5)
        self.market_cache = TTLCache(10)

    def get_price_detail(self, code: str, market: str, premarket: bool = False) -> dict:
        key = f"{market}:{code}:{'pre' if premarket else 'reg'}"
        cached = self.price_cache.get(key)
        if cached:
            return cached
        detail = (
            self.client.premarket_price(code, market)
            if premarket
            else self.client.current_price(code, market)
        ) or {}
        self.price_cache.set(key, detail)
        return detail

    def get_candidates(self, market: str) -> list[dict]:
        return self.client.screening_candidates(market)

    def get_minute_candles(self, code: str, market: str, count: int = 30) -> list[dict]:
        key = f"m:{market}:{code}:{int(count)}"
        cached = self.minute_cache.get(key)
        if cached is not None:
            return cached
        rows = self.client.minute_candles(code, market, count=int(count)) or []
        self.minute_cache.set(key, rows)
        return rows

    def get_market_snapshot(self, market: str) -> dict:
        key = f"s:{market}"
        cached = self.market_cache.get(key)
        if cached is not None:
            return cached
        snap = self.client.market_snapshot(market) or {}
        self.market_cache.set(key, snap)
        return snap
