from backtest.simulator import run_backtest


def test_backtest_runs():
    rows = []
    price = 100.0
    for i in range(120):
        price += 1 if i % 3 else -0.2
        rows.append({"ts": str(i), "open": price - 0.5, "high": price + 0.5, "low": price - 1, "close": price, "volume": 1000 + i})
    result = run_backtest(rows)
    assert "metrics" in result
    assert "trade_count" in result["metrics"]
