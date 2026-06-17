# ============================================================
# config.py — 환경변수 기반 설정 파일
# ============================================================

import os


# 민감정보는 코드에 넣지 않고 환경변수로만 주입한다.
APP_KEY = os.getenv("APP_KEY", "").strip()
APP_SECRET = os.getenv("APP_SECRET", "").strip()
ACCOUNT_NO = os.getenv("ACCOUNT_NO", "").strip()  # 예: 50123456-01

# 모의투자 = True / 실전투자 = False
IS_VIRTUAL = True

# 도메인 자동 선택
if IS_VIRTUAL:
    BASE_URL = "https://openapivts.koreainvestment.com:29443"
else:
    BASE_URL = "https://openapi.koreainvestment.com:9443"

# ── 매매 파라미터 ──────────────────────────────────────────
MAX_STOCKS        = 3        # 동시 보유 최대 종목 수
BUY_PCT           = 0.05     # 종목당 매수 비율 (보수적)
BUY_MIN_AMOUNT    = 300000   # 종목당 최소 매수 금액 (원)
BUY_MAX_AMOUNT    = 1500000  # 종목당 최대 매수 금액 (원)
MIN_CASH_RATIO    = 0.35     # 최소 현금 비중 (35% 이상 유지)
ADD_ON_ENABLED    = False    # 손실 구간 물타기 금지
ADD_ON_MIN_SCORE  = 38       # 추가매수 최소 점수
ADD_ON_MAX_PER_STOCK = 2     # 종목당 추가매수 최대 횟수
ADD_ON_COOLDOWN_SEC = 600    # 추가매수 최소 간격(초)
ADD_ON_MIN_PROFIT_RATE = -1.5  # 추가매수 허용 최소 수익률(%)
ADD_ON_MAX_CHASE_RATE = 6.0     # 추가매수 허용 최대 추격 수익률(%)
ADD_ON_MIN_MOMENTUM_RATE = 0.3  # 추가매수 최소 모멘텀(%)
ADD_ON_BUY_PCT_MULTIPLIER = 0.7 # 추가매수 시 기본 BUY_PCT 배수
TARGET_RATE_1     = 0.05     # 1차 목표 수익률 (5%)
TARGET_RATE_2     = 0.10     # 2차 목표 수익률 (10%)
STOP_LOSS_RATE    = 0.03     # 손절 비율 (3%)
POST_DCA_STOP_LOSS_RATE = 0.02  # 물타기 후 손절 비율 (2%)
DCA_MIN_VOL_TNRT  = 120.0    # 물타기 최소 거래량 회전율(%)
DCA_MIN_CHANGE_RATE = -5.0   # 물타기 허용 최소 등락률(%), 더 급락이면 물타기 금지
STOP_BREACH_CONFIRM_COUNT = 2  # 손절가 연속 하회 확인 횟수
VOLUME_RATIO_MIN  = 1.5      # 거래량 배율 최소 기준 (20일 평균 대비)
CHANGE_RATE_MIN   = 1.0      # 최소 등락률 (%)
CHANGE_RATE_MAX   = 25.0     # 최대 등락률 (상한가 근처 제외, %)
SCORE_THRESHOLD   = 55       # 매수 진입 최소 점수 (공격형 실험 모드)

# ── 공격형 스크리닝 필터 ───────────────────────────────────
AGGRESSIVE_SCREENING = False         # 기본(초기) 스코어링 방식 사용
SCREENING_MIN_CHANGE_RATE = 1.2      # 최소 등락률(%)
SCREENING_MIN_VOL_TNRT = 130.0       # 최소 거래량 회전율(%)
SCREENING_MIN_TRADING_VALUE = 800000000  # 최소 거래대금(원)
SCREENING_RELAX_ENABLED = True       # 기준 미달 시 자동 완화 허용 여부
SCREENING_LUNCH_RELAX_ENABLED = True
SCREENING_LUNCH_START = "11:20"
SCREENING_LUNCH_END = "13:10"
SCREENING_LUNCH_RELAX_FACTOR = 0.65   # 점심시간엔 기준을 65% 수준으로 완화
SCREENING_EMERGENCY_RELAX_FACTOR = 0.55  # 후보 0개면 2차 완화
SCREENING_ALLOW_KEYWORD_RELAX_IF_EMPTY = True  # 그래도 0개면 ETF/혼합도 임시 허용
SCREENING_EXCLUDE_KEYWORDS = [
    "ETF", "ETN", "채권", "국채", "회사채", "혼합",
    "인덱스", "KODEX", "TIGER", "RISE", "ACE", "SOL", "ARIRANG",
]

