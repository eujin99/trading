from config import *  # noqa: F401,F403
import os

# ============================================================
# 후니 전용 오버라이드
# - 전략 파라미터는 config.py 값을 그대로 사용
# - 아래 인증/계좌/텔레그램만 계좌2 값으로 바꿔서 사용
# ============================================================

APP_KEY = os.getenv("APP_KEY_ACC2", "").strip()
APP_SECRET = os.getenv("APP_SECRET_ACC2", "").strip()
ACCOUNT_NO = os.getenv("ACCOUNT_NO_ACC2", "").strip()  # 예: 50123456-01

# 모의/실전 계좌2 설정
IS_VIRTUAL = False
if IS_VIRTUAL:
    BASE_URL = "https://openapivts.koreainvestment.com:29443"
else:
    BASE_URL = "https://openapi.koreainvestment.com:9443"

# 계좌2 텔레그램(다른 봇/채팅방 권장)
TELEGRAM_NOTIFY_ENABLED = True
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN_ACC2", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID_ACC2", "").strip()
