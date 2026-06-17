from __future__ import annotations

from backtest.simulator import run_backtest


def run_walk_forward(rows: list[dict], train_size: int = 200, test_size: int = 100) -> list[dict]:
    results = []
    idx = 0
    while idx + train_size + test_size <= len(rows):
        train = rows[idx : idx + train_size]
        test = rows[idx + train_size : idx + train_size + test_size]
        _ = run_backtest(train)
        out = run_backtest(test)
        results.append(out["metrics"])
        idx += test_size
    return results
