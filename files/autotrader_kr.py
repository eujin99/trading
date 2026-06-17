import os
import sys

os.environ["TRADER_CONFIG_MODULE"] = "config_kr"

import autotrader as trader


if __name__ == "__main__":
    try:
        trader.main()
    except KeyboardInterrupt:
        trader.log("\n사용자 중단 감지")
        if trader.SELL_ON_INTERRUPT:
            trader.log("설정값에 따라 잔여 포지션 강제 청산을 실행합니다...")
            trader.force_sell_all()
            trader.log("종료 완료.")
        else:
            trader.log("강제 청산 없이 종료합니다. (포지션은 계좌에 그대로 유지)")
        sys.exit(0)
