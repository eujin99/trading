from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ScoreBreakdown:
    volume: float
    momentum: float
    trend: float
    vwap: float
    intensity: float
    spread: float
    market: float
    risk_reward: float

    @property
    def total(self) -> float:
        return (
            self.volume * 0.20
            + self.momentum * 0.15
            + self.trend * 0.20
            + self.vwap * 0.15
            + self.intensity * 0.10
            + self.spread * 0.10
            + self.market * 0.05
            + self.risk_reward * 0.05
        )


class ScoreEngine:
    @staticmethod
    def _cap(value: float) -> float:
        return max(0.0, min(100.0, float(value)))

    def score(self, *, change_rate: float, vol_tnrt: float, trading_value: float, vwap_gap: float, spread_pct: float, market_score: float, rr_ratio: float, trend_score: float, intensity: float) -> ScoreBreakdown:
        volume_score = self._cap((trading_value / 10_000_000_000) * 100 + (vol_tnrt / 300) * 40)
        momentum_score = self._cap((change_rate + 5) * 8)
        vwap_score = self._cap(50 + vwap_gap * 40)
        spread_score = self._cap(100 - spread_pct * 200)
        rr_score = self._cap(rr_ratio * 40)
        return ScoreBreakdown(
            volume=self._cap(volume_score),
            momentum=self._cap(momentum_score),
            trend=self._cap(trend_score),
            vwap=self._cap(vwap_score),
            intensity=self._cap(intensity),
            spread=self._cap(spread_score),
            market=self._cap(market_score),
            risk_reward=self._cap(rr_score),
        )
