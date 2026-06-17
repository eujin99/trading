from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator


class Database:
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._init_schema()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._lock, self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id TEXT,
                    market TEXT NOT NULL,
                    code TEXT NOT NULL,
                    side TEXT NOT NULL,
                    qty INTEGER NOT NULL,
                    price INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    requested_at TEXT NOT NULL,
                    raw_response TEXT
                );

                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id TEXT,
                    market TEXT NOT NULL,
                    code TEXT NOT NULL,
                    side TEXT NOT NULL,
                    qty INTEGER NOT NULL,
                    fill_price INTEGER NOT NULL,
                    fee INTEGER NOT NULL DEFAULT 0,
                    tax INTEGER NOT NULL DEFAULT 0,
                    slippage INTEGER NOT NULL DEFAULT 0,
                    realized_pnl INTEGER NOT NULL DEFAULT 0,
                    filled_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS positions (
                    code TEXT PRIMARY KEY,
                    market TEXT NOT NULL,
                    name TEXT NOT NULL,
                    qty INTEGER NOT NULL,
                    avg_price INTEGER NOT NULL,
                    stop_price INTEGER NOT NULL,
                    target1_price INTEGER NOT NULL,
                    target2_price INTEGER NOT NULL,
                    trailing_high INTEGER NOT NULL DEFAULT 0,
                    sold_half INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    market TEXT NOT NULL,
                    code TEXT NOT NULL,
                    name TEXT NOT NULL,
                    signal_type TEXT NOT NULL,
                    score REAL NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS risk_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    message TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS daily_pnl (
                    trade_date TEXT PRIMARY KEY,
                    realized_pnl INTEGER NOT NULL DEFAULT 0,
                    unrealized_pnl INTEGER NOT NULL DEFAULT 0,
                    trade_count INTEGER NOT NULL DEFAULT 0,
                    loss_streak INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS system_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    level TEXT NOT NULL,
                    source TEXT NOT NULL,
                    message TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS strategy_params (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS daily_symbol_guard (
                    trade_date TEXT NOT NULL,
                    code TEXT NOT NULL,
                    buy_count INTEGER NOT NULL DEFAULT 0,
                    sell_count INTEGER NOT NULL DEFAULT 0,
                    stopped_out INTEGER NOT NULL DEFAULT 0,
                    last_trade_time TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY (trade_date, code)
                );
                """
            )

    def upsert_position(self, position: dict[str, Any]) -> None:
        now = datetime.now().isoformat()
        with self._lock, self.connect() as conn:
            conn.execute(
                """
                INSERT INTO positions
                (code, market, name, qty, avg_price, stop_price, target1_price, target2_price, trailing_high, sold_half, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(code) DO UPDATE SET
                    market=excluded.market,
                    name=excluded.name,
                    qty=excluded.qty,
                    avg_price=excluded.avg_price,
                    stop_price=excluded.stop_price,
                    target1_price=excluded.target1_price,
                    target2_price=excluded.target2_price,
                    trailing_high=excluded.trailing_high,
                    sold_half=excluded.sold_half,
                    updated_at=excluded.updated_at
                """,
                (
                    position["code"],
                    position["market"],
                    position["name"],
                    int(position["qty"]),
                    int(position["avg_price"]),
                    int(position["stop_price"]),
                    int(position["target1_price"]),
                    int(position["target2_price"]),
                    int(position.get("trailing_high", 0)),
                    int(position.get("sold_half", 0)),
                    now,
                ),
            )

    def delete_position(self, code: str) -> None:
        with self._lock, self.connect() as conn:
            conn.execute("DELETE FROM positions WHERE code = ?", (code,))

    def get_positions(self) -> list[dict[str, Any]]:
        with self._lock, self.connect() as conn:
            rows = conn.execute("SELECT * FROM positions ORDER BY code").fetchall()
        return [dict(r) for r in rows]

    def add_order(self, order: dict[str, Any]) -> int:
        with self._lock, self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO orders(order_id, market, code, side, qty, price, status, requested_at, raw_response)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    order.get("order_id", ""),
                    order["market"],
                    order["code"],
                    order["side"],
                    int(order["qty"]),
                    int(order["price"]),
                    order.get("status", "requested"),
                    order.get("requested_at", datetime.now().isoformat()),
                    json.dumps(order.get("raw_response", {}), ensure_ascii=False),
                ),
            )
            return int(cur.lastrowid)

    def update_order_status(self, order_id: str, status: str, raw_response: dict[str, Any] | None = None) -> None:
        with self._lock, self.connect() as conn:
            conn.execute(
                "UPDATE orders SET status=?, raw_response=? WHERE order_id=?",
                (status, json.dumps(raw_response or {}, ensure_ascii=False), order_id),
            )

    def add_trade(self, trade: dict[str, Any]) -> int:
        with self._lock, self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO trades
                (order_id, market, code, side, qty, fill_price, fee, tax, slippage, realized_pnl, filled_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trade.get("order_id", ""),
                    trade["market"],
                    trade["code"],
                    trade["side"],
                    int(trade["qty"]),
                    int(trade["fill_price"]),
                    int(trade.get("fee", 0)),
                    int(trade.get("tax", 0)),
                    int(trade.get("slippage", 0)),
                    int(trade.get("realized_pnl", 0)),
                    trade.get("filled_at", datetime.now().isoformat()),
                ),
            )
            return int(cur.lastrowid)

    def add_signal(self, market: str, code: str, name: str, signal_type: str, score: float, payload: dict[str, Any]) -> None:
        with self._lock, self.connect() as conn:
            conn.execute(
                """
                INSERT INTO signals(market, code, name, signal_type, score, payload, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    market,
                    code,
                    name,
                    signal_type,
                    float(score),
                    json.dumps(payload, ensure_ascii=False),
                    datetime.now().isoformat(),
                ),
            )

    def add_risk_event(self, event_type: str, severity: str, message: str, payload: dict[str, Any] | None = None) -> None:
        with self._lock, self.connect() as conn:
            conn.execute(
                """
                INSERT INTO risk_events(event_type, severity, message, payload, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    event_type,
                    severity,
                    message,
                    json.dumps(payload or {}, ensure_ascii=False),
                    datetime.now().isoformat(),
                ),
            )

    def get_daily_pnl(self, trade_date: str) -> dict[str, Any]:
        with self._lock, self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM daily_pnl WHERE trade_date=?",
                (trade_date,),
            ).fetchone()
            if row:
                return dict(row)
            now = datetime.now().isoformat()
            conn.execute(
                """
                INSERT INTO daily_pnl(trade_date, realized_pnl, unrealized_pnl, trade_count, loss_streak, updated_at)
                VALUES (?, 0, 0, 0, 0, ?)
                """,
                (trade_date, now),
            )
            return {
                "trade_date": trade_date,
                "realized_pnl": 0,
                "unrealized_pnl": 0,
                "trade_count": 0,
                "loss_streak": 0,
                "updated_at": now,
            }

    def update_daily_pnl(self, trade_date: str, realized_pnl: int, unrealized_pnl: int, trade_count: int, loss_streak: int) -> None:
        with self._lock, self.connect() as conn:
            conn.execute(
                """
                INSERT INTO daily_pnl(trade_date, realized_pnl, unrealized_pnl, trade_count, loss_streak, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(trade_date) DO UPDATE SET
                    realized_pnl=excluded.realized_pnl,
                    unrealized_pnl=excluded.unrealized_pnl,
                    trade_count=excluded.trade_count,
                    loss_streak=excluded.loss_streak,
                    updated_at=excluded.updated_at
                """,
                (
                    trade_date,
                    int(realized_pnl),
                    int(unrealized_pnl),
                    int(trade_count),
                    int(loss_streak),
                    datetime.now().isoformat(),
                ),
            )

    def log(self, level: str, source: str, message: str, payload: dict[str, Any] | None = None) -> None:
        with self._lock, self.connect() as conn:
            conn.execute(
                """
                INSERT INTO system_logs(level, source, message, payload, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    level,
                    source,
                    message,
                    json.dumps(payload or {}, ensure_ascii=False),
                    datetime.now().isoformat(),
                ),
            )

    def set_param(self, key: str, value: str) -> None:
        with self._lock, self.connect() as conn:
            conn.execute(
                """
                INSERT INTO strategy_params(key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
                """,
                (key, value, datetime.now().isoformat()),
            )

    def get_param(self, key: str, default: str = "") -> str:
        with self._lock, self.connect() as conn:
            row = conn.execute("SELECT value FROM strategy_params WHERE key=?", (key,)).fetchone()
        return str(row["value"]) if row else default

    def get_symbol_guard(self, trade_date: str, code: str) -> dict[str, Any]:
        with self._lock, self.connect() as conn:
            row = conn.execute(
                """
                SELECT trade_date, code, buy_count, sell_count, stopped_out, last_trade_time
                FROM daily_symbol_guard
                WHERE trade_date=? AND code=?
                """,
                (trade_date, code),
            ).fetchone()
            if row:
                return dict(row)
            now = datetime.now().isoformat()
            conn.execute(
                """
                INSERT INTO daily_symbol_guard
                (trade_date, code, buy_count, sell_count, stopped_out, last_trade_time)
                VALUES (?, ?, 0, 0, 0, ?)
                """,
                (trade_date, code, now),
            )
            return {
                "trade_date": trade_date,
                "code": code,
                "buy_count": 0,
                "sell_count": 0,
                "stopped_out": 0,
                "last_trade_time": now,
            }

    def update_symbol_guard(
        self,
        trade_date: str,
        code: str,
        buy_count: int,
        sell_count: int,
        stopped_out: int,
        last_trade_time: str | None = None,
    ) -> None:
        updated = last_trade_time or datetime.now().isoformat()
        with self._lock, self.connect() as conn:
            conn.execute(
                """
                INSERT INTO daily_symbol_guard
                (trade_date, code, buy_count, sell_count, stopped_out, last_trade_time)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(trade_date, code) DO UPDATE SET
                    buy_count=excluded.buy_count,
                    sell_count=excluded.sell_count,
                    stopped_out=excluded.stopped_out,
                    last_trade_time=excluded.last_trade_time
                """,
                (
                    trade_date,
                    code,
                    int(buy_count),
                    int(sell_count),
                    int(stopped_out),
                    updated,
                ),
            )
