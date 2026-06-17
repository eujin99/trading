from __future__ import annotations

import csv
from pathlib import Path


def load_ohlcv_csv(path: str) -> list[dict]:
    file_path = Path(path)
    rows: list[dict] = []
    with file_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(
                {
                    "ts": row.get("ts", ""),
                    "open": float(row.get("open", 0) or 0),
                    "high": float(row.get("high", 0) or 0),
                    "low": float(row.get("low", 0) or 0),
                    "close": float(row.get("close", 0) or 0),
                    "volume": float(row.get("volume", 0) or 0),
                }
            )
    return rows
