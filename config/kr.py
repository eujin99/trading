from .base import Settings


def apply_kr_overrides(settings: Settings) -> Settings:
    settings.default_market = "KR"
    settings.market_open = "09:00"
    settings.force_sell_time = "15:30"
    return settings
