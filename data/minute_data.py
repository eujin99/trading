from __future__ import annotations


class MinuteDataService:
    @staticmethod
    def trend_score(candles: list[dict]) -> float:
        if len(candles) < 2:
            return 0.0
        ups = 0
        for prev, cur in zip(candles[:-1], candles[1:]):
            if float(cur.get("close", 0)) > float(prev.get("close", 0)):
                ups += 1
        return ups / max(1, len(candles) - 1) * 100

    @staticmethod
    def vwap(candles: list[dict]) -> float:
        pv = 0.0
        vv = 0.0
        for c in candles:
            p = float(c.get("close", 0))
            v = float(c.get("volume", 0))
            pv += p * v
            vv += v
        return pv / vv if vv > 0 else 0.0

    @staticmethod
    def atr(candles: list[dict], period: int = 14) -> float:
        if len(candles) < 2:
            return 0.0
        trs = []
        for i in range(1, len(candles)):
            h = float(candles[i].get("high", candles[i].get("close", 0)))
            l = float(candles[i].get("low", candles[i].get("close", 0)))
            pc = float(candles[i - 1].get("close", 0))
            tr = max(h - l, abs(h - pc), abs(l - pc))
            trs.append(tr)
        window = trs[-period:] if len(trs) >= period else trs
        return sum(window) / len(window) if window else 0.0
