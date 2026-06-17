from __future__ import annotations

import re

from config import Settings
from data import MarketDataService, MinuteDataService
from strategy.scoring import ScoreEngine


class Screener:
    def __init__(self, settings: Settings, market_data: MarketDataService):
        self.settings = settings
        self.market_data = market_data
        self.minute_data = MinuteDataService()
        self.scorer = ScoreEngine()

    def _is_risky_name(self, name: str) -> bool:
        lowered = str(name).lower()
        if any(token in lowered for token in ["etf", "etn", "스팩", "관리", "경고", "위험"]):
            return True
        # 우선주 계열만 패턴으로 제외: ..., ...우, ...우B, ...1우, ...2우B
        if re.search(r"(우|[12]우B?|우B)$", str(name).strip()):
            return True
        return False

    def collect_candidates(self, market: str, premarket: bool = False) -> list[dict]:
        raw = self.market_data.get_candidates(market)
        result: list[dict] = []
        for item in raw:
            code = str(item.get("code", "")).strip()
            name = str(item.get("name", code)).strip()
            if not code:
                continue
            if self._is_risky_name(name):
                continue
            detail = self.market_data.get_price_detail(code, market, premarket=premarket)
            price = int(float(detail.get("stck_prpr", 0) or 0))
            if price <= 0:
                continue
            change_rate = float(detail.get("prdy_ctrt", item.get("change_rate", 0)) or 0)
            vol_tnrt = float(detail.get("vol_tnrt", 0) or 0)
            acml_vol = float(detail.get("acml_vol", 0) or 0)
            trading_value = price * acml_vol
            if trading_value < 500_000_000:
                continue
            result.append(
                {
                    "code": code,
                    "name": name,
                    "price": price,
                    "change_rate": change_rate,
                    "vol_tnrt": vol_tnrt,
                    "trading_value": trading_value,
                    "detail": detail,
                }
            )
        return result

    def rank(self, market: str, premarket: bool = False) -> list[dict]:
        ranked: list[dict] = []
        for c in self.collect_candidates(market, premarket=premarket):
            price = c["price"]
            stop = int(round(price * (1 - self.settings.stop_loss_rate)))
            target = int(round(price * (1 + self.settings.target_rate_2)))
            risk_per_share = max(1, price - stop)
            reward_per_share = max(1, target - price)
            rr_ratio = reward_per_share / risk_per_share
            breakdown = self.scorer.score(
                change_rate=c["change_rate"],
                vol_tnrt=c["vol_tnrt"],
                trading_value=c["trading_value"],
                vwap_gap=0.2,
                spread_pct=0.3,
                market_score=60,
                rr_ratio=rr_ratio,
                trend_score=65,
                intensity=min(100, c["vol_tnrt"] / 3),
            )
            scored = {
                **c,
                "score": breakdown.total,
                "score_breakdown": breakdown,
                "stop_price": stop,
                "target1_price": int(round(price * (1 + self.settings.target_rate_1))),
                "target2_price": target,
                "rr_ratio": rr_ratio,
            }
            ranked.append(scored)
        ranked.sort(key=lambda x: x["score"], reverse=True)
        return ranked[:50]
