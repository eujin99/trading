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

    @staticmethod
    def _to_int(value, default: int = 0) -> int:
        try:
            return int(float(str(value).replace(",", "").strip()))
        except Exception:
            return default

    @staticmethod
    def _to_float(value, default: float = 0.0) -> float:
        try:
            return float(str(value).replace(",", "").strip())
        except Exception:
            return default

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
            price = self._to_int(detail.get("stck_prpr", 0))
            if price <= 0:
                continue
            change_rate = self._to_float(detail.get("prdy_ctrt", item.get("change_rate", 0)))
            vol_tnrt = self._to_float(detail.get("vol_tnrt", 0))
            acml_vol = self._to_float(detail.get("acml_vol", 0))
            trading_value = price * acml_vol
            if trading_value < 500_000_000:
                continue

            bid1 = self._to_int(detail.get("bidp1", detail.get("stck_bdp1", 0)))
            ask1 = self._to_int(detail.get("askp1", detail.get("stck_askp1", 0)))
            aspr_unit = self._to_int(detail.get("aspr_unit", 0))
            if bid1 > 0 and ask1 > 0 and ask1 >= bid1:
                spread_pct = ((ask1 - bid1) / max(1, price)) * 100.0
            elif aspr_unit > 0:
                spread_pct = (aspr_unit / max(1, price)) * 100.0
            else:
                spread_pct = 0.2
            if spread_pct > self.settings.max_spread_pct:
                continue

            open_price = self._to_int(detail.get("stck_oprc", price), price)
            high_price = self._to_int(detail.get("stck_hgpr", price), price)
            low_price = self._to_int(detail.get("stck_lwpr", price), price)
            day_range = max(1, high_price - low_price)
            range_pos = ((price - low_price) / day_range) * 100.0
            trend_score = max(0.0, min(100.0, range_pos if price >= open_price else range_pos * 0.6))
            if trend_score < self.settings.min_trend_score:
                continue

            vwap_price = self._to_float(detail.get("wghn_avrg_stck_prc", 0.0), 0.0)
            if vwap_price <= 0:
                vwap_price = float(open_price)
            vwap_gap = (price - vwap_price) / max(1.0, vwap_price)
            if self.settings.require_price_above_vwap and vwap_gap < 0:
                continue

            prev_close = price / max(0.01, (1.0 + (change_rate / 100.0)))
            gap_up_pct = ((open_price - prev_close) / max(1.0, prev_close)) * 100.0
            if gap_up_pct > self.settings.max_gap_up_pct:
                continue

            result.append(
                {
                    "code": code,
                    "name": name,
                    "price": price,
                    "change_rate": change_rate,
                    "vol_tnrt": vol_tnrt,
                    "trading_value": trading_value,
                    "spread_pct": spread_pct,
                    "trend_score": trend_score,
                    "vwap_gap": vwap_gap,
                    "market_score": 60.0,
                    "detail": detail,
                }
            )
        return result

    def rank(self, market: str, premarket: bool = False) -> list[dict]:
        ranked: list[dict] = []
        candidates = self.collect_candidates(market, premarket=premarket)
        if not candidates:
            return ranked

        # 시장점수(브레드스/평균 상승률 기반) 동적 계산
        avg_change = sum(float(c.get("change_rate", 0.0)) for c in candidates) / max(1, len(candidates))
        positive_ratio = sum(1 for c in candidates if float(c.get("change_rate", 0.0)) > 0) / max(1, len(candidates))
        base_market_score = max(0.0, min(100.0, 45.0 + avg_change * 3.0 + positive_ratio * 35.0))

        for c in candidates:
            own_change = float(c.get("change_rate", 0.0))
            market_score = max(0.0, min(100.0, base_market_score + own_change * 1.2))
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
                vwap_gap=c.get("vwap_gap", 0.0),
                spread_pct=c.get("spread_pct", 0.3),
                market_score=market_score,
                rr_ratio=rr_ratio,
                trend_score=c.get("trend_score", 65),
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
