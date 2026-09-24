"""Diagnostic result models for `otpilot doctor`."""

from collections import Counter
from dataclasses import dataclass
from enum import StrEnum

from otpilot.domain.state import RuntimeState


class CheckStatus(StrEnum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
    SKIP = "SKIP"


@dataclass(frozen=True, slots=True)
class DiagnosticCheck:
    category: str
    name: str
    status: CheckStatus
    message: str
    remediation: str | None = None


@dataclass(frozen=True, slots=True)
class DiagnosticReport:
    checks: tuple[DiagnosticCheck, ...]
    runtime: RuntimeState

    def counts(self) -> Counter[CheckStatus]:
        return Counter(check.status for check in self.checks)

    def has_failures(self) -> bool:
        return any(check.status is CheckStatus.FAIL for check in self.checks)
