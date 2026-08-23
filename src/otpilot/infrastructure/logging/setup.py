"""Logging setup with redaction-first formatting."""

import logging
import re
from collections.abc import Mapping
from typing import Any

SECRET_PATTERNS = (
    re.compile(r"(?i)(password|app_password|token|secret|credential)=([^\\s]+)"),
)


def redact(value: str) -> str:
    redacted = value
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub(r"\1=[REDACTED]", redacted)
    return redacted


class RedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        rendered = super().format(record)
        return redact(rendered)


def configure_logging(level: int = logging.INFO, extra: Mapping[str, Any] | None = None) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(RedactingFormatter("%(levelname)s %(name)s: %(message)s"))
    logging.basicConfig(level=level, handlers=[handler], force=True)
    if extra:
        logging.getLogger("otpilot").debug("logging configured", extra=dict(extra))

