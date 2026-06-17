from config import *  # noqa: F401,F403

# ============================================================
# 후니 전용 오버라이드
# - 전략 파라미터는 config.py 값을 그대로 사용
# - 아래 인증/계좌/텔레그램만 계좌2 값으로 바꿔서 사용
# ============================================================

APP_KEY = resolve_secret(
    "APP_KEY_ACC2",
    "ENC(v1.z4lIvJQOwjdehaWxgl35uw.4ZRen5dmu-YdnC-kUXIjgw.yxJlW0CqSWM-ASH7iRXZCTXz6o2rOXA_8wDJVWGPifUQAQP3.yg-UlD0V3w4IXz73nQXur6bYwzr4UO8Aa48O3H7MAQk)",
)
APP_SECRET = resolve_secret(
    "APP_SECRET_ACC2",
    "ENC(v1.0yQ76lXQM_9BjCCB_0SSaQ.P1oGlcBPxZg6smTBeIPAKA.vW0lfRk5Q5VCzd1GXw8YH2lpjKJXL5w6kp8-t6Yn8iJ8sfEkInztbveE_x_NF090mpIIpEB7_HMDJInmF60oWo3H9XhEmJD06p3JoNLMHQG8stwSKpcQTmV6I_86FAOTVo4CyH3NOB8O6SaoxuUUTI34Bp26V3C5F1vEw5Wxj5nKF8-YqZofGn2F_FtIiFeOoDsSEgfinSEl1g9XtxtezYkB3Q9E6mGw8JJL5QlvIAQJLRoD.exBWFYo_OEVUcpuBLUcu4OjDYBciWvGegEG6H5ITx_Y)",
)
ACCOUNT_NO = resolve_secret(
    "ACCOUNT_NO_ACC2",
    "ENC(v1.oNyUzZkl0Eh6GNpgVSFRzA.f_Eep6UpvFOqKNsavOakgg.zI7mRp197wwnBA0.By-dUKjBvU0iChN3pVC8jgiQxyWtawBPvjBKWotIhJo)",
)  # 예: 50123456-01

# 모의/실전 계좌2 설정
IS_VIRTUAL = False
if IS_VIRTUAL:
    BASE_URL = "https://openapivts.koreainvestment.com:29443"
else:
    BASE_URL = "https://openapi.koreainvestment.com:9443"

# 계좌2 텔레그램(다른 봇/채팅방 권장)
TELEGRAM_NOTIFY_ENABLED = True
TELEGRAM_BOT_TOKEN = resolve_secret(
    "TELEGRAM_BOT_TOKEN_ACC2",
    "ENC(v1.u30xmEHGurbJFCCljy_S8A.WgwdEehPj4_GDaL0mr64nA.0IQpQRmI5xJP0KSLUU3YrQcZnYmhaZwXH8NNyHn6IXwYEUo7aHjnpffdMmjUWw.9EaBkGKbkB3X-f5UpMMED-ltjYHbgbv2J19iGfIamL0)",
)
TELEGRAM_CHAT_ID = resolve_secret(
    "TELEGRAM_CHAT_ID_ACC2",
    "ENC(v1.IyrScJVKpQlbWOZKrUG1ZQ.Kvp2V01WI4l0GRrhRrixxw.t1FXwj1_5H6FbQ.xcJFp9Il2ZXVzXHot23rNdBX6s0rprkRGQcfh7cxIpM)",
)
