from __future__ import annotations

from broker import KISClient
from data.cache import TTLCache


class MarketDataService:
    def __init__(self, client: KISClient, price_ttl_sec: int = 2):
        self.client = client
        self.price_cache = TTLCache(price_ttl_sec)

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
