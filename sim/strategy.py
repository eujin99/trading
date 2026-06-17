import datetime


def _parse_hhmm(value: str, fallback: str) -> datetime.time:
    raw = str(value or "").strip() or fallback
    try:
        hh, mm = raw.split(":", 1)
        return datetime.time(hour=int(hh), minute=int(mm))
    except Exception:
        hh, mm = fallback.split(":", 1)
        return datetime.time(hour=int(hh), minute=int(mm))


def evaluate_candidate(ctx: dict) -> dict:
    """
    모의투자 전용 급등주 필터.
    실험 중심: 공격적인 기준 + 점심 시간대 자동 완화.
    """
    market = str(ctx.get("market", "KR"))
    if market != "KR":
        return {"accept": True}

    name_lower = str(ctx.get("name_lower", "")).lower()
    change_rate = float(ctx.get("change_rate", 0.0))
    vol_tnrt = float(ctx.get("vol_tnrt", 0.0))
    price = int(ctx.get("price", 0))
    acml_vol = int(ctx.get("acml_vol", 0))
    allow_keyword_relax = bool(ctx.get("allow_keyword_relax", False))
    defaults = ctx.get("defaults", {})

    exclude_keywords = [str(x).lower() for x in defaults.get("SCREENING_EXCLUDE_KEYWORDS", [])]
    if (not allow_keyword_relax) and any(token in name_lower for token in exclude_keywords):
        return {"accept": False}

    # 모투 실험은 공격형 기준을 기본값으로 두되, 점심에는 자동 완화
    relax = float(ctx.get("aggressive_relax_factor", 1.0))
    now = datetime.datetime.now()
    lunch_start = _parse_hhmm("11:20", "11:20")
    lunch_end = _parse_hhmm("13:10", "13:10")
    if now.weekday() < 5 and lunch_start <= now.time() <= lunch_end:
        relax = min(relax, 0.65)

    min_change = max(0.4, float(defaults.get("SCREENING_MIN_CHANGE_RATE", 1.2)) * relax)
    min_vol = max(60.0, float(defaults.get("SCREENING_MIN_VOL_TNRT", 130.0)) * relax)
    min_value = int(max(100000000, int(defaults.get("SCREENING_MIN_TRADING_VALUE", 800000000)) * relax))

    if change_rate < max(float(defaults.get("CHANGE_RATE_MIN", 1.0)), min_change):
        return {"accept": False}
    if vol_tnrt < max(float(defaults.get("VOLUME_RATIO_MIN", 1.5)) * 100, min_vol):
        return {"accept": False}
    if int(price * max(0, acml_vol)) < min_value:
        return {"accept": False}
    return {"accept": True}
