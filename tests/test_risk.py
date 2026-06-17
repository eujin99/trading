from risk import CircuitBreaker, RiskManager
from storage import Database
from config.base import Settings


def _settings() -> Settings:
    return Settings(
        app_key="a",
        app_secret="b",
        account_no="00000000-01",
        is_virtual=True,
        base_url="http://example.com",
    )


def test_circuit_breaker_pauses_after_limit(tmp_path):
    db = Database(str(tmp_path / "risk.db"))
    s = _settings()
    br = CircuitBreaker(api_error_limit=1, order_fail_limit=2)
    rm = RiskManager(s, db, br)
    br.record_api_error("x")
    ok, _ = br.can_open_new_position()
    assert not ok
    rm.register_resume()
    ok2, _ = br.can_open_new_position()
    assert ok2


def test_daily_trade_limit_blocks(tmp_path):
    db = Database(str(tmp_path / "risk2.db"))
    s = _settings()
    s.max_daily_trades = 1
    br = CircuitBreaker(api_error_limit=3, order_fail_limit=2)
    rm = RiskManager(s, db, br)
    rm.register_trade_result(1000)
    dec = rm.approve_buy("005930", 1000, 10_000_000, 1_000_000, 9_000_000, 0)
    assert not dec.approved
