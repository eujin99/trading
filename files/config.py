# ============================================================
# config.py — 설정 파일 (APP KEY / SECRET 여기에 입력)
# ============================================================

from secret_crypto import resolve_secret

# ★ 민감정보는 ENC(...) 암호문 + TRADING_MASTER_KEY 조합으로 복호화됩니다.
APP_KEY = resolve_secret(
    "APP_KEY",
    "ENC(v1.oY42LICZ6WKe4SRyYDNwEA.D_XZhLg-ZBoKfJsmQqJb1Q.khkmCi0_zDWn4mDAQZ8__NgTNSqpKCpuwDI0VMk_NfL8rnha.j5kL69IzxQ9GAQTSTqQK-jzWlz-0ZE8rqZbOAGl6zjk)",
)
APP_SECRET = resolve_secret(
    "APP_SECRET",
    "ENC(v1.dYuVqyuSi6EEpD0M6ywbPg.sN-1liFi0bGzQjwu_UaUgA.m7QMq92f4uxSbsmSXhS5Fh8LvBmJ1BfZ3unQHGRf2d8W8fXInUaH2aCkOtcAI5lYqirSkg6jJw4j7z2SdFcr3fi1IKZxwsyOr6_NgfuVbb00l17_N0NMAv7jKruDncEd2U--Rg0NPNuagLo_TJcXlqG5uE7F0LAIpbIQlpnAmzYHMIm1nfNUNGkgzSFDFZPOMqm8g2gORrT-ayJYLkfAYJLel3F2uohH6J09ZcY04T64kYCY.jTfGnkufNSwbmrKJWnN9duGyItIADKCjP4lg6dgI5vo)",
)
ACCOUNT_NO = resolve_secret(
    "ACCOUNT_NO",
    "ENC(v1.EboemOZBhJ3ZZ2idoGaCNw.VEymh3ARo0ndLCRC2okJMA.ZEnK6YmgpLTSFWk.tnC1gAmg7141x3luSbH0saQLOqlWIEgCf9MwymgOacQ)",
)  # 예: 50123456-01

# 모의투자 = True / 실전투자 = False
IS_VIRTUAL = True

# 도메인 자동 선택
if IS_VIRTUAL:
    BASE_URL = "https://openapivts.koreainvestment.com:29443"
else:
    BASE_URL = "https://openapi.koreainvestment.com:9443"

# ── 매매 파라미터 ──────────────────────────────────────────
MAX_STOCKS        = 6        # 동시 보유 최대 종목 수 (공격형)
BUY_PCT           = 0.15     # 종목당 매수 비율 (가용 현금의 15%)
BUY_MIN_AMOUNT    = 300000   # 종목당 최소 매수 금액 (원)
BUY_MAX_AMOUNT    = 1500000  # 종목당 최대 매수 금액 (원)
MIN_CASH_RATIO    = 0.10     # 최소 현금 비중 (10% 이상 유지, 공격형)
ADD_ON_ENABLED    = True     # 보유 종목 추가매수(피라미딩) 허용
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
SCORE_THRESHOLD   = 32       # 매수 진입 최소 점수

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
TELEGRAM_BOT_TOKEN = resolve_secret(
    "TELEGRAM_BOT_TOKEN",
    "ENC(v1.j5pN7GnjW7woXWU9arpnWA.tUXEOnIQp_BRc0rqBUMn2Q.ia5TIgWxnaibcpc8r8qjeyeMA36gwrEdxLe32JFFVfYwZkhs0A53Q95ttkdvJQ.gCtC5RJjdeZaxJZpOl-gVPSlIbLsZdYSfCXKrp7bnaA)",
)  # BotFather에서 발급받은 봇 토큰
TELEGRAM_CHAT_ID = resolve_secret(
    "TELEGRAM_CHAT_ID",
    "ENC(v1.4_hzmwOorQv4Da2J4QbXsA.5l5YcaUggbhkqPXXTnHK4g.hFtoYPRRoHHBbg.ixOcrQRHab_22rBD8-F2Q3upZR6Ma2iEvYPhrGtWxn0)",
)  # 내 개인 chat_id (숫자)
AUTO_SCREEN_INTERVAL_SEC = 5                 # 자동 스크리닝 주기(초)
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