# ── 시장 선택(국장/미장) ───────────────────────────────────
DEFAULT_MARKET    = "KR"     # KR: 국장, US: 미장
US_EXCHANGE       = "NAS"    # NAS(나스닥), NYS(뉴욕), AMS(아멕스)
US_UNIVERSE       = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL",
    "META", "TSLA", "AVGO", "AMD", "NFLX",
]
SELL_ON_INTERRUPT = False    # Ctrl+C 종료 시 전량 강제매도 여부
TELEGRAM_NOTIFY_ENABLED = True     # OpenClaw 텔레그램 상태 알림 사용
TELEGRAM_NOTIFY_INTERVAL_SEC = 300  # 보유종목 상태 알림 주기(초, 5분)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()  # BotFather에서 발급받은 봇 토큰
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()  # 내 개인 chat_id (숫자)
AUTO_SCREEN_INTERVAL_SEC = 15                # 자동 스크리닝 주기(초)
PORTFOLIO_SCORE_INTERVAL_SEC = 3             # 메뉴 1 보유종목 실시간 점수 출력 주기(초)
PRICE_CACHE_TTL_SEC = 2                      # 시세 캐시 유지 시간(초)
SCREENING_SOURCE_LIMIT = 300                 # 스크리닝 원천 후보 수집 개수(거래량/등락률 각각)
SCREENING_CANDIDATE_LIMIT = 300              # 1회 스크리닝 상세분석 최대 종목 수
SCREENING_STEP_SLEEP_SEC = 0.02              # 스크리닝 분석 간 지연(초)
SCREENING_RESULT_COUNT = 50                  # 스크리닝 결과 출력/선택 대상 개수
DISPLAY_SCORE_THRESHOLD = 30                 # 화면/선택에 표시할 최소 점수
PREMARKET_START = "08:00"                    # 장전 관찰 스크리닝 시작 시각

# ── 스케줄 ────────────────────────────────────────────────
MARKET_OPEN       = "09:00"
SCREENING_TIME    = "09:05"  # 스크리닝 시작 시각
FORCE_SELL_TIME   = "15:20"  # 장 마감 전 강제 청산 시각

# ── 계좌 단위 리스크 제한(v2) ───────────────────────────────
DAILY_MAX_LOSS_PCT = 0.015           # 일일 최대 손실 -1.5%
TRADE_RISK_PCT = 0.005               # 1회 거래 최대 손실 0.5%
MAX_DAILY_TRADES = 5                 # 일일 거래 횟수 제한
MAX_CONSECUTIVE_LOSSES = 2           # 연속 손실 제한
MAX_POSITION_PCT = 0.15              # 종목당 최대 비중
MAX_TOTAL_INVEST_PCT = 0.65          # 총 투자 비중 상한
REENTRY_PER_DAY = 1                  # 동일 종목 재진입 제한
API_ERROR_LIMIT = 3                  # API 오류 누적 제한
ORDER_FAIL_LIMIT = 2                 # 주문 실패 누적 제한
FEE_RATE = 0.00015                   # 수수료율(왕복 계산에 사용)
SELL_TAX_RATE = 0.0018               # 매도세율(국내)
PARTIAL_RETRY_MAX = 1                # 부분체결 잔량 재시도 횟수(매도)
PARTIAL_RETRY_SLEEP_SEC = 0.7        # 부분체결 재시도 간격(초)
BUY_PARTIAL_RETRY_MAX = 0            # 매수 부분체결 잔량 재시도(기본 비활성)

# ── 스크리닝 하드필터(v2) ─────────────────────────────────
MAX_SPREAD_PCT = 0.8                 # 스프레드 상한(%)
MIN_TREND_SCORE = 55.0               # 분봉 추세 최소 점수
MAX_GAP_UP_PCT = 8.0                 # 갭상승 상한(%)
REQUIRE_PRICE_ABOVE_VWAP = True      # VWAP 상회 종목만 허용

# ── 손실 누적 시 비중 축소(v2) ─────────────────────────────
LOSS_STREAK_RISK_MULTIPLIER = 0.7    # 연속손실 시 리스크 축소 배수
DAILY_DRAWDOWN_RISK_MULTIPLIER = 0.5 # 일일 손실 누적 시 리스크 축소 배수
