# ============================================================
# autotrader.py — 급등주 자동매매 메인 봇 (v2 위임 래퍼)
# ============================================================
# 기본 실행은 새 오케스트레이터(app.py)로 위임합니다.
# 기존 코드 블록은 하위호환 참조를 위해 파일 내에 남겨둡니다.
# ------------------------------------------------------------
if __name__ == "__main__":
    import os
    import pathlib
    import subprocess
    import sys

    root = pathlib.Path(__file__).resolve().parents[1]
    cmd = [sys.executable, str(root / "app.py"), "--config-module", os.getenv("TRADER_CONFIG_MODULE", "config")]
    raise SystemExit(subprocess.call(cmd, cwd=str(root)))

import time
import datetime
import sys
import os
import importlib
import importlib.util
import threading
import json

import kis_api as api
CFG_MODULE = os.getenv("TRADER_CONFIG_MODULE", "config")
cfg = importlib.import_module(CFG_MODULE)
CURRENT_CFG_MODULE = CFG_MODULE
STARTUP_CFG_MODULE = CFG_MODULE

MAX_STOCKS = 3
BUY_PCT = 0.15
BUY_MIN_AMOUNT = 300000
BUY_MAX_AMOUNT = 1500000
MIN_CASH_RATIO = 0.30
ADD_ON_ENABLED = True
ADD_ON_MIN_SCORE = 38
ADD_ON_MAX_PER_STOCK = 2
ADD_ON_COOLDOWN_SEC = 600
ADD_ON_MIN_PROFIT_RATE = -1.5
ADD_ON_MAX_CHASE_RATE = 6.0
ADD_ON_MIN_MOMENTUM_RATE = 0.3
ADD_ON_BUY_PCT_MULTIPLIER = 0.7
TARGET_RATE_1 = 0.05
TARGET_RATE_2 = 0.10
STOP_LOSS_RATE = 0.03
POST_DCA_STOP_LOSS_RATE = 0.02
DCA_MIN_VOL_TNRT = 120.0
DCA_MIN_CHANGE_RATE = -5.0
STOP_BREACH_CONFIRM_COUNT = 2
VOLUME_RATIO_MIN = 1.5
CHANGE_RATE_MIN = 1.0
CHANGE_RATE_MAX = 25.0
SCORE_THRESHOLD = 32
DEFAULT_MARKET = "KR"
SELL_ON_INTERRUPT = False
IS_VIRTUAL = True
TELEGRAM_NOTIFY_ENABLED = True
TELEGRAM_NOTIFY_INTERVAL_SEC = 180
TELEGRAM_BOT_TOKEN = ""
TELEGRAM_CHAT_ID = ""
MARKET_OPEN = "09:00"
FORCE_SELL_TIME = "15:20"
PREMARKET_START = "08:00"
AUTO_SCREEN_INTERVAL_SEC = 30
PORTFOLIO_SCORE_INTERVAL_SEC = 3
PRICE_CACHE_TTL_SEC = 2
SCREENING_CANDIDATE_LIMIT = 12
SCREENING_STEP_SLEEP_SEC = 0.02
SCREENING_RESULT_COUNT = 20
DISPLAY_SCORE_THRESHOLD = 30
AGGRESSIVE_SCREENING = True
SCREENING_MIN_CHANGE_RATE = 2.0
SCREENING_MIN_VOL_TNRT = 180.0
SCREENING_MIN_TRADING_VALUE = 3000000000
SCREENING_RELAX_ENABLED = False
SCREENING_EXCLUDE_KEYWORDS = [
    "etf", "etn", "채권", "국채", "회사채", "혼합",
    "인덱스", "kodex", "tiger", "rise", "ace", "sol", "arirang",
]
SCREENING_LUNCH_RELAX_ENABLED = True
SCREENING_LUNCH_START = "11:20"
SCREENING_LUNCH_END = "13:10"
SCREENING_LUNCH_RELAX_FACTOR = 0.65
SCREENING_EMERGENCY_RELAX_FACTOR = 0.55
SCREENING_ALLOW_KEYWORD_RELAX_IF_EMPTY = True


def apply_runtime_config(module_name: str):
    """설정 모듈을 런타임에 적용하고 API 모듈을 동기화"""
    global cfg, MAX_STOCKS, BUY_PCT, BUY_MIN_AMOUNT, BUY_MAX_AMOUNT
    global MIN_CASH_RATIO, TARGET_RATE_1, TARGET_RATE_2, STOP_LOSS_RATE
    global POST_DCA_STOP_LOSS_RATE, DCA_MIN_VOL_TNRT, DCA_MIN_CHANGE_RATE
    global STOP_BREACH_CONFIRM_COUNT, VOLUME_RATIO_MIN, CHANGE_RATE_MIN
    global CHANGE_RATE_MAX, SCORE_THRESHOLD, DEFAULT_MARKET, SELL_ON_INTERRUPT, IS_VIRTUAL
    global TELEGRAM_NOTIFY_ENABLED, TELEGRAM_NOTIFY_INTERVAL_SEC
    global TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, MARKET_OPEN, FORCE_SELL_TIME, PREMARKET_START
    global AUTO_SCREEN_INTERVAL_SEC, PORTFOLIO_SCORE_INTERVAL_SEC
    global PRICE_CACHE_TTL_SEC, SCREENING_CANDIDATE_LIMIT, SCREENING_STEP_SLEEP_SEC, SCREENING_RESULT_COUNT
    global DISPLAY_SCORE_THRESHOLD
    global ADD_ON_ENABLED, ADD_ON_MIN_SCORE, ADD_ON_MAX_PER_STOCK, ADD_ON_COOLDOWN_SEC
    global ADD_ON_MIN_PROFIT_RATE, ADD_ON_MAX_CHASE_RATE, ADD_ON_MIN_MOMENTUM_RATE, ADD_ON_BUY_PCT_MULTIPLIER
    global AGGRESSIVE_SCREENING, SCREENING_MIN_CHANGE_RATE, SCREENING_MIN_VOL_TNRT
    global SCREENING_MIN_TRADING_VALUE, SCREENING_RELAX_ENABLED, SCREENING_EXCLUDE_KEYWORDS
    global SCREENING_LUNCH_RELAX_ENABLED, SCREENING_LUNCH_START, SCREENING_LUNCH_END
    global SCREENING_LUNCH_RELAX_FACTOR, SCREENING_EMERGENCY_RELAX_FACTOR
    global SCREENING_ALLOW_KEYWORD_RELAX_IF_EMPTY
    global api, CURRENT_CFG_MODULE, _daily_realized_loaded, _daily_trade_guard_loaded, _price_cache

    os.environ["TRADER_CONFIG_MODULE"] = module_name
    cfg = importlib.reload(importlib.import_module(module_name))
    api = importlib.reload(api)
    CURRENT_CFG_MODULE = module_name
    _daily_realized_loaded = False
    _daily_trade_guard_loaded = False
    _price_cache = {}

    MAX_STOCKS = getattr(cfg, "MAX_STOCKS", 3)
    BUY_PCT = getattr(cfg, "BUY_PCT", 0.15)
    BUY_MIN_AMOUNT = getattr(cfg, "BUY_MIN_AMOUNT", 300000)
    BUY_MAX_AMOUNT = getattr(cfg, "BUY_MAX_AMOUNT", 1500000)
    MIN_CASH_RATIO = getattr(cfg, "MIN_CASH_RATIO", 0.30)
    ADD_ON_ENABLED = getattr(cfg, "ADD_ON_ENABLED", True)
    ADD_ON_MIN_SCORE = getattr(cfg, "ADD_ON_MIN_SCORE", 38)
    ADD_ON_MAX_PER_STOCK = getattr(cfg, "ADD_ON_MAX_PER_STOCK", 2)
    ADD_ON_COOLDOWN_SEC = getattr(cfg, "ADD_ON_COOLDOWN_SEC", 600)
    ADD_ON_MIN_PROFIT_RATE = getattr(cfg, "ADD_ON_MIN_PROFIT_RATE", -1.5)
    ADD_ON_MAX_CHASE_RATE = getattr(cfg, "ADD_ON_MAX_CHASE_RATE", 6.0)
    ADD_ON_MIN_MOMENTUM_RATE = getattr(cfg, "ADD_ON_MIN_MOMENTUM_RATE", 0.3)
    ADD_ON_BUY_PCT_MULTIPLIER = getattr(cfg, "ADD_ON_BUY_PCT_MULTIPLIER", 0.7)
    TARGET_RATE_1 = getattr(cfg, "TARGET_RATE_1", 0.05)
    TARGET_RATE_2 = getattr(cfg, "TARGET_RATE_2", 0.10)
    STOP_LOSS_RATE = getattr(cfg, "STOP_LOSS_RATE", 0.03)
    POST_DCA_STOP_LOSS_RATE = getattr(cfg, "POST_DCA_STOP_LOSS_RATE", 0.02)
    DCA_MIN_VOL_TNRT = getattr(cfg, "DCA_MIN_VOL_TNRT", 120.0)
    DCA_MIN_CHANGE_RATE = getattr(cfg, "DCA_MIN_CHANGE_RATE", -5.0)
    STOP_BREACH_CONFIRM_COUNT = getattr(cfg, "STOP_BREACH_CONFIRM_COUNT", 2)
    VOLUME_RATIO_MIN = getattr(cfg, "VOLUME_RATIO_MIN", 1.5)
    CHANGE_RATE_MIN = getattr(cfg, "CHANGE_RATE_MIN", 1.0)
    CHANGE_RATE_MAX = getattr(cfg, "CHANGE_RATE_MAX", 25.0)
    SCORE_THRESHOLD = getattr(cfg, "SCORE_THRESHOLD", 32)
    DEFAULT_MARKET = getattr(cfg, "DEFAULT_MARKET", "KR")
    SELL_ON_INTERRUPT = getattr(cfg, "SELL_ON_INTERRUPT", False)
    IS_VIRTUAL = getattr(cfg, "IS_VIRTUAL", True)
    TELEGRAM_NOTIFY_ENABLED = getattr(cfg, "TELEGRAM_NOTIFY_ENABLED", True)
    TELEGRAM_NOTIFY_INTERVAL_SEC = getattr(cfg, "TELEGRAM_NOTIFY_INTERVAL_SEC", 180)
    TELEGRAM_BOT_TOKEN = str(getattr(cfg, "TELEGRAM_BOT_TOKEN", "")).strip()
    TELEGRAM_CHAT_ID = str(getattr(cfg, "TELEGRAM_CHAT_ID", "")).strip()
    MARKET_OPEN = str(getattr(cfg, "MARKET_OPEN", "09:00")).strip()
    FORCE_SELL_TIME = str(getattr(cfg, "FORCE_SELL_TIME", "15:20")).strip()
    PREMARKET_START = str(getattr(cfg, "PREMARKET_START", "08:00")).strip()
    AUTO_SCREEN_INTERVAL_SEC = int(getattr(cfg, "AUTO_SCREEN_INTERVAL_SEC", 30))
    PORTFOLIO_SCORE_INTERVAL_SEC = max(3, int(getattr(cfg, "PORTFOLIO_SCORE_INTERVAL_SEC", 3)))
    PRICE_CACHE_TTL_SEC = max(0, int(getattr(cfg, "PRICE_CACHE_TTL_SEC", 2)))
    SCREENING_CANDIDATE_LIMIT = max(1, int(getattr(cfg, "SCREENING_CANDIDATE_LIMIT", 12)))
    SCREENING_STEP_SLEEP_SEC = max(0.0, float(getattr(cfg, "SCREENING_STEP_SLEEP_SEC", 0.02)))
    SCREENING_RESULT_COUNT = max(1, int(getattr(cfg, "SCREENING_RESULT_COUNT", 20)))
    DISPLAY_SCORE_THRESHOLD = max(1, int(getattr(cfg, "DISPLAY_SCORE_THRESHOLD", 30)))
    AGGRESSIVE_SCREENING = bool(getattr(cfg, "AGGRESSIVE_SCREENING", True))
    SCREENING_MIN_CHANGE_RATE = float(getattr(cfg, "SCREENING_MIN_CHANGE_RATE", 2.0))
    SCREENING_MIN_VOL_TNRT = float(getattr(cfg, "SCREENING_MIN_VOL_TNRT", 180.0))
    SCREENING_MIN_TRADING_VALUE = int(getattr(cfg, "SCREENING_MIN_TRADING_VALUE", 3000000000))
    SCREENING_RELAX_ENABLED = bool(getattr(cfg, "SCREENING_RELAX_ENABLED", False))
    SCREENING_EXCLUDE_KEYWORDS = [
        str(x).strip().lower()
        for x in getattr(
            cfg,
            "SCREENING_EXCLUDE_KEYWORDS",
            ["etf", "etn", "채권", "국채", "회사채", "혼합", "인덱스", "kodex", "tiger", "rise", "ace", "sol", "arirang"],
        )
        if str(x).strip()
    ]
    SCREENING_LUNCH_RELAX_ENABLED = bool(getattr(cfg, "SCREENING_LUNCH_RELAX_ENABLED", True))
    SCREENING_LUNCH_START = str(getattr(cfg, "SCREENING_LUNCH_START", "11:20")).strip()
    SCREENING_LUNCH_END = str(getattr(cfg, "SCREENING_LUNCH_END", "13:10")).strip()
    SCREENING_LUNCH_RELAX_FACTOR = float(getattr(cfg, "SCREENING_LUNCH_RELAX_FACTOR", 0.65))
    SCREENING_EMERGENCY_RELAX_FACTOR = float(getattr(cfg, "SCREENING_EMERGENCY_RELAX_FACTOR", 0.55))
    SCREENING_ALLOW_KEYWORD_RELAX_IF_EMPTY = bool(getattr(cfg, "SCREENING_ALLOW_KEYWORD_RELAX_IF_EMPTY", True))


