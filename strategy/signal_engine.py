from __future__ import annotations

from config import Settings
from storage import Database
from strategy import Screener


class SignalEngine:
    def __init__(self, settings: Settings, db: Database, screener: Screener):
        self.settings = settings
        self.db = db
        self.screener = screener

    def generate_buy_signals(self, market: str, premarket: bool = False) -> list[dict]:
        ranked = self.screener.rank(market, premarket=premarket)
        approved = []
        for row in ranked:
            if row["score"] < self.settings.score_threshold:
                continue
            self.db.add_signal(
                market=market,
                code=row["code"],
                name=row["name"],
                signal_type="buy_candidate",
                score=row["score"],
                payload=row,
            )
            approved.append(row)
            if len(approved) >= self.settings.max_stocks:
                break
        return approved
