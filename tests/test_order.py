from portfolio.position_store import PositionStore
from portfolio.portfolio_service import PortfolioService
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


def test_position_upsert_and_reduce(tmp_path):
    db = Database(str(tmp_path / "orders.db"))
    store = PositionStore(db)
    service = PortfolioService(_settings(), store)
    service.upsert_position("005930", "삼성전자", 10, 70000, "KR")
    pos = service.get_position("005930")
    assert pos is not None
    service.reduce_position("005930", 4)
    pos2 = service.get_position("005930")
    assert int(pos2["qty"]) == 6