apply_runtime_config(CFG_MODULE)

# ── 보유 종목 상태 저장소 ──────────────────────────────────
# { "종목코드": { name, qty, avg_price, target1, target2, stop,
#                sold_half, entry_time, hold_until } }
portfolio = {}
last_screened = []
current_market = DEFAULT_MARKET if DEFAULT_MARKET in ("KR", "US") else "KR"
_tg_last_notified_at = 0.0
_tg_last_close_message_date = ""
_tg_update_offset = 0
_tg_updates_bootstrapped = False
_tg_sell_sessions = {}
_tg_commands_registered = False
_daily_realized_date = datetime.date.today().strftime("%Y-%m-%d")
_daily_realized_pnl = 0
_daily_realized_loaded = False
_REALIZED_PNL_STATE_FILE = os.path.join(os.path.dirname(__file__), ".realized_pnl_state.json")
_last_realized_sync_ts = 0.0
_daily_trade_guard_date = datetime.date.today().strftime("%Y-%m-%d")
_daily_trade_guard_loaded = False
_daily_bought_codes = set()
_daily_sold_codes = set()
_DAILY_TRADE_GUARD_STATE_FILE = os.path.join(os.path.dirname(__file__), ".daily_trade_guard_state.json")
_price_cache = {}
_price_cache_lock = threading.Lock()


# ── 유틸 ──────────────────────────────────────────────────

def now_str() -> str:
    return datetime.datetime.now().strftime("%H:%M:%S")


def log(msg: str):
    print(f"[{now_str()}] {msg}")


def _get_price_detail_cached(code: str, market: str, ttl_sec: float = None, force: bool = False) -> dict:
    ttl = float(PRICE_CACHE_TTL_SEC if ttl_sec is None else ttl_sec)
    key = f"{market}:{code}"
    now_ts = time.time()

    if not force and ttl > 0:
        with _price_cache_lock:
            cached = _price_cache.get(key)
        if cached:
            cached_ts, payload = cached
            if (now_ts - cached_ts) <= ttl and isinstance(payload, dict):
                return payload

    detail = api.get_current_price_by_market(code, market) or {}
    with _price_cache_lock:
        _price_cache[key] = (now_ts, detail)
    return detail


def _parse_hhmm_to_time(value: str, fallback: str) -> datetime.time:
    raw = str(value or "").strip()
    for candidate in (raw, fallback):
        try:
            hh, mm = candidate.split(":", 1)
            return datetime.time(hour=int(hh), minute=int(mm))
        except Exception:
            continue
    return datetime.time(hour=9, minute=0)


def _market_open_close_times() -> tuple[datetime.time, datetime.time]:
    open_t = _parse_hhmm_to_time(MARKET_OPEN, "09:00")
    close_t = _parse_hhmm_to_time(FORCE_SELL_TIME, "15:20")
    return open_t, close_t


def _is_kr_market_open(now_dt: datetime.datetime = None) -> bool:
    now_dt = now_dt or datetime.datetime.now()
    if now_dt.weekday() >= 5:
        return False
    open_t, close_t = _market_open_close_times()
    now_t = now_dt.time()
    return open_t <= now_t < close_t


def _is_kr_premarket_observe_time(now_dt: datetime.datetime = None) -> bool:
    now_dt = now_dt or datetime.datetime.now()
    if now_dt.weekday() >= 5:
        return False
    pre_t = _parse_hhmm_to_time(PREMARKET_START, "08:00")
    open_t, _ = _market_open_close_times()
    now_t = now_dt.time()
    return pre_t <= now_t < open_t


def _profit_icon(rate: float) -> str:
    if rate > 0:
        return "📈"
    if rate < 0:
        return "📉"
    return "➖"


def _send_telegram_message(text: str):
    if not TELEGRAM_NOTIFY_ENABLED or not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests_payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "disable_web_page_preview": True,
        }
        import requests
        requests.post(url, json=requests_payload, timeout=10)
    except Exception:
        pass


def _send_telegram_message_to(chat_id: str, text: str):
    if not TELEGRAM_NOTIFY_ENABLED or not TELEGRAM_BOT_TOKEN:
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests_payload = {
            "chat_id": str(chat_id),
            "text": text,
            "disable_web_page_preview": True,
        }
        import requests
        requests.post(url, json=requests_payload, timeout=10)
    except Exception:
        pass


def _send_target_recommendation(level: str, name: str, code: str, cur_price: int, target_price: int):
    if level == "1차":
        title = "1차 목표입니다. 매도 권장 알림입니다."
    else:
        title = "2차 목표입니다. 매도 권장 알림입니다."
    message = (
        f"🔔 목표 도달 알림\n"
        f"시장: {market_label(current_market)}\n"
        f"종목: {name}({code})\n"
        f"{title}\n"
        f"현재가: {cur_price:,}원 / 목표가: {target_price:,}원"
    )
    _send_telegram_message(message)


def _send_stop_recommendation(name: str, code: str, qty: int, cur_price: int, stop_price: int):
    message = (
        "🔔 손절 권장 알림\n"
        f"종목: {name}({code})\n"
        f"{qty}주 손절 권장 알림입니다.\n"
        f"(현재가 : {cur_price:,}원 / 손절가 : {stop_price:,}원)\n"
        "/매도 를 입력해 매도 하십시오."
    )
    _send_telegram_message(message)


def _realized_state_key() -> str:
    account_no = str(getattr(cfg, "ACCOUNT_NO", "")).strip() or "UNKNOWN"
    return f"{CURRENT_CFG_MODULE}::{account_no}"


