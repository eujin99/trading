from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CircuitBreakerState:
    api_errors: int = 0
    order_failures: int = 0
    paused: bool = False
    reason: str = ""


class CircuitBreaker:
    def __init__(self, api_error_limit: int, order_fail_limit: int):
        self.api_error_limit = api_error_limit
        self.order_fail_limit = order_fail_limit
        self.state = CircuitBreakerState()

    def record_api_error(self, reason: str) -> None:
        self.state.api_errors += 1
        if self.state.api_errors >= self.api_error_limit:
            self.pause(f"API 오류 누적: {reason}")

    def record_order_failure(self, reason: str) -> None:
        self.state.order_failures += 1
        if self.state.order_failures >= self.order_fail_limit:
            self.pause(f"주문 실패 누적: {reason}")

    def record_success(self) -> None:
        self.state.api_errors = 0
        self.state.order_failures = 0

    def pause(self, reason: str) -> None:
        self.state.paused = True
        self.state.reason = reason

    def resume(self) -> None:
        self.state = CircuitBreakerState()

    def can_open_new_position(self) -> tuple[bool, str]:
        if self.state.paused:
            return False, self.state.reason or "리스크 차단 상태"
        return True, ""
