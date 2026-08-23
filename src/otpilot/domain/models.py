"""Domain models shared across application services and providers."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import NewType

ProviderId = NewType("ProviderId", str)
AccountId = NewType("AccountId", str)


class ProviderKind(StrEnum):
    IMAP = "imap"
    LOCAL = "local"
    FUTURE = "future"


@dataclass(frozen=True, slots=True)
class EmailAddress:
    value: str


@dataclass(frozen=True, slots=True)
class EmailMessageRef:
    provider_id: ProviderId
    account_id: AccountId
    message_id: str
    received_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class OtpCandidate:
    value: str
    score: float
    source: EmailMessageRef
    reason: str
    expires_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class OtpResult:
    candidate: OtpCandidate
    extracted_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class ProviderDescriptor:
    provider_id: ProviderId
    display_name: str
    kind: ProviderKind
    supports_imap: bool
