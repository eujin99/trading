from strategy.scoring import ScoreEngine


def test_weighted_score_range():
    engine = ScoreEngine()
    b = engine.score(
        change_rate=5.0,
        vol_tnrt=300.0,
        trading_value=20_000_000_000,
        vwap_gap=0.5,
        spread_pct=0.2,
        market_score=80.0,
        rr_ratio=2.0,
        trend_score=85.0,
        intensity=90.0,
    )
    assert 0 <= b.total <= 100
    assert b.total > 60
