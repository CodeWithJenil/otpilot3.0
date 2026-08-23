"""Short-lived in-memory OTP cache."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from otpilot.domain.models import OtpResult


@dataclass(slots=True)
class CacheEntry:
    result: OtpResult
    expires_at: datetime


class InMemoryOtpCache:
    def __init__(self) -> None:
        self._entries: dict[str, CacheEntry] = {}

    def get(self, key: str) -> OtpResult | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        if entry.expires_at <= datetime.now(UTC):
            self._entries.pop(key, None)
            return None
        return entry.result

    def put(self, key: str, result: OtpResult, ttl_seconds: int) -> None:
        self._entries[key] = CacheEntry(
            result=result,
            expires_at=datetime.now(UTC) + timedelta(seconds=ttl_seconds),
        )

