from .base import Settings


def apply_us_overrides(settings: Settings) -> Settings:
    settings.default_market = "US"
    settings.market_open = "22:30"
    settings.force_sell_time = "05:50"
    return settings
