from __future__ import annotations

import math


def _max_drawdown(equity_curve: list[float]) -> float:
    if not equity_curve:
        return 0.0
    peak = equity_curve[0]
    max_dd = 0.0
    for v in equity_curve:
        peak = max(peak, v)
        if peak > 0:
            dd = (peak - v) / peak
            max_dd = max(max_dd, dd)
    return max_dd


def summarize_metrics(equity_curve: list[float], trades: list[dict]) -> dict:
    realized = [t["pnl"] for t in trades if t["side"] == "sell"]
    wins = [p for p in realized if p > 0]
    losses = [p for p in realized if p <= 0]
    win_rate = len(wins) / len(realized) if realized else 0.0
    avg_win = sum(wins) / len(wins) if wins else 0.0
    avg_loss = abs(sum(losses) / len(losses)) if losses else 0.0
    payoff = (avg_win / avg_loss) if avg_loss > 0 else 0.0
    expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
    rets = []
    for prev, cur in zip(equity_curve[:-1], equity_curve[1:]):
        if prev > 0:
            rets.append((cur - prev) / prev)
    mean = sum(rets) / len(rets) if rets else 0.0
    std = math.sqrt(sum((x - mean) ** 2 for x in rets) / len(rets)) if rets else 0.0
    sharpe = (mean / std * math.sqrt(252)) if std > 0 else 0.0
    return {
        "trade_count": len(realized),
        "win_rate": win_rate,
        "payoff_ratio": payoff,
        "expectancy": expectancy,
        "mdd": _max_drawdown(equity_curve),
        "sharpe": sharpe,
        "net_profit": sum(realized),
    }
