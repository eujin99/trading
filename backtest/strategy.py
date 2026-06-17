from __future__ import annotations


def momentum_signal(rows: list[dict], i: int, lookback: int = 5) -> dict:
    if i < lookback:
        return {"buy": False, "sell": False}
    window = rows[i - lookback : i]
    up_cnt = 0
    for prev, cur in zip(window[:-1], window[1:]):
        if cur["close"] > prev["close"]:
            up_cnt += 1
    trend = up_cnt / max(1, lookback - 1)
    buy = trend >= 0.75
    sell = trend <= 0.25
    return {"buy": buy, "sell": sell}
