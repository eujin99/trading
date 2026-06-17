from __future__ import annotations

from typing import Callable

import requests

from config import Settings


class TelegramNotifier:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.handlers: dict[str, Callable[[str], str]] = {}

    def bind_handler(self, command: str, handler: Callable[[str], str]) -> None:
        self.handlers[command] = handler

    def send(self, message: str) -> None:
        if not self.settings.telegram_enabled:
            return
        if not self.settings.telegram_bot_token or not self.settings.telegram_chat_id:
            return
        url = f"https://api.telegram.org/bot{self.settings.telegram_bot_token}/sendMessage"
        try:
            requests.post(
                url,
                json={"chat_id": self.settings.telegram_chat_id, "text": message, "disable_web_page_preview": True},
                timeout=10,
            )
        except Exception:
            pass

    def parse_command(self, text: str) -> tuple[str, str]:
        raw = str(text).strip()
        if not raw.startswith("/"):
            return "", raw
        parts = raw.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""
        return cmd, arg

    def handle(self, text: str) -> str:
        cmd, arg = self.parse_command(text)
        if not cmd:
            return ""
        fn = self.handlers.get(cmd)
        if not fn:
            return "지원하지 않는 명령입니다."
        try:
            return fn(arg)
        except Exception as e:
            return f"명령 처리 실패: {e}"
