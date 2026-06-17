#!/usr/bin/env python3
import argparse
import os
import secrets

from secret_crypto import encrypt_secret


def main() -> None:
    parser = argparse.ArgumentParser(
        description="민감정보를 ENC(...) 형식 암호문으로 변환합니다."
    )
    parser.add_argument("value", nargs="?", help="암호화할 평문 값")
    parser.add_argument(
        "--new-key",
        action="store_true",
        help="새 TRADING_MASTER_KEY를 생성합니다.",
    )
    args = parser.parse_args()

    if args.new_key:
        print(f"TRADING_MASTER_KEY={secrets.token_urlsafe(48)}")
        return

    value = args.value
    if not value:
        raise SystemExit("암호화할 값을 인자로 전달하세요. 예: python encrypt_secret.py my_secret")

    master_key = os.getenv("TRADING_MASTER_KEY", "").strip()
    if not master_key:
        raise SystemExit("TRADING_MASTER_KEY 환경변수를 먼저 설정하세요.")

    encrypted = encrypt_secret(value, master_key)
    print(f"ENC({encrypted})")


if __name__ == "__main__":
    main()