def _load_realized_pnl_state():
    global _daily_realized_date, _daily_realized_pnl, _daily_realized_loaded
    today = datetime.date.today().strftime("%Y-%m-%d")
    key = _realized_state_key()
    _daily_realized_date = today
    _daily_realized_pnl = 0

    try:
        if not os.path.exists(_REALIZED_PNL_STATE_FILE):
            _daily_realized_loaded = True
            return
        with open(_REALIZED_PNL_STATE_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        if not isinstance(raw, dict):
            _daily_realized_loaded = True
            return
        bucket = raw.get(key, {})
        if isinstance(bucket, dict) and bucket.get("date") == today:
            _daily_realized_pnl = safe_int(bucket.get("pnl", 0), 0)
    except Exception:
        pass
    _daily_realized_loaded = True


def _save_realized_pnl_state():
    key = _realized_state_key()
    payload = {}
    try:
        if os.path.exists(_REALIZED_PNL_STATE_FILE):
            with open(_REALIZED_PNL_STATE_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    payload = loaded
    except Exception:
        payload = {}

    payload[key] = {
        "date": _daily_realized_date,
        "pnl": int(_daily_realized_pnl),
    }

    try:
        with open(_REALIZED_PNL_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _ensure_realized_state_loaded():
    if not _daily_realized_loaded:
        _load_realized_pnl_state()


def _daily_trade_guard_key() -> str:
    account_no = str(getattr(cfg, "ACCOUNT_NO", "")).strip() or "UNKNOWN"
    return f"{CURRENT_CFG_MODULE}::{account_no}"


def _load_daily_trade_guard_state():
    global _daily_trade_guard_date, _daily_trade_guard_loaded
    global _daily_bought_codes, _daily_sold_codes

    today = datetime.date.today().strftime("%Y-%m-%d")
    key = _daily_trade_guard_key()
    _daily_trade_guard_date = today
    _daily_bought_codes = set()
    _daily_sold_codes = set()

    try:
        if not os.path.exists(_DAILY_TRADE_GUARD_STATE_FILE):
            _daily_trade_guard_loaded = True
            return
        with open(_DAILY_TRADE_GUARD_STATE_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        if not isinstance(raw, dict):
            _daily_trade_guard_loaded = True
            return
        bucket = raw.get(key, {})
        if isinstance(bucket, dict) and bucket.get("date") == today:
            _daily_bought_codes = set(str(x).strip() for x in (bucket.get("bought") or []) if str(x).strip())
            _daily_sold_codes = set(str(x).strip() for x in (bucket.get("sold") or []) if str(x).strip())
    except Exception:
        pass
    _daily_trade_guard_loaded = True


def _save_daily_trade_guard_state():
    key = _daily_trade_guard_key()
    payload = {}
    try:
        if os.path.exists(_DAILY_TRADE_GUARD_STATE_FILE):
            with open(_DAILY_TRADE_GUARD_STATE_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    payload = loaded
    except Exception:
        payload = {}

    payload[key] = {
        "date": _daily_trade_guard_date,
        "bought": sorted(_daily_bought_codes),
        "sold": sorted(_daily_sold_codes),
    }

    try:
        with open(_DAILY_TRADE_GUARD_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _ensure_daily_trade_guard_loaded():
    if not _daily_trade_guard_loaded:
        _load_daily_trade_guard_state()


def _rollover_daily_trade_guard_if_needed():
    global _daily_trade_guard_date, _daily_bought_codes, _daily_sold_codes
    _ensure_daily_trade_guard_loaded()
    today = datetime.date.today().strftime("%Y-%m-%d")
    if _daily_trade_guard_date != today:
        _daily_trade_guard_date = today
        _daily_bought_codes = set()
        _daily_sold_codes = set()
        _save_daily_trade_guard_state()


def _mark_daily_buy(code: str):
    _rollover_daily_trade_guard_if_needed()
    _daily_bought_codes.add(str(code).strip())
    _save_daily_trade_guard_state()


def _mark_daily_sell(code: str):
    _rollover_daily_trade_guard_if_needed()
    _daily_sold_codes.add(str(code).strip())
    _save_daily_trade_guard_state()


def _is_daily_reentry_blocked(code: str) -> tuple[bool, str]:
    _rollover_daily_trade_guard_if_needed()
    code_s = str(code).strip()
    if code_s in _daily_sold_codes:
        return True, "당일 매도 이력 종목"
    if code_s in _daily_bought_codes:
        return True, "당일 매수 이력 종목"
    return False, ""


def _sync_realized_pnl_from_account(force: bool = False):
    """계좌 체결이력 기반 오늘 실현손익 동기화 (API 호출 과다 방지용 캐시 포함)."""
    global _daily_realized_pnl, _last_realized_sync_ts
    _rollover_realized_pnl_if_needed()

    now_ts = time.time()
    if not force and (now_ts - _last_realized_sync_ts) < 20:
        return

    try:
        realized = api.get_today_realized_pnl_by_market(current_market)
        _daily_realized_pnl = int(realized)
        _save_realized_pnl_state()
    except Exception:
        # 계좌이력 조회 실패 시 직전값 유지
        pass
    _last_realized_sync_ts = now_ts


def _rollover_realized_pnl_if_needed():
    global _daily_realized_date, _daily_realized_pnl
    _ensure_realized_state_loaded()
    today = datetime.date.today().strftime("%Y-%m-%d")
    if _daily_realized_date != today:
        _daily_realized_date = today
        _daily_realized_pnl = 0
        _save_realized_pnl_state()


def _telegram_help_text() -> str:
    return (
        "사용 가능한 명령어\n"
        "/실시간 (/realtime) : 장중 브리핑 즉시 1회 조회\n"
        "/매니저 (/manager) : 보유 종목 액션 가이드(보유/축소/손절)\n"
        "/보유 (/holdings) : 보유 종목/평가/현금/목표가/손절가 조회\n"
        "/매도 (/sell) : 보유 종목 선택 후 비율 매도\n"
        "/전량매도 (/sellall) : 전체 종목 전량 매도(2단계 확인)\n"
        "/취소 (/cancel) : 진행 중인 명령 취소\n"
        "/help : 도움말"
    )


def _set_telegram_bot_commands():
    if not TELEGRAM_NOTIFY_ENABLED or not TELEGRAM_BOT_TOKEN:
        return
    try:
        import requests
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setMyCommands"
        commands = [
            {"command": "realtime", "description": "장중 브리핑 즉시 1회 조회"},
            {"command": "manager", "description": "보유 종목 액션 가이드(보유/축소/손절)"},
            {"command": "holdings", "description": "보유/평가/목표가/손절가 조회"},
            {"command": "sell", "description": "보유 종목 선택 후 비율 매도"},
            {"command": "sellall", "description": "전체 종목 전량 매도(확인 포함)"},
            {"command": "cancel", "description": "진행 중인 명령 취소"},
            {"command": "help", "description": "도움말"},
        ]
        requests.post(url, json={"commands": commands}, timeout=10)
    except Exception:
        pass


def _collect_account_status():
    """
    텔레그램 알림용 계좌 스냅샷 생성.
    반환: (rows, available_cash, total_pnl, total_rate)
    """
    positions = get_account_positions() if current_market == "KR" else []
    if not positions:
        return [], 0, 0, 0.0

    rows = []
    total_cost = 0
    total_eval = 0

    for p in positions:
        code = p["code"]
        name = p["name"]
        qty = p["qty"]
        avg = max(1, p["avg_price"])
        cur = p["cur_price"]
        if cur <= 0:
            try:
                cur = safe_int(_get_price_detail_cached(code, current_market).get("stck_prpr", 0), avg)
            except Exception:
                cur = avg

        cost = avg * qty
        eva = cur * qty
        pnl = eva - cost
        rate = (cur - avg) / avg * 100
        total_cost += cost
        total_eval += eva
        rows.append({
            "code": code,
            "name": name,
            "qty": qty,
            "pnl": pnl,
            "rate": rate,
            "cur": cur,
        })

    total_pnl = total_eval - total_cost
    total_rate = (total_pnl / total_cost * 100) if total_cost > 0 else 0.0

    available_cash = 0
    if rows:
        ref_code = rows[0]["code"]
        ref_price = max(1, rows[0]["cur"])
        try:
            available_cash = api.get_available_cash_by_market(ref_code, ref_price, "KR")
        except Exception:
            available_cash = 0

    return rows, available_cash, total_pnl, total_rate


def _build_account_status_message() -> str:
    """장중 3분 주기 텔레그램 메시지 생성"""
    _rollover_realized_pnl_if_needed()
    _sync_realized_pnl_from_account()
    sync_portfolio_with_account()
    rows, available_cash, total_pnl, total_rate = _collect_account_status()
    total_icon = _profit_icon(total_rate)

    if not rows:
        return (
            "📊 장중 브리핑\n"
            f"💰 주문가능현금: {available_cash:,}원\n"
            f"{total_icon} 전체 평가손익: {total_pnl:+,}원 ({total_rate:+.2f}%)\n"
            f"🧾 오늘 실현손익: {_daily_realized_pnl:+,}원\n"
            "보유 종목 없음"
        )

    lines = [
        "📊 장중 브리핑",
        f"💰 주문가능현금: {available_cash:,}원",
        f"{total_icon} 전체 평가손익: {total_pnl:+,}원 ({total_rate:+.2f}%)",
        f"🧾 오늘 실현손익: {_daily_realized_pnl:+,}원",
        f"[{market_label(current_market)}] 보유 {len(rows)}개",
    ]
    for row in rows[:8]:
        icon = _profit_icon(row["rate"])
        lines.append(
            f"{icon} {row['name']}({row['code']}) {row['qty']}주 | "
            f"{row['rate']:+.2f}% | {row['pnl']:+,}원"
        )
        info = portfolio.get(row["code"])
        if not info:
            continue

        stop_price = int(info.get("stop", 0))
        target1 = int(info.get("target1", 0))
        target2 = int(info.get("target2", 0))
        cur = int(row.get("cur", 0))

        if stop_price > 0 and cur > 0 and cur <= stop_price:
            lines.append(f"   ‼️ 손절가 도달 · 손절 권장 (현재가 {cur:,}원 / 손절가 {stop_price:,}원)")
        elif target2 > 0 and cur >= target2:
            lines.append(f"   🎉 2차 목표 도달 · 익절 권장 (현재가 {cur:,}원 / 2차 {target2:,}원)")
        elif target1 > 0 and cur >= target1:
            lines.append(f"   🎉 1차 목표 도달 · 익절 권장 (현재가 {cur:,}원 / 1차 {target1:,}원)")
    return "\n".join(lines)


def _build_market_close_message() -> str:
    """장 마감 1회 브리핑 메시지 생성"""
    _rollover_realized_pnl_if_needed()
    _sync_realized_pnl_from_account(force=True)
    rows, available_cash, total_pnl, total_rate = _collect_account_status()
    total_icon = _profit_icon(total_rate)
    lines = [
        "🔔 장 마감입니다. 고생하셨습니다.",
        "📌 오늘 주식 보유 결과 브리핑",
        f"💰 주문가능현금: {available_cash:,}원",
        f"{total_icon} 전체 평가손익: {total_pnl:+,}원 ({total_rate:+.2f}%)",
        f"🧾 오늘 실현손익: {_daily_realized_pnl:+,}원",
    ]
    if not rows:
        lines.append("보유 종목 없음")
    else:
        lines.append(f"[{market_label(current_market)}] 보유 {len(rows)}개")
        for row in rows[:8]:
            icon = _profit_icon(row["rate"])
            lines.append(
                f"{icon} {row['name']}({row['code']}) {row['qty']}주 | "
                f"{row['rate']:+.2f}% | {row['pnl']:+,}원"
            )
    lines.append("다음 장 시작 전까지 알림 발송을 중지합니다.")
    return "\n".join(lines)


def telegram_status_notifier_loop():
    global _tg_last_notified_at, _tg_last_close_message_date
    while True:
        try:
            if TELEGRAM_NOTIFY_ENABLED and current_market == "KR" and TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
                now_ts = time.time()
                now_dt = datetime.datetime.now()
                today = now_dt.strftime("%Y-%m-%d")
                _, close_t = _market_open_close_times()

                # 사용자 요청: 장중에는 3분마다 무조건 발송
                if _is_kr_market_open(now_dt):
                    if now_ts - _tg_last_notified_at >= 180:
                        _send_telegram_message(_build_account_status_message())
                        _tg_last_notified_at = now_ts
                else:
                    # 장 마감 후 1회 브리핑만 전송하고 이후 다음 장 전까지 중지
                    if now_dt.weekday() < 5 and now_dt.time() >= close_t and _tg_last_close_message_date != today:
                        _send_telegram_message(_build_market_close_message())
                        _tg_last_close_message_date = today
        except Exception:
            pass
        time.sleep(5)


def _get_sellable_positions() -> list[dict]:
    sync_portfolio_with_account()
    positions = []
    for code, info in portfolio.items():
        qty = int(info.get("qty", 0))
        if qty <= 0:
            continue
        cur_price = 0
        try:
            market = info.get("market", current_market)
            detail = _get_price_detail_cached(code, market)
            cur_price = safe_int(detail.get("stck_prpr", 0), 0)
        except Exception:
            cur_price = 0
        positions.append({
            "code": code,
            "name": info.get("name", code),
            "qty": qty,
            "market": info.get("market", current_market),
            "avg_price": int(info.get("avg_price", 0)),
            "cur_price": cur_price,
        })
    positions.sort(key=lambda x: x["name"])
    return positions


def _execute_manual_sell(code: str, sell_qty: int) -> tuple[bool, str]:
    sync_portfolio_with_account()
    info = portfolio.get(code)
    if not info:
        return False, "해당 종목은 현재 보유 목록에 없습니다."

    hold_qty = int(info.get("qty", 0))
    if hold_qty <= 0:
        return False, "보유 수량이 0주입니다."

    qty = max(1, min(int(sell_qty), hold_qty))
    market = info.get("market", current_market)
    name = info.get("name", code)
    avg_price = int(info.get("avg_price", 0))

    cur_price = avg_price
    try:
        detail = _get_price_detail_cached(code, market)
        fetched = safe_int(detail.get("stck_prpr", 0), avg_price)
        if fetched > 0:
            cur_price = fetched
    except Exception:
        pass

    result = api.sell_market_order_by_market(code, qty, market)
    if result.get("rt_cd") != "0":
        return False, f"매도 실패: {result.get('msg1', '주문 오류')}"

    if qty >= hold_qty:
        portfolio.pop(code, None)
    else:
        info["qty"] = hold_qty - qty

    notify_sell_event("텔레그램수동", name, code, qty, cur_price, avg_price, market=market)
    return True, f"{name}({code}) {qty}주 매도 완료"


def _execute_force_sell_all_manual() -> tuple[bool, str]:
    sync_portfolio_with_account()
    if not portfolio:
        return False, "현재 보유 종목이 없습니다."

    fail_messages = []
    sold_count = 0
    for code, info in list(portfolio.items()):
        try:
            market = info.get("market", current_market)
            qty = int(info.get("qty", 0))
            if qty <= 0:
                continue

            cur_price = int(info.get("avg_price", 1))
            try:
                detail = _get_price_detail_cached(code, market)
                fetched = safe_int(detail.get("stck_prpr", 0), cur_price)
                if fetched > 0:
                    cur_price = fetched
            except Exception:
                pass

            result = api.sell_market_order_by_market(code, qty, market)
            if result.get("rt_cd") == "0":
                portfolio.pop(code, None)
                sold_count += 1
                notify_sell_event("텔레그램전량", info.get("name", code), code, qty, cur_price, int(info.get("avg_price", 0)), market=market)
            else:
                fail_messages.append(f"{info.get('name', code)}: {result.get('msg1', '주문 실패')}")
        except Exception as e:
            fail_messages.append(f"{info.get('name', code)}: {e}")
        time.sleep(0.2)

    if sold_count == 0:
        return False, "전량 매도에 실패했습니다."
    if fail_messages:
        return True, f"일부 매도 완료({sold_count}종목). 실패: " + " | ".join(fail_messages[:3])
    return True, f"전량 매도 완료: {sold_count}종목"


def _build_holdings_detail_message() -> str:
    sync_portfolio_with_account()
    if not portfolio:
        return "📌 보유 현황\n현재 보유 종목이 없습니다."

    snapshots, totals = get_portfolio_snapshot()
    available_cash = 0
    if snapshots:
        ref = snapshots[0]
        ref_info = portfolio.get(ref["code"], {})
        ref_market = ref_info.get("market", current_market)
        ref_price = ref["cur_price"] if ref["cur_price"] > 0 else ref["avg_price"]
        try:
            available_cash = api.get_available_cash_by_market(ref["code"], ref_price, ref_market)
        except Exception:
            available_cash = 0

    total_asset = totals["total_eval"] + available_cash
    invest_ratio = (totals["total_eval"] / total_asset * 100) if total_asset > 0 else 0.0
    cash_ratio = (available_cash / total_asset * 100) if total_asset > 0 else 0.0

    lines = [
        "📌 보유 현황",
        f"시장: {market_label(current_market)}",
        f"총자산(추정): {total_asset:,}원",
        f"투자금(평가): {totals['total_eval']:,}원 ({invest_ratio:.1f}%)",
        f"현금(주문가능): {available_cash:,}원 ({cash_ratio:.1f}%)",
        f"평가손익: {totals['total_pnl']:+,}원 ({totals['total_pnl_rate']:+.2f}%)",
        f"보유 종목: {len(snapshots)}개",
    ]

    for idx, s in enumerate(snapshots, 1):
        lines.append(
            f"{idx}. {s['name']}({s['code']}) {s['qty']}주 | "
            f"평단:{s['avg_price']:,}원 현재:{s['cur_price']:,}원 | "
            f"손익:{s['pnl_amount']:+,}원 ({s['pnl_rate']:+.2f}%)"
        )
        lines.append(
            f"   목표가: 1차 {s['target1']:,}원 / 2차 {s['target2']:,}원 | "
            f"손절가: {s['stop']:,}원"
        )
    return "\n".join(lines)


def _evaluate_manager_signal(code: str, info: dict) -> dict:
    market = info.get("market", current_market)
    name = info.get("name", code)
    qty = int(info.get("qty", 0))
    avg = max(1, int(info.get("avg_price", 1)))
    stop = max(1, int(info.get("stop", 1)))
    target1 = max(1, int(info.get("target1", avg)))
    target2 = max(1, int(info.get("target2", target1)))

    detail = {}
    try:
        detail = _get_price_detail_cached(code, market) or {}
    except Exception:
        detail = {}

    cur = safe_int(detail.get("stck_prpr", 0), avg)
    if cur <= 0:
        cur = avg

    change_rate = safe_float(detail.get("prdy_ctrt", 0), 0.0)
    vol_tnrt = safe_float(detail.get("vol_tnrt", 0), 0.0)
    w52_high = safe_float(detail.get("w52_hgpr", cur), float(cur))
    w52_low = safe_float(detail.get("w52_lwpr", cur), float(cur))

    profit_rate = ((cur - avg) / avg * 100) if avg > 0 else 0.0
    stop_gap_rate = ((cur - stop) / cur * 100) if cur > 0 else 0.0
    to_t1_rate = ((target1 - cur) / cur * 100) if cur > 0 else 0.0
    to_t2_rate = ((target2 - cur) / cur * 100) if cur > 0 else 0.0

    score = 50
    reasons = []

    # 1) 손절선/목표선과의 거리 (리스크 우선)
    if cur <= stop:
        score -= 40
        reasons.append("손절가 하회")
    elif stop_gap_rate <= 1.0:
        score -= 18
        reasons.append("손절가 근접(1% 이내)")
    elif stop_gap_rate <= 2.5:
        score -= 10
        reasons.append("손절가 근접(2.5% 이내)")
    else:
        score += 6
        reasons.append("손절선 여유")

    if cur >= target2:
        score += 22
        reasons.append("2차 목표가 도달")
    elif cur >= target1:
        score += 12
        reasons.append("1차 목표가 도달")

    # 2) 모멘텀(등락률) + 수급(회전율)
    if change_rate >= 2.0:
        score += 8
        reasons.append(f"단기 모멘텀 양호({change_rate:+.2f}%)")
    elif change_rate <= -2.0:
        score -= 8
        reasons.append(f"단기 모멘텀 약세({change_rate:+.2f}%)")

    if vol_tnrt >= 220:
        score += 8
        reasons.append(f"거래량 강함({vol_tnrt:.0f}%)")
    elif vol_tnrt <= 70:
        score -= 6
        reasons.append(f"거래량 둔화({vol_tnrt:.0f}%)")

    # 3) 52주 고점/저점 위치
    if w52_high > 0 and (cur / w52_high) >= 0.97:
        score += 6
        reasons.append("52주 고점권(추세 유지)")
    if w52_low > 0 and (cur / w52_low) <= 1.08:
        score -= 5
        reasons.append("52주 저점권(약세 가능성)")

    # 4) 현재 수익 상태 보정
    if profit_rate >= 6:
        score += 6
    elif profit_rate <= -4:
        score -= 8

    score = max(0, min(100, int(round(score))))

    if cur <= stop or score <= 30:
        action = "손절 우선"
    elif score <= 45:
        action = "비중 축소 권장"
    elif score >= 70:
        action = "좀 기다려보세요"
    else:
        action = "관망(조건 확인)"

    trigger_cut = stop
    trigger_keep = target1 if cur < target1 else target2
    return {
        "code": code,
        "name": name,
        "qty": qty,
        "cur": cur,
        "avg": avg,
        "target1": target1,
        "target2": target2,
        "stop": stop,
        "profit_rate": profit_rate,
        "to_t1_rate": to_t1_rate,
        "to_t2_rate": to_t2_rate,
        "score": score,
        "action": action,
        "trigger_cut": trigger_cut,
        "trigger_keep": trigger_keep,
        "reasons": reasons[:4],
    }


def _build_manager_message() -> str:
    sync_portfolio_with_account()
    if not portfolio:
        return "🧠 매니저 리포트\n현재 보유 종목이 없습니다."

    reports = []
    for code, info in portfolio.items():
        qty = int(info.get("qty", 0))
        if qty <= 0:
            continue
        try:
            reports.append(_evaluate_manager_signal(code, info))
        except Exception as e:
            reports.append({
                "name": info.get("name", code),
                "code": code,
                "error": str(e),
            })
        time.sleep(0.05)

    actionable = [r for r in reports if not r.get("error")]
    errors = [r for r in reports if r.get("error")]
    actionable.sort(key=lambda x: x.get("score", 0))

    lines = [
        "🧠 매니저 리포트",
        "점수 낮은 종목부터 우선 점검하세요.",
        "",
    ]

    for idx, r in enumerate(actionable, 1):
        action = r["action"]
        if action == "손절 우선":
            icon = "🔴"
        elif action == "비중 축소 권장":
            icon = "🟠"
        elif action == "좀 기다려보세요":
            icon = "🟢"
        else:
            icon = "🟡"

        direction = "▲" if r["profit_rate"] >= 0 else "▼"
        if r.get("error"):
            continue
        lines.append(f"{icon} {idx}) {r['name']}({r['code']}) · {r['qty']}주")
        lines.append(f"   판단: {action} | 신뢰도: {r['score']}/100")
        lines.append(f"   손익: {direction} {r['profit_rate']:+.2f}% (현재 {r['cur']:,} / 평단 {r['avg']:,})")
        lines.append(f"   가격대: 손절 {r['stop']:,} | 1차 {r['target1']:,} | 2차 {r['target2']:,}")
        lines.append(f"   트리거: {r['trigger_cut']:,} 이탈 시 손절 / {r['trigger_keep']:,} 회복 시 보유")
        if r.get("reasons"):
            lines.append(f"   근거: {' · '.join(r['reasons'])}")
        lines.append("")

    for err in errors:
        lines.append(f"⚪ 분석 실패: {err['name']}({err['code']}) - {err['error']}")

    if actionable:
        lines.append("")
        lines.append("범례: 🔴손절 우선 / 🟠비중 축소 / 🟡관망 / 🟢보유 우세")
    return "\n".join(lines)


def _handle_telegram_sell_flow(chat_id: str, text: str):
    normalized = text.strip()
    if not normalized:
        return

    if normalized in ("/취소", "취소", "/cancel", "cancel"):
        _tg_sell_sessions.pop(chat_id, None)
        _send_telegram_message_to(chat_id, "현재 매도 요청을 취소했습니다.")
        return

    if normalized in ("/help", "/도움", "/start", "/"):
        _send_telegram_message_to(
            chat_id,
            _telegram_help_text(),
        )
        return

    if normalized in ("/실시간", "/realtime", "/now"):
        _send_telegram_message_to(chat_id, _build_account_status_message())
        return

    if normalized in ("/매니저", "/manager"):
        _send_telegram_message_to(chat_id, _build_manager_message())
        return

    if normalized in ("/보유", "/holdings"):
        _send_telegram_message_to(chat_id, _build_holdings_detail_message())
        return

    if normalized in ("/매도", "/sell"):
        positions = _get_sellable_positions()
        if not positions:
            _send_telegram_message_to(chat_id, "현재 보유 종목이 없습니다.")
            return
        _tg_sell_sessions[chat_id] = {
            "step": "pick_stock",
            "positions": positions,
        }
        lines = ["매도할 종목 번호를 입력하세요."]
        for idx, pos in enumerate(positions, 1):
            lines.append(f"{idx}. {pos['name']}({pos['code']}) - {pos['qty']}주")
        lines.append("취소하려면 /취소")
        _send_telegram_message_to(chat_id, "\n".join(lines))
        return

    if normalized in ("/전량매도", "/sellall"):
        if not _get_sellable_positions():
            _send_telegram_message_to(chat_id, "현재 보유 종목이 없습니다.")
            return
        _tg_sell_sessions[chat_id] = {
            "step": "confirm_force_sell",
        }
        _send_telegram_message_to(
            chat_id,
            "전량 매도 하시겠습니까?\n"
            "1. yes\n"
            "2. no (취소)",
        )
        return

    session = _tg_sell_sessions.get(chat_id)
    if not session:
        return

    if session.get("step") == "confirm_force_sell":
        if normalized == "1":
            ok, message = _execute_force_sell_all_manual()
            _tg_sell_sessions.pop(chat_id, None)
            _send_telegram_message_to(chat_id, message if ok else f"실패: {message}")
            return
        if normalized == "2":
            _tg_sell_sessions.pop(chat_id, None)
            _send_telegram_message_to(chat_id, "전량 매도를 취소했습니다.")
            return
        _send_telegram_message_to(chat_id, "1 또는 2로 입력해주세요.")
        return

    if session.get("step") == "pick_stock":
        try:
            selected_idx = int(normalized)
        except ValueError:
            _send_telegram_message_to(chat_id, "번호로 입력해주세요. 예) 1")
            return

        positions = session.get("positions", [])
        if selected_idx < 1 or selected_idx > len(positions):
            _send_telegram_message_to(chat_id, "유효한 번호가 아닙니다. 목록의 번호를 다시 입력해주세요.")
            return

        selected = positions[selected_idx - 1]
        session["step"] = "pick_ratio"
        session["selected"] = selected
        _send_telegram_message_to(
            chat_id,
            f"{selected['name']}({selected['code']}) 선택됨. 매도 수량을 선택하세요.\n"
            "1. 25%\n"
            "2. 50%\n"
            "3. 75%\n"
            "4. 100% (전량)\n"
            "취소하려면 /취소",
        )
        return

    if session.get("step") == "pick_ratio":
        ratio_map = {
            "1": 0.25,
            "2": 0.50,
            "3": 0.75,
            "4": 1.00,
        }
        ratio = ratio_map.get(normalized)
        if ratio is None:
            _send_telegram_message_to(chat_id, "1~4 중에서 선택해주세요.")
            return

        selected = session.get("selected") or {}
        code = selected.get("code", "")
        base_qty = int(selected.get("qty", 0))
        if not code or base_qty <= 0:
            _tg_sell_sessions.pop(chat_id, None)
            _send_telegram_message_to(chat_id, "선택 정보가 만료되었습니다. 다시 /매도를 입력해주세요.")
            return

        sell_qty = base_qty if ratio >= 1.0 else max(1, int(base_qty * ratio))
        ok, message = _execute_manual_sell(code, sell_qty)
        _tg_sell_sessions.pop(chat_id, None)
        _send_telegram_message_to(chat_id, message if ok else f"실패: {message}")


def telegram_command_listener_loop():
    global _tg_update_offset, _tg_updates_bootstrapped, _tg_commands_registered
    while True:
        try:
            if not TELEGRAM_NOTIFY_ENABLED or not TELEGRAM_BOT_TOKEN:
                time.sleep(3)
                continue

            if not _tg_commands_registered:
                _set_telegram_bot_commands()
                _tg_commands_registered = True

            import requests
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
            params = {
                "timeout": 20,
                "offset": _tg_update_offset,
                "allowed_updates": ["message"],
            }
            res = requests.get(url, params=params, timeout=25)
            data = res.json() if res.ok else {}
            updates = data.get("result", []) if isinstance(data, dict) else []
            if not updates:
                continue

            # 기동 직후에는 누적 메시지를 스킵하고 이후 메시지부터 처리
            if not _tg_updates_bootstrapped:
                max_id = max(int(u.get("update_id", 0)) for u in updates)
                _tg_update_offset = max_id + 1
                _tg_updates_bootstrapped = True
                continue

            for update in updates:
                update_id = int(update.get("update_id", 0))
                _tg_update_offset = max(_tg_update_offset, update_id + 1)

                msg = update.get("message", {})
                text = str(msg.get("text", "")).strip()
                chat = msg.get("chat", {})
                chat_id = str(chat.get("id", "")).strip()
                if not text or not chat_id:
                    continue

                # 지정된 chat_id가 있으면 해당 채팅만 허용
                if TELEGRAM_CHAT_ID and chat_id != str(TELEGRAM_CHAT_ID).strip():
                    continue

                _handle_telegram_sell_flow(chat_id, text)
        except Exception:
            time.sleep(2)
            continue


def format_elapsed(seconds: int) -> str:
    minutes, sec = divmod(max(0, int(seconds)), 60)
    return f"{minutes:02d}:{sec:02d}"


def safe_float(value, default: float = 0.0) -> float:
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return default


def safe_int(value, default: int = 0) -> int:
    try:
        return int(round(safe_float(value, float(default))))
    except (TypeError, ValueError):
        return default


def market_label(market: str) -> str:
    return "국장" if market == "KR" else "미장"


def _is_lunch_liquidity_time(now_dt: datetime.datetime = None) -> bool:
    now_dt = now_dt or datetime.datetime.now()
    if now_dt.weekday() >= 5:
        return False
    start_t = _parse_hhmm_to_time(SCREENING_LUNCH_START, "11:20")
    end_t = _parse_hhmm_to_time(SCREENING_LUNCH_END, "13:10")
    return start_t <= now_dt.time() <= end_t


def _aggressive_screening_thresholds(relax_factor: float = 1.0) -> tuple[float, float, int]:
    factor = max(0.2, min(1.0, float(relax_factor)))
    if SCREENING_LUNCH_RELAX_ENABLED and _is_lunch_liquidity_time():
        factor = min(factor, max(0.2, min(1.0, SCREENING_LUNCH_RELAX_FACTOR)))

    min_change = max(0.3, SCREENING_MIN_CHANGE_RATE * factor)
    min_vol = max(60.0, SCREENING_MIN_VOL_TNRT * factor)
    min_value = int(max(100000000, SCREENING_MIN_TRADING_VALUE * factor))
    return min_change, min_vol, min_value


def parse_balance_row(row: dict) -> dict | None:
    """잔고 행을 표준 포맷으로 변환"""
    code = (
        str(row.get("pdno", "")).strip()
        or str(row.get("mksc_shrn_iscd", "")).strip()
        or str(row.get("ovrs_pdno", "")).strip()
    )
    qty = safe_int(
        row.get("hldg_qty", row.get("hold_qty", row.get("ovrs_cblc_qty", 0))),
        0,
    )
    if not code or qty <= 0:
        return None

    name = (
        str(row.get("prdt_name", "")).strip()
        or str(row.get("hldg_pdno_nm", "")).strip()
        or str(row.get("hts_kor_isnm", "")).strip()
        or code
    )
    avg_price = safe_int(
        row.get("pchs_avg_pric", row.get("pchs_avg_pric", row.get("avg_prvs", 0))),
        0,
    )
    cur_price = safe_int(row.get("prpr", row.get("ovrs_now_pric", 0)), 0)

    if avg_price <= 0 and cur_price > 0:
        avg_price = cur_price
    if avg_price <= 0:
        avg_price = 1

    return {
        "code": code,
        "name": name,
        "qty": qty,
        "avg_price": avg_price,
        "cur_price": cur_price,
    }


def get_account_positions() -> list[dict]:
    """실계좌 보유 종목 조회(국장 기준)"""
    if current_market != "KR":
        return []
    try:
        rows = api.get_balance()
    except Exception as e:
        log(f"[WARN] 계좌 잔고 조회 실패: {e}")
        return []

    positions = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        parsed = parse_balance_row(row)
        if parsed:
            positions.append(parsed)
    return positions


def sync_portfolio_with_account():
    """
    내부 portfolio를 실계좌 잔고 기준으로 동기화.
    - 기존 보유 종목(수동매수 포함)도 5번 화면/점검에서 일치하게 처리
    """
    if current_market != "KR":
        return

    account_positions = get_account_positions()
    if not account_positions:
        portfolio.clear()
        return

    account_map = {p["code"]: p for p in account_positions}

    # 계좌에 없는 종목 제거
    for code in list(portfolio.keys()):
        if code not in account_map:
            portfolio.pop(code, None)

    # 계좌 기준으로 갱신/보강
    for code, p in account_map.items():
        avg_price = max(1, p["avg_price"])
        if code not in portfolio:
            portfolio[code] = {
                "market": "KR",
                "name": p["name"],
                "qty": p["qty"],
                "avg_price": avg_price,
                "target1": round(avg_price * (1 + TARGET_RATE_1)),
                "target2": round(avg_price * (1 + TARGET_RATE_2)),
                "stop": round(avg_price * (1 - STOP_LOSS_RATE)),
                "sold_half": False,
                "target1_alerted": False,
                "target2_alerted": False,
                "stop_alerted": False,
                "averaged_down": False,
                "stop_breach_count": 0,
                "entry_time": now_str(),
                "entry_ts": time.time(),
                "last_buy_ts": time.time(),
                "add_buy_count": 0,
                "hold_until": datetime.date.today().strftime("%Y-%m-%d"),
            }
            continue

        info = portfolio[code]
        info["market"] = "KR"
        info["name"] = p["name"]
        info["qty"] = p["qty"]
        info["avg_price"] = avg_price
        info["target1"] = round(avg_price * (1 + TARGET_RATE_1))
        info["target2"] = round(avg_price * (1 + TARGET_RATE_2))
        if not info.get("averaged_down", False):
            info["stop"] = round(avg_price * (1 - STOP_LOSS_RATE))
        else:
            info["stop"] = round(avg_price * (1 - POST_DCA_STOP_LOSS_RATE))
        info.setdefault("last_buy_ts", time.time())
        info.setdefault("add_buy_count", 0)
        info.setdefault("target1_alerted", False)
        info.setdefault("target2_alerted", False)
        info.setdefault("stop_alerted", False)


def get_portfolio_snapshot() -> tuple[list, dict]:
    """보유 종목의 실시간 평가 정보를 계산"""
    snapshots = []
    total_cost = 0
    total_eval = 0

    for code, info in portfolio.items():
        qty = info["qty"]
        avg = info["avg_price"]
        cost_amount = avg * qty
        total_cost += cost_amount

        entry_ts = info.get("entry_ts", time.time())
        elapsed_sec = int(time.time() - entry_ts)
        remain_3m_sec = max(0, 180 - elapsed_sec)
        is_3m_ready = elapsed_sec >= 180

        cur_price = 0
        eval_amount = cost_amount
        pnl_amount = 0
        pnl_rate = 0.0
        price_ok = False

        try:
            detail = _get_price_detail_cached(code, info.get("market", current_market))
            cur_price = int(detail.get("stck_prpr", 0))
            if cur_price > 0:
                eval_amount = cur_price * qty
                pnl_amount = eval_amount - cost_amount
                pnl_rate = (cur_price - avg) / avg * 100
                price_ok = True
        except Exception:
            pass

        total_eval += eval_amount
        snapshots.append({
            "code": code,
            "name": info["name"],
            "qty": qty,
            "avg_price": avg,
            "cur_price": cur_price,
            "eval_amount": eval_amount,
            "pnl_amount": pnl_amount,
            "pnl_rate": pnl_rate,
            "is_3m_ready": is_3m_ready,
            "remain_3m_sec": remain_3m_sec,
            "elapsed_sec": elapsed_sec,
            "price_ok": price_ok,
            "target1": info["target1"],
            "target2": info["target2"],
            "stop": info["stop"],
        })
        time.sleep(0.05)

    total_pnl = total_eval - total_cost
    total_pnl_rate = (total_pnl / total_cost * 100) if total_cost > 0 else 0.0
    totals = {
        "total_cost": total_cost,
        "total_eval": total_eval,
        "total_pnl": total_pnl,
        "total_pnl_rate": total_pnl_rate,
    }
    return snapshots, totals


def notify_sell_event(reason: str, name: str, code: str, qty: int, sell_price: int, avg_price: int, market: str = None):
    """매도 체결 알림 + 갱신된 보유 상태 출력"""
    global _daily_realized_pnl
    _rollover_realized_pnl_if_needed()
    pnl_amount = (sell_price - avg_price) * qty
    pnl_rate = ((sell_price - avg_price) / avg_price * 100) if avg_price > 0 else 0.0
    # 실현손익은 계좌 체결이력 기준을 우선 사용한다.
    # (내부 평균단가 누적만으로 계산하면 수동거래/부분체결 시 오차 발생)
    _sync_realized_pnl_from_account(force=True)
    _mark_daily_sell(code)
    target_market = market or current_market
    message = (
        f"🔔 매도 체결 [{reason}]\n"
        f"시장: {market_label(target_market)}\n"
        f"종목: {name}({code})\n"
        f"수량: {qty}주\n"
        f"체결가: {sell_price:,}원\n"
        f"실현손익: {pnl_amount:+,}원 ({pnl_rate:+.2f}%)"
    )
    log(
        f"🔔 매도 알림[{reason}] — {name}({code}) {qty}주 @ {sell_price:,}원 | "
        f"실현손익:{pnl_amount:+,}원 ({pnl_rate:+.2f}%)"
    )
    _send_telegram_message(message)
    show_portfolio()


def notify_buy_event(name: str, code: str, qty: int, buy_price: int):
    """매수 체결 알림(콘솔 + 텔레그램)"""
    _mark_daily_buy(code)
    message = (
        f"🟢 매수 체결\n"
        f"시장: {market_label(current_market)}\n"
        f"종목: {name}({code})\n"
        f"수량: {qty}주\n"
        f"체결가: {buy_price:,}원"
    )
    log(f"🔔 매수 알림 — {name}({code}) 체결, 즉시 보유 상태를 갱신합니다.")
    _send_telegram_message(message)
    show_portfolio()


def calculate_order_amount(code: str, price: int, market: str, buy_pct: float = None) -> tuple[int, int]:
    """
    공통 주문 금액 계산.
    반환: (order_amount, available_cash)
    """
    available_cash = api.get_available_cash_by_market(code, price, market)
    if available_cash <= 0:
        return 0, 0

    snapshots, totals = get_portfolio_snapshot()
    total_eval = totals["total_eval"]
    total_asset = total_eval + available_cash
    max_investable = max(0, int(total_asset * (1 - MIN_CASH_RATIO)) - total_eval)
    if max_investable <= 0:
        return 0, available_cash

    pct = BUY_PCT if buy_pct is None else max(0.01, float(buy_pct))
    target_amount = int(available_cash * pct)
    order_amount = max(BUY_MIN_AMOUNT, target_amount)
    order_amount = min(order_amount, BUY_MAX_AMOUNT, available_cash, max_investable)
    return order_amount, available_cash


def should_add_to_position(info: dict, candidate: dict) -> tuple[bool, str]:
    """보유 종목 추가매수(피라미딩) 조건 확인"""
    if not ADD_ON_ENABLED:
        return False, "추가매수 비활성화"
    if info.get("market") != current_market:
        return False, "다른 시장 보유 종목"

    add_count = int(info.get("add_buy_count", 0))
    if add_count >= ADD_ON_MAX_PER_STOCK:
        return False, f"추가매수 한도 도달({ADD_ON_MAX_PER_STOCK}회)"

    last_buy_ts = float(info.get("last_buy_ts", 0))
    if last_buy_ts > 0 and (time.time() - last_buy_ts) < ADD_ON_COOLDOWN_SEC:
        remain = int(ADD_ON_COOLDOWN_SEC - (time.time() - last_buy_ts))
        return False, f"쿨다운 중({remain}초)"

    score = int(candidate.get("score", 0))
    if score < ADD_ON_MIN_SCORE:
        return False, f"점수 부족({score} < {ADD_ON_MIN_SCORE})"

    cur_price = int(candidate.get("price", 0))
    avg_price = int(info.get("avg_price", 0))
    if cur_price <= 0 or avg_price <= 0:
        return False, "가격 정보 부족"

    profit_rate = (cur_price - avg_price) / avg_price * 100
    if profit_rate < ADD_ON_MIN_PROFIT_RATE:
        return False, f"손실 구간 과도({profit_rate:.2f}%)"
    if profit_rate > ADD_ON_MAX_CHASE_RATE:
        return False, f"추격 매수 과열({profit_rate:.2f}%)"

    momentum_rate = safe_float(candidate.get("change_rate", 0))
    if momentum_rate < ADD_ON_MIN_MOMENTUM_RATE:
        return False, f"모멘텀 부족({momentum_rate:.2f}%)"

    return True, "추가매수 조건 충족"


def execute_average_down(code: str, info: dict, cur_price: int, detail: dict) -> bool:
    """손절 구간 진입 시 1회 물타기 실행"""
    name = info["name"]
    vol_tnrt = safe_float(detail.get("vol_tnrt", 0))
    change_rate = safe_float(detail.get("prdy_ctrt", 0))

    if vol_tnrt < DCA_MIN_VOL_TNRT:
        log(
            f"[DCA SKIP] {name} 수급 약함 "
            f"(회전율:{vol_tnrt:.1f}% < 기준:{DCA_MIN_VOL_TNRT:.1f}%)"
        )
        return False

    if change_rate < DCA_MIN_CHANGE_RATE:
        log(
            f"[DCA SKIP] {name} 급락 구간 "
            f"(등락률:{change_rate:.2f}% < 기준:{DCA_MIN_CHANGE_RATE:.2f}%)"
        )
        return False

    market = info.get("market", current_market)
    order_amount, available_cash = calculate_order_amount(code, cur_price, market)
    if order_amount < cur_price:
        log(
            f"[DCA SKIP] {name} 물타기 금액 부족 "
            f"(주문가능:{available_cash:,}원, 산출:{order_amount:,}원, 현재가:{cur_price:,}원)"
        )
        return False

    add_qty = max(1, order_amount // cur_price)
    result = api.buy_market_order_by_market(code, add_qty, market)
    if result.get("rt_cd") != "0":
        log(f"[DCA ✗] {name} 물타기 실패: {result.get('msg1', '')}")
        return False

    prev_qty = info["qty"]
    prev_avg = info["avg_price"]
    new_qty = prev_qty + add_qty
    new_avg = round((prev_avg * prev_qty + cur_price * add_qty) / new_qty)

    info["qty"] = new_qty
    info["avg_price"] = new_avg
    info["target1"] = round(new_avg * (1 + TARGET_RATE_1))
    info["target2"] = round(new_avg * (1 + TARGET_RATE_2))
    info["stop"] = round(new_avg * (1 - POST_DCA_STOP_LOSS_RATE))
    info["averaged_down"] = True
    info["dca_time"] = now_str()
    info["stop_breach_count"] = 0
    info["target1_alerted"] = False
    info["target2_alerted"] = False
    info["stop_alerted"] = False

    log(
        f"🔔 물타기 알림 — {name}({code}) {add_qty}주 @ {cur_price:,}원 | "
        f"평단:{prev_avg:,}원 -> {new_avg:,}원 | 새 손절:{info['stop']:,}원 "
        f"(-{POST_DCA_STOP_LOSS_RATE*100:.1f}%)"
    )
    show_portfolio()
    return True


# ── 스크리닝 ──────────────────────────────────────────────

def score_stock(
    code: str,
    name: str,
    change_rate: float,
    market: str,
    aggressive_relax_factor: float = 1.0,
    allow_keyword_relax: bool = False,
    skip_entry_filters: bool = False,
    preopen_mode: bool = False,
) -> dict | None:
    """
    종목 점수 계산.
    반환: { code, name, score, reasons, price, target1, target2, stop,
            hold_until, entry_signal_time }
    실패 또는 기준 미달 시 None 반환.
    """
    try:
        detail = (
            api.get_premarket_price_snapshot_by_market(code, market)
            if preopen_mode
            else _get_price_detail_cached(code, market)
        )
        if not detail:
            return None

        price        = int(detail.get("stck_prpr", 0))
        vol_tnrt     = float(detail.get("vol_tnrt", 0))     # 거래량 회전율(대용)
        acml_vol     = int(detail.get("acml_vol", 0))
        avls_hmcl_no = int(detail.get("avls_hmcl_no", 1))   # 상장주식수(간이 평균 거래량 대용)
        w52_hgpr     = float(detail.get("w52_hgpr", price))
        w52_lwpr     = float(detail.get("w52_lwpr", price))
        per          = detail.get("per", "")

        if price <= 0:
            return None

        lowered_name = str(name).lower()
        if (not skip_entry_filters) and market == "KR" and AGGRESSIVE_SCREENING:
            if (not allow_keyword_relax) and any(token in lowered_name for token in SCREENING_EXCLUDE_KEYWORDS):
                return None

            min_change, min_vol_tnrt, min_trading_value = _aggressive_screening_thresholds(aggressive_relax_factor)

            if change_rate < max(CHANGE_RATE_MIN, min_change):
                return None

            if vol_tnrt < max(VOLUME_RATIO_MIN * 100, min_vol_tnrt):
                return None

            trading_value = int(price * max(0, acml_vol))
            if trading_value < min_trading_value:
                return None

        score   = 0
        reasons = []

        # 1. 거래량 배율 (vol_tnrt: % 값으로 취급)
        # VOLUME_RATIO_MIN=1.5라면 최소 기준은 150%
        volume_ratio_pct = VOLUME_RATIO_MIN * 100
        if vol_tnrt >= max(300, volume_ratio_pct + 100):
            score += 15
            reasons.append(f"거래량 폭발({vol_tnrt:.0f}%)")
        elif vol_tnrt >= max(200, volume_ratio_pct):
            score += 10
            reasons.append(f"거래량 증가({vol_tnrt:.0f}%)")
        elif vol_tnrt >= volume_ratio_pct:
            score += 6
            reasons.append(f"거래량 기준 충족({vol_tnrt:.0f}%)")

        # 2. 등락률
        if CHANGE_RATE_MIN <= change_rate <= CHANGE_RATE_MAX:
            score += 15
            reasons.append(f"등락률 {change_rate:.1f}%")
        elif 0 < change_rate < CHANGE_RATE_MIN:
            score += 6
            reasons.append(f"완만 상승 {change_rate:.1f}%")

        # 3. 52주 신고가 근접 (5% 이내)
        if w52_hgpr > 0 and price / w52_hgpr >= 0.95:
            score += 8
            reasons.append("52주 신고가 근접")

        # 4. 52주 저점 대비 상승 모멘텀 (저점 대비 20% 이상 반등)
        if w52_lwpr > 0 and price / w52_lwpr >= 1.20:
            score += 7
            reasons.append(f"저점 대비 +{(price/w52_lwpr-1)*100:.0f}%")

        # 5. PER 적정 (0 < PER < 30)
        try:
            per_val = float(per)
            if 0 < per_val < 30:
                score += 5
                reasons.append(f"PER {per_val:.1f}")
        except (ValueError, TypeError):
            pass

        # 목표가 / 손절가 / 보유 기간 계산
        target1    = round(price * (1 + TARGET_RATE_1))
        target2    = round(price * (1 + TARGET_RATE_2))
        stop       = round(price * (1 - STOP_LOSS_RATE))

        # 보유 기간: 점수에 따라 단타 or 스윙
        if score >= 60:
            hold_days  = 3
            hold_label = "스윙 (3일)"
        elif score >= 50:
            hold_days  = 1
            hold_label = "단타+1일"
        else:
            hold_days  = 0
            hold_label = "당일 단타"

        hold_until = (datetime.date.today() + datetime.timedelta(days=hold_days)).strftime("%Y-%m-%d")

        return {
            "code":               code,
            "name":               name,
            "score":              score,
            "reasons":            " / ".join(reasons),
            "price":              price,
            "target1":            target1,
            "target2":            target2,
            "stop":               stop,
            "hold_label":         hold_label,
            "hold_until":         hold_until,
            "entry_signal_time":  now_str(),
        }

    except Exception as e:
        log(f"  [WARN] {code} 분석 오류: {e}")
        return None


def run_screening(preopen_mode: bool = False) -> list:
    """
    거래량 상위 + 등락률 상위 종목을 합산 스크리닝.
    점수 상위 MAX_STOCKS개 반환.
    """
    log("=" * 55)
    mode_label = "장전관찰" if preopen_mode else "장중"
    log(f"▶ 스크리닝 시작 [{market_label(current_market)} | {mode_label}]")

    try:
        candidates = api.get_screening_candidates(current_market)
    except Exception as e:
        log(f"  [ERROR] 스크리닝 후보 수집 실패: {e}")
        log("  [GUIDE] API 인증/권한 상태를 확인하세요. (APP_KEY, APP_SECRET, 모의/실전 권한)")
        return []
    if current_market == "US" and not candidates:
        log("  [WARN] 미장 후보 수집 0건 — KIS/공개시세 응답 실패 또는 프록시/권한 이슈일 수 있습니다.")
    original_count = len(candidates)
    if current_market == "KR" and original_count > SCREENING_CANDIDATE_LIMIT:
        candidates = candidates[:SCREENING_CANDIDATE_LIMIT]
        log(f"  후보 종목 수: {original_count}개 -> 분석 {len(candidates)}개로 제한")
    else:
        log(f"  후보 종목 수: {len(candidates)}개 — 개별 분석 중...")

    all_results = []
    step_sleep = max(0.0, float(SCREENING_STEP_SLEEP_SEC))
    for item in candidates:
        code = item.get("code", "")
        name = item.get("name", code)
        change_rate = safe_float(item.get("change_rate", 0))
        r = score_stock(
            code,
            name,
            change_rate,
            current_market,
            aggressive_relax_factor=1.0,
            allow_keyword_relax=False,
            preopen_mode=preopen_mode,
        )
        if r:
            all_results.append(r)
        if step_sleep > 0:
            time.sleep(step_sleep)

    if AGGRESSIVE_SCREENING and current_market == "KR" and not all_results and candidates:
        log("  [완화 재시도] 점심/유동성 구간으로 기준을 2차 완화합니다...")
        for item in candidates:
            code = item.get("code", "")
            name = item.get("name", code)
            change_rate = safe_float(item.get("change_rate", 0))
            r = score_stock(
                code,
                name,
                change_rate,
                current_market,
                aggressive_relax_factor=SCREENING_EMERGENCY_RELAX_FACTOR,
                allow_keyword_relax=False,
                preopen_mode=preopen_mode,
            )
            if r:
                all_results.append(r)
            if step_sleep > 0:
                time.sleep(step_sleep)

    if AGGRESSIVE_SCREENING and current_market == "KR" and not all_results and candidates and SCREENING_ALLOW_KEYWORD_RELAX_IF_EMPTY:
        log("  [최후 대체] 키워드 제외를 임시 해제해 대체 후보를 탐색합니다...")
        for item in candidates:
            code = item.get("code", "")
            name = item.get("name", code)
            change_rate = safe_float(item.get("change_rate", 0))
            r = score_stock(
                code,
                name,
                change_rate,
                current_market,
                aggressive_relax_factor=SCREENING_EMERGENCY_RELAX_FACTOR,
                allow_keyword_relax=True,
                preopen_mode=preopen_mode,
            )
            if r:
                all_results.append(r)
            if step_sleep > 0:
                time.sleep(step_sleep)

    all_results.sort(key=lambda x: x["score"], reverse=True)
    display_threshold = max(1, int(DISPLAY_SCORE_THRESHOLD))
    results = [r for r in all_results if r["score"] >= display_threshold]
    used_threshold = display_threshold

    result_count = max(1, int(SCREENING_RESULT_COUNT))
    log(f"\n{'─'*55}")
    log(f"  ★ 최종 추천 종목 (상위 {result_count}개)")
    log(f"{'─'*55}")
    if AGGRESSIVE_SCREENING and current_market == "KR":
        min_change, min_vol_tnrt, min_trading_value = _aggressive_screening_thresholds(1.0)
        log(
            "  [공격형 필터] "
            f"등락률>={min_change:.1f}% / "
            f"회전율>={min_vol_tnrt:.0f}% / "
            f"거래대금>={min_trading_value:,}원 / "
            f"완화:{'ON' if SCREENING_RELAX_ENABLED else 'OFF'}"
        )
    top_results = results[:result_count]
    if not top_results:
        log(f"  조건 통과 종목이 없습니다. ({display_threshold}점 이상 없음)")

    for i, r in enumerate(top_results, 1):
        log(f"  [{i}] {r['name']} ({r['code']})")
        log(f"       점수     : {r['score']}점")
        log(f"       근거     : {r['reasons']}")
        log(f"       진입가   : {r['price']:,}원  ({r['entry_signal_time']} 기준)")
        log(f"       1차목표  : {r['target1']:,}원  (+{TARGET_RATE_1*100:.0f}%)")
        log(f"       2차목표  : {r['target2']:,}원  (+{TARGET_RATE_2*100:.0f}%)")
        log(f"       손절가   : {r['stop']:,}원  (-{STOP_LOSS_RATE*100:.0f}%)")
        log(f"       보유기간 : {r['hold_label']}  (~{r['hold_until']})")
        log("")
    log(f"{'─'*55}\n")

    return top_results


# ── 매수 ──────────────────────────────────────────────────

def execute_buy(candidates: list):
    """후보 종목 매수 실행"""
    for r in candidates:
        try:
            code = r["code"]
            blocked, reason = _is_daily_reentry_blocked(code)
            if blocked:
                log(f"[SKIP] {r['name']} 재진입 금지: {reason}")
                continue
            if code in portfolio:
                info = portfolio[code]
                ok_add, reason = should_add_to_position(info, r)
                if not ok_add:
                    log(f"[SKIP] {r['name']} 추가매수 불가: {reason}")
                    continue

                price = r["price"]
                add_buy_pct = BUY_PCT * ADD_ON_BUY_PCT_MULTIPLIER
                order_amount, available_cash = calculate_order_amount(code, price, current_market, buy_pct=add_buy_pct)
                if available_cash <= 0 or order_amount < price:
                    log(
                        f"[SKIP] {r['name']} 추가매수 금액 부족 "
                        f"(주문가능:{available_cash:,}원, 산출:{order_amount:,}원, 현재가:{price:,}원)"
                    )
                    continue

                qty = max(1, order_amount // price)
                log(
                    f"[ADD PLAN] {r['name']} 점수:{r['score']} | 모멘텀:{safe_float(r.get('change_rate', 0)):.2f}% | "
                    f"주문금액:{order_amount:,}원 | 수량:{qty}주"
                )
                result = api.buy_market_order_by_market(code, qty, current_market)
                if result.get("rt_cd") != "0":
                    log(f"[ADD BUY ✗] {r['name']} 추가매수 실패: {result.get('msg1','')}")
                    continue

                prev_qty = info["qty"]
                prev_avg = info["avg_price"]
                new_qty = prev_qty + qty
                new_avg = round((prev_avg * prev_qty + price * qty) / new_qty)
                info["qty"] = new_qty
                info["avg_price"] = new_avg
                info["target1"] = round(new_avg * (1 + TARGET_RATE_1))
                info["target2"] = round(new_avg * (1 + TARGET_RATE_2))
                if info.get("averaged_down", False):
                    info["stop"] = round(new_avg * (1 - POST_DCA_STOP_LOSS_RATE))
                else:
                    info["stop"] = round(new_avg * (1 - STOP_LOSS_RATE))
                info["sold_half"] = False
                info["add_buy_count"] = int(info.get("add_buy_count", 0)) + 1
                info["last_buy_ts"] = time.time()

                log(
                    f"[ADD BUY ✓] [{market_label(current_market)}] {r['name']} {qty}주 @ {price:,}원 | "
                    f"평단:{prev_avg:,} -> {new_avg:,}"
                )
                notify_buy_event(r["name"], code, qty, price)
                time.sleep(0.3)
                continue
            if len(portfolio) >= MAX_STOCKS:
                log("[SKIP] 최대 보유 종목 수 도달")
                break

            price = r["price"]
            order_amount, available_cash = calculate_order_amount(code, price, current_market)
            if available_cash <= 0:
                log(f"[SKIP] {r['name']} 주문 가능 현금 조회 실패/부족")
                continue

            if order_amount < price:
                log(
                    f"[SKIP] {r['name']} 주문금액 부족 "
                    f"(주문가능:{available_cash:,}원, 산출:{order_amount:,}원, 현재가:{price:,}원, "
                    f"현금최소유지:{MIN_CASH_RATIO*100:.0f}%)"
                )
                continue

            qty = max(1, order_amount // price)
            log(
                f"[BUY PLAN] {r['name']} 주문가능:{available_cash:,}원 | "
                f"비율:{BUY_PCT*100:.1f}% | 주문금액:{order_amount:,}원 | 수량:{qty}주"
            )

            result = api.buy_market_order_by_market(code, qty, current_market)
            if result.get("rt_cd") == "0":
                portfolio[code] = {
                    "market":     current_market,
                    "name":       r["name"],
                    "qty":        qty,
                    "avg_price":  price,
                    "target1":    r["target1"],
                    "target2":    r["target2"],
                    "stop":       r["stop"],
                    "sold_half":  False,
                    "target1_alerted": False,
                    "target2_alerted": False,
                    "stop_alerted": False,
                    "averaged_down": False,
                    "stop_breach_count": 0,
                    "entry_time": now_str(),
                    "entry_ts":   time.time(),
                    "last_buy_ts": time.time(),
                    "add_buy_count": 0,
                    "hold_until": r["hold_until"],
                }
                log(f"[BUY ✓] [{market_label(current_market)}] {r['name']} {qty}주 @ {price:,}원")
                notify_buy_event(r["name"], code, qty, price)
            else:
                log(f"[BUY ✗] {r['name']} 매수 실패: {result.get('msg1','')}")

            time.sleep(0.3)
        except Exception as e:
            log(f"[ERROR] 매수 처리 실패 ({r.get('name', 'UNKNOWN')}): {e}")
            continue


# ── 매도 로직 ─────────────────────────────────────────────

def check_and_sell():
    """보유 종목 수익률 체크 → 목표가/손절 도달 시 매도"""
    sync_portfolio_with_account()
    if not portfolio:
        return

    for code, info in list(portfolio.items()):
        try:
            market      = info.get("market", current_market)
            detail      = _get_price_detail_cached(code, market)
            cur_price   = int(detail.get("stck_prpr", 0))
            if cur_price <= 0:
                continue

            avg         = info["avg_price"]
            profit_rate = (cur_price - avg) / avg * 100
            qty         = info["qty"]
            name        = info["name"]

            log(f"  {name}({code}) | 현재:{cur_price:,}원 | 수익률:{profit_rate:+.2f}%")

            # 손절
            if cur_price <= info["stop"]:
                if not info.get("stop_alerted", False):
                    _send_stop_recommendation(name, code, qty, cur_price, info["stop"])
                    info["stop_alerted"] = True
                info["stop_breach_count"] = info.get("stop_breach_count", 0) + 1
                if info["stop_breach_count"] < STOP_BREACH_CONFIRM_COUNT:
                    log(
                        f"  ⏳ 손절 하회 확인중 — {name} "
                        f"({info['stop_breach_count']}/{STOP_BREACH_CONFIRM_COUNT})"
                    )
                    continue

                if not info.get("averaged_down", False):
                    log(f"  ⚠ 손절 구간 진입 — {name} 물타기 시도")
                    dca_done = execute_average_down(code, info, cur_price, detail)
                    if not dca_done:
                        log(f"  ⛔ 물타기 실패로 손절 전환 — {name} {qty}주 @ {cur_price:,}원")
                        result = api.sell_market_order_by_market(code, qty, market)
                        if result.get("rt_cd") == "0":
                            portfolio.pop(code, None)
                            notify_sell_event("손절", name, code, qty, cur_price, avg, market=market)
                        else:
                            log(f"  [SELL ✗] {name} 손절 매도 실패: {result.get('msg1', '')}")
                else:
                    log(f"  ⛔ 물타기 후 손절 — {name} {qty}주 @ {cur_price:,}원")
                    result = api.sell_market_order_by_market(code, qty, market)
                    if result.get("rt_cd") == "0":
                        portfolio.pop(code, None)
                        notify_sell_event("손절", name, code, qty, cur_price, avg, market=market)
                    else:
                        log(f"  [SELL ✗] {name} 손절 매도 실패: {result.get('msg1', '')}")

            # 2차 목표가 달성 → 전량 매도
            elif cur_price >= info["target2"]:
                info["stop_breach_count"] = 0
                if not info.get("target2_alerted", False):
                    _send_target_recommendation("2차", name, code, cur_price, info["target2"])
                    info["target2_alerted"] = True
                log(f"  🎯 2차목표 달성 — {name} {qty}주 전량 매도")
                result = api.sell_market_order_by_market(code, qty, market)
                if result.get("rt_cd") == "0":
                    portfolio.pop(code, None)
                    notify_sell_event("2차목표", name, code, qty, cur_price, avg, market=market)
                else:
                    log(f"  [SELL ✗] {name} 2차목표 매도 실패: {result.get('msg1', '')}")

            # 1차 목표가 달성 → 절반 매도 (아직 안 팔았을 때)
            elif cur_price >= info["target1"] and not info["sold_half"]:
                info["stop_breach_count"] = 0
                if not info.get("target1_alerted", False):
                    _send_target_recommendation("1차", name, code, cur_price, info["target1"])
                    info["target1_alerted"] = True
                half = max(1, qty // 2)
                log(f"  ✅ 1차목표 달성 — {name} {half}주 절반 매도")
                result = api.sell_market_order_by_market(code, half, market)
                if result.get("rt_cd") == "0":
                    info["qty"] = qty - half
                    info["sold_half"] = True
                    notify_sell_event("1차목표", name, code, half, cur_price, avg, market=market)
                else:
                    log(f"  [SELL ✗] {name} 1차목표 매도 실패: {result.get('msg1', '')}")
            else:
                info["stop_breach_count"] = 0
                info["stop_alerted"] = False

        except Exception as e:
            log(f"  [WARN] {code} 체크 오류: {e}")

        time.sleep(0.1)


def force_sell_all():
    """장 마감 전 전량 강제 청산"""
    if not portfolio:
        return
    log("⚠ 강제 청산 시작")
    for code, info in list(portfolio.items()):
        try:
            market = info.get("market", current_market)
            qty = info["qty"]
            detail = _get_price_detail_cached(code, market)
            cur_price = int(detail.get("stck_prpr", 0))
            if cur_price <= 0:
                cur_price = info["avg_price"]
            result = api.sell_market_order_by_market(code, qty, market)
            if result.get("rt_cd") == "0":
                portfolio.pop(code, None)
                log(f"  강제매도[{market_label(market)}]: {info['name']} {qty}주")
                notify_sell_event("강제청산", info["name"], code, qty, cur_price, info["avg_price"], market=market)
            else:
                log(f"  [SELL ✗] {info['name']} 강제매도 실패: {result.get('msg1', '')}")
            time.sleep(0.3)
        except Exception as e:
            log(f"  [ERROR] 강제매도 처리 실패 ({info.get('name', code)}): {e}")


def show_portfolio():
    """현재 보유 종목 + 평가손익 + 3분 기준 상태 출력"""
    sync_portfolio_with_account()
    if not portfolio:
        log("현재 보유 종목이 없습니다.")
        return

    snapshots, totals = get_portfolio_snapshot()
    ref = snapshots[0]
    ref_market = portfolio.get(ref["code"], {}).get("market", current_market)
    ref_price = ref["cur_price"] if ref["cur_price"] > 0 else ref["avg_price"]
    try:
        available_cash = api.get_available_cash_by_market(ref["code"], ref_price, ref_market)
    except Exception:
        available_cash = 0
    total_asset = totals["total_eval"] + available_cash
    invested_ratio = (totals["total_eval"] / total_asset * 100) if total_asset > 0 else 0.0
    cash_ratio = (available_cash / total_asset * 100) if total_asset > 0 else 0.0
    max_risk_to_stop = 0

    log(f"현재 보유 종목 {len(snapshots)}개")
    for s in snapshots:
        market = portfolio.get(s["code"], {}).get("market", current_market)
        base = (
            f"  - [{market_label(market)}] {s['name']}({s['code']}) | 수량:{s['qty']}주 | "
            f"평단:{s['avg_price']:,}원 | 현재:{s['cur_price']:,}원 | "
            f"평가손익:{s['pnl_amount']:+,}원 ({s['pnl_rate']:+.2f}%)"
        )
        if not s["price_ok"]:
            log(base + " | 현재가 조회 실패")
            continue

        if s["is_3m_ready"]:
            log(base + f" | 3분기준:{s['pnl_rate']:+.2f}%")
        else:
            remain = format_elapsed(s["remain_3m_sec"])
            log(base + f" | 3분기준 대기:{remain} 남음")

        stop_gap_pct = ((s["cur_price"] - s["stop"]) / s["cur_price"] * 100) if s["cur_price"] > 0 else 0.0
        target1_gap_pct = ((s["target1"] - s["cur_price"]) / s["cur_price"] * 100) if s["cur_price"] > 0 else 0.0
        risk_amount = max(0, s["cur_price"] - s["stop"]) * s["qty"]
        max_risk_to_stop += risk_amount

        log(
            f"      목표/손절: 1차 {s['target1']:,}원 | "
            f"2차 {s['target2']:,}원 | 손절 {s['stop']:,}원 | "
            f"손절거리:{stop_gap_pct:.2f}% | 1차목표까지:{target1_gap_pct:+.2f}%"
        )

    log(
        f"  현금상태 | 주문가능:{available_cash:,}원 | "
        f"현금비중:{cash_ratio:.1f}% | 투자비중:{invested_ratio:.1f}%"
    )
    log(
        f"  리스크상태 | 손절 도달 시 추가감소 가능액(추정): {max_risk_to_stop:,}원"
    )
    log(
        f"  합계 | 매입:{totals['total_cost']:,}원 | 평가:{totals['total_eval']:,}원 | "
        f"손익:{totals['total_pnl']:+,}원 ({totals['total_pnl_rate']:+.2f}%)"
    )


def print_menu():
    print("\n" + "=" * 55)
    print(f" KIS 급등주 자동매매 봇 - 수동 실행 메뉴 [{market_label(current_market)}]")
    print("=" * 55)
    print("1) 국장 자동모드 (08:00 관찰, 09:00 이후 32점 자동매수, 3초 주기)")
    print("2) 국장 자동 스크리닝만 실행 (3초 주기)")
    print("3) 스크리닝 결과에서 선택 매수")
    print("4) 보유 종목 점검 및 조건 매도")
    print("5) 보유 종목 상태 보기")
    print("6) 전량 강제 매도")
    print("9) 종료")
    print("=" * 55)


def select_market_for_screening() -> bool:
    """스크리닝 직전 시장 선택"""
    global current_market, last_screened

    print("\n[시장 선택]")
    print("1) 국장 (KR)")
    print("2) 미장 (US)")
    choice = input("선택 번호: ").strip()
    selected_market = "KR" if choice == "1" else "US" if choice == "2" else ""
    if not selected_market:
        log("올바른 번호를 입력하세요.")
        return False

    if portfolio and selected_market != current_market:
        log("보유 종목이 있을 때는 시장을 변경할 수 없습니다. 먼저 청산하세요.")
        return False

    # 시작 시 사용한 설정 모듈(예: config_acc2)은 계좌 정보의 기준점으로 유지한다.
    # 필요 시 {base}_us 같은 분리 모듈을 우선 적용하고, 없으면 base 모듈을 그대로 사용.
    base_module = STARTUP_CFG_MODULE
    if base_module == "config":
        target_module = "config" if selected_market == "KR" else "config_us"
    else:
        preferred_us_module = f"{base_module}_us"
        if selected_market == "US" and importlib.util.find_spec(preferred_us_module):
            target_module = preferred_us_module
        else:
            target_module = base_module

    try:
        if target_module != CURRENT_CFG_MODULE:
            apply_runtime_config(target_module)
    except Exception:
        # 분리 설정 파일 로딩 실패 시 시작 설정으로 롤백
        if CURRENT_CFG_MODULE != base_module:
            apply_runtime_config(base_module)

    current_market = selected_market
    last_screened = []
    log(f"시장 선택 완료: {market_label(current_market)}")
    return True


def run_auto_kr_screening_and_buy_loop():
    """국장 자동 스크리닝 + 자동 매수 루프"""
    global current_market, last_screened

    selected_market = "KR"
    if portfolio and selected_market != current_market:
        log("보유 종목이 있을 때는 시장을 변경할 수 없습니다. 먼저 청산하세요.")
        return

    base_module = STARTUP_CFG_MODULE
    target_module = "config" if base_module == "config" else base_module
    try:
        if target_module != CURRENT_CFG_MODULE:
            apply_runtime_config(target_module)
    except Exception:
        if CURRENT_CFG_MODULE != base_module:
            apply_runtime_config(base_module)

    current_market = "KR"
    last_screened = []
    interval_sec = max(3, int(AUTO_SCREEN_INTERVAL_SEC))
    score_interval_sec = max(3, int(PORTFOLIO_SCORE_INTERVAL_SEC))
    log(
        f"국장 자동 스크리닝 모드 시작 "
        f"(장전관찰:{PREMARKET_START}~{MARKET_OPEN}, 주기 {interval_sec}초, 매수기준 {SCORE_THRESHOLD}점)"
    )
    _send_telegram_message(
        f"🤖 자동 스크리닝 시작\n시장: 국장\n장전관찰: {PREMARKET_START}~{MARKET_OPEN}\n"
        f"주기: {interval_sec}초\n자동매수 기준: {SCORE_THRESHOLD}점 이상(09:00 이후)"
    )

    def log_realtime_portfolio_scores():
        sync_portfolio_with_account()
        if not portfolio:
            return
        log(f"📊 실시간 점수 업데이트 ({score_interval_sec}초)")
        for code, info in list(portfolio.items()):
            name = info.get("name", code)
            market = info.get("market", current_market)
            try:
                detail = _get_price_detail_cached(code, market)
                change_rate = safe_float(detail.get("prdy_ctrt", 0))
                cur_price = safe_int(detail.get("stck_prpr", 0), int(info.get("avg_price", 0)))
                scored = score_stock(
                    code,
                    name,
                    change_rate,
                    market,
                    aggressive_relax_factor=1.0,
                    allow_keyword_relax=True,
                    skip_entry_filters=True,
                )
                if not scored:
                    log(f"  - {name}({code}) | 점수 계산 불가 | 현재가:{cur_price:,}원")
                    continue
                score = int(scored.get("score", 0))
                delta = score - int(SCORE_THRESHOLD)
                log(
                    f"  - {name}({code}) | 점수:{score}점 ({delta:+d}) | "
                    f"현재가:{cur_price:,}원 | 등락률:{change_rate:+.2f}%"
                )
            except Exception as e:
                log(f"  - {name}({code}) 점수 계산 오류: {e}")
            time.sleep(0.03)

    stop_event = threading.Event()

    def score_worker():
        while not stop_event.is_set():
            try:
                log_realtime_portfolio_scores()
            except Exception as e:
                log(f"[WARN] 실시간 점수 업데이트 오류: {e}")
            if stop_event.wait(score_interval_sec):
                break

    def screening_worker():
        global last_screened
        next_run_ts = time.time()
        phase = ""
        while not stop_event.is_set():
            now_ts = time.time()
            wait_sec = max(0.0, next_run_ts - now_ts)
            if stop_event.wait(wait_sec):
                break

            started_ts = time.time()
            try:
                now_dt = datetime.datetime.now()
                if _is_kr_premarket_observe_time(now_dt):
                    if phase != "PREOPEN":
                        log(f"🕗 장전 관찰 모드 진입 ({PREMARKET_START}~{MARKET_OPEN}) — 스크리닝만 수행")
                        phase = "PREOPEN"
                    last_screened = run_screening(preopen_mode=True)
                    top = last_screened[0] if last_screened else None
                    if top:
                        log(f"장전 상위 후보: {top['name']}({top['code']}) {top['score']}점")
                    else:
                        log("장전 후보 없음")
                elif _is_kr_market_open(now_dt):
                    if phase != "OPEN":
                        log(f"🟢 장중 자동매수 모드 진입 ({MARKET_OPEN} 이후)")
                        phase = "OPEN"
                    last_screened = run_screening(preopen_mode=False)
                    buy_candidates = [r for r in last_screened if int(r.get("score", 0)) >= SCORE_THRESHOLD]
                    if buy_candidates:
                        log(f"자동매수 후보 {len(buy_candidates)}개 감지 — 매수 실행")
                        execute_buy(buy_candidates)
                    else:
                        log(f"자동매수 후보 없음 (기준 {SCORE_THRESHOLD}점 이상, 계속 대기)")
                else:
                    if phase != "CLOSED":
                        log("시장 외 시간 — 자동매수 대기")
                        phase = "CLOSED"
            except Exception as e:
                log(f"[WARN] 자동 스크리닝 처리 오류: {e}")

            next_run_ts = started_ts + interval_sec
            remain = max(0, int(next_run_ts - time.time()))
            log(f"다음 자동 스크리닝까지 {remain}초")

    try:
        score_thread = threading.Thread(target=score_worker, daemon=True)
        screening_thread = threading.Thread(target=screening_worker, daemon=True)
        score_thread.start()
        screening_thread.start()

        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        stop_event.set()
        time.sleep(0.2)
        log("국장 자동 스크리닝 모드 중단")
        _send_telegram_message("⏹ 자동 스크리닝이 중단되었습니다.")
        return


def run_auto_kr_screening_only_loop():
    """국장 자동 스크리닝 전용 루프 (자동매수 없음)"""
    global current_market, last_screened

    selected_market = "KR"
    if portfolio and selected_market != current_market:
        log("보유 종목이 있을 때는 시장을 변경할 수 없습니다. 먼저 청산하세요.")
        return

    base_module = STARTUP_CFG_MODULE
    target_module = "config" if base_module == "config" else base_module
    try:
        if target_module != CURRENT_CFG_MODULE:
            apply_runtime_config(target_module)
    except Exception:
        if CURRENT_CFG_MODULE != base_module:
            apply_runtime_config(base_module)

    current_market = "KR"
    interval_sec = max(3, int(AUTO_SCREEN_INTERVAL_SEC))
    log(f"국장 자동 스크리닝(매수 없음) 시작 (주기 {interval_sec}초)")

    try:
        while True:
            last_screened = run_screening()
            log(f"다음 스크리닝까지 {interval_sec}초 대기...")
            time.sleep(interval_sec)
    except KeyboardInterrupt:
        log("국장 자동 스크리닝(매수 없음) 모드 중단")
        return


def buy_from_last_screened_selection():
    """최근 스크리닝 결과에서 선택 매수"""
    global last_screened
    if not last_screened:
        log("최근 스크리닝 결과가 없습니다. 먼저 2번(스크리닝만 실행)을 사용하세요.")
        return

    print("\n[선택 매수] 최근 스크리닝 종목")
    for i, r in enumerate(last_screened, 1):
        print(f"{i}) {r['name']}({r['code']}) | 점수:{r['score']} | 현재가:{r['price']:,}원")

    raw = input("매수할 번호 입력 (예: 1 또는 1,3): ").strip()
    if not raw:
        log("입력이 비어 있어 선택 매수를 취소합니다.")
        return

    picked = []
    seen = set()
    for token in raw.split(","):
        s = token.strip()
        if not s:
            continue
        if not s.isdigit():
            log(f"잘못된 입력 '{s}' — 숫자만 입력하세요.")
            continue
        idx = int(s)
        if idx < 1 or idx > len(last_screened):
            log(f"번호 {idx}는 범위를 벗어났습니다.")
            continue
        if idx in seen:
            continue
        seen.add(idx)
        picked.append(last_screened[idx - 1])

    if not picked:
        log("유효한 선택이 없어 매수를 진행하지 않습니다.")
        return

    log(f"선택 매수 실행: {len(picked)}개 종목")
    execute_buy(picked)


# ── 메인 루프 ─────────────────────────────────────────────

def main():
    log("=" * 55)
    log("  KIS 급등주 자동매매 봇 시작 (수동 메뉴 모드)")
    log(f"  모드: {'모의투자' if IS_VIRTUAL else '실전투자'}")
    log(f"  시장: {market_label(current_market)}")
    log("=" * 55)

    global last_screened
    sync_portfolio_with_account()
    if TELEGRAM_NOTIFY_ENABLED:
        notifier = threading.Thread(target=telegram_status_notifier_loop, daemon=True)
        notifier.start()
        command_listener = threading.Thread(target=telegram_command_listener_loop, daemon=True)
        command_listener.start()

    while True:
        print_menu()
        choice = input("메뉴 번호를 선택하세요: ").strip()

        if choice == "1":
            run_auto_kr_screening_and_buy_loop()

        elif choice == "2":
            run_auto_kr_screening_only_loop()

        elif choice == "3":
            buy_from_last_screened_selection()

        elif choice == "4":
            log(f"── 보유 종목 점검 ({len(portfolio)}개) ──")
            check_and_sell()

        elif choice == "5":
            show_portfolio()

        elif choice == "6":
            force_sell_all()

        elif choice == "9":
            if portfolio:
                confirm = input("보유 종목이 있습니다. 종료 전에 전량 매도할까요? (y/N): ").strip().lower()
                if confirm == "y":
                    force_sell_all()
            log("프로그램을 종료합니다.")
            break

        else:
            log("올바른 메뉴 번호를 입력하세요.")

        if choice != "9":
            input("\n엔터를 누르면 메뉴로 돌아갑니다...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("\n사용자 중단 감지")
        if SELL_ON_INTERRUPT:
            log("설정값에 따라 잔여 포지션 강제 청산을 실행합니다...")
            force_sell_all()
            log("종료 완료.")
        else:
            log("강제 청산 없이 종료합니다. (포지션은 계좌에 그대로 유지)")
        sys.exit(0)
