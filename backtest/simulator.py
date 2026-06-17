from __future__ import annotations

from backtest.metrics import summarize_metrics
from backtest.strategy import momentum_signal


def run_backtest(
    rows: list[dict],
    fee_rate: float = 0.00015,
    tax_rate: float = 0.0018,
    slippage_rate: float = 0.0005,
) -> dict:
    cash = 10_000_000.0
    qty = 0.0
    entry = 0.0
    equity_curve = []
    trades = []

    for i, row in enumerate(rows):
        price = float(row["close"])
        signal = momentum_signal(rows, i)
        if qty == 0 and signal["buy"] and price > 0:
            fill = price * (1 + slippage_rate)
            qty = cash // fill
            if qty <= 0:
                equity_curve.append(cash)
                continue
            gross = qty * fill
            fee = gross * fee_rate
            cash -= gross + fee
            entry = fill
            trades.append({"side": "buy", "price": fill, "qty": qty, "fee": fee, "tax": 0.0, "pnl": 0.0})
        elif qty > 0 and signal["sell"]:
            fill = price * (1 - slippage_rate)
            gross = qty * fill
            fee = gross * fee_rate
            tax = gross * tax_rate
            pnl = (fill - entry) * qty - fee - tax
            cash += gross - fee - tax
            trades.append({"side": "sell", "price": fill, "qty": qty, "fee": fee, "tax": tax, "pnl": pnl})
            qty = 0
            entry = 0
        equity = cash + qty * price
        equity_curve.append(equity)

    if qty > 0:
        price = float(rows[-1]["close"])
        fill = price * (1 - slippage_rate)
        gross = qty * fill
        fee = gross * fee_rate
        tax = gross * tax_rate
        pnl = (fill - entry) * qty - fee - tax
        cash += gross - fee - tax
        trades.append({"side": "sell", "price": fill, "qty": qty, "fee": fee, "tax": tax, "pnl": pnl})
        equity_curve[-1] = cash

    metrics = summarize_metrics(equity_curve, trades)
    return {"equity_curve": equity_curve, "trades": trades, "metrics": metrics}
