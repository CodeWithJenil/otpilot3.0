from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest

from otpilot.application.services import FetchOtpService
from otpilot.cache.memory import InMemoryOtpCache
from otpilot.config.models import AppConfig, ProviderConfig
from otpilot.domain.errors import ClipboardError
from otpilot.domain.extraction import ExtractableEmail, OtpExtractor
from otpilot.domain.models import (
    AccountId,
    EmailMessageRef,
    ProviderDescriptor,
    ProviderId,
    ProviderKind,
)
from otpilot.domain.otp import ContextOtpCandidateScorer, EmailOtpCandidateGenerator
from otpilot.domain.providers import ProviderRegistry
from otpilot.domain.search import SearchCriteria


class FakeCredentials:
    def get_app_password(self, account_id: AccountId) -> tuple[str, str] | None:
        return "user@example.com", "secret"


class FakeConfig:
    def load(self) -> AppConfig:
        return AppConfig(provider=ProviderConfig(account="user@example.com"))


class FakeClipboard:
    def __init__(self) -> None:
        self.values: list[str] = []

    def copy(self, value: str) -> None:
        self.values.append(value)


@dataclass
class FakeProvider:
    descriptor = ProviderDescriptor(ProviderId("gmail"), "Gmail", ProviderKind.IMAP, True)
    authenticated: tuple[AccountId, str, str] | None = None

    def authenticate(self, account_id: AccountId, username: str, app_password: str) -> None:
        self.authenticated = (account_id, username, app_password)

    def search(self, account_id: AccountId, criteria: SearchCriteria) -> list[ExtractableEmail]:
        return [
            ExtractableEmail(
                EmailMessageRef(ProviderId("gmail"), account_id, "1"),
                "security@example.com",
                "OTP",
                "Code 482913",
            )
        ]


def make_service(clipboard=None) -> tuple[FetchOtpService, FakeProvider]:
    provider = FakeProvider()
    registry = ProviderRegistry()
    registry.register(provider)
    return FetchOtpService(
        registry,
        InMemoryOtpCache(),
        FakeCredentials(),
        FakeConfig(),
        OtpExtractor(EmailOtpCandidateGenerator(), ContextOtpCandidateScorer()),
        clipboard,
    ), provider


def test_fetch_service_runs_credentials_provider_and_extractor() -> None:
    service, provider = make_service()

    result = service.fetch(SearchCriteria(unseen_only=False))

    assert result.candidate.value == "482913"
    assert provider.authenticated == (AccountId("user@example.com"), "user@example.com", "secret")


def test_fetch_service_copies_exact_otp_when_enabled() -> None:
    clipboard = FakeClipboard()
    service, _ = make_service(clipboard)

    service.fetch(SearchCriteria(unseen_only=False), copy_to_clipboard=True)

    assert clipboard.values == ["482913"]


def test_fetch_service_does_not_copy_when_disabled() -> None:
    clipboard = FakeClipboard()
    service, _ = make_service(clipboard)

    service.fetch(SearchCriteria(unseen_only=False))

    assert clipboard.values == []


def test_fetch_service_surfaces_clipboard_failure() -> None:
    class FailingClipboard:
        def copy(self, value: str) -> None:
            raise RuntimeError("clipboard unavailable")

    service, _ = make_service(FailingClipboard())

    with pytest.raises(ClipboardError, match="Unable to copy"):
        service.fetch(SearchCriteria(unseen_only=False), copy_to_clipboard=True)


def test_fetch_service_prefers_relevant_sender_and_subject_over_unrelated_email() -> None:
    service, provider = make_service()
    now = datetime.now(UTC)
    provider.search = lambda account_id, criteria: [  # type: ignore[method-assign]
        ExtractableEmail(
            EmailMessageRef(ProviderId("gmail"), account_id, "1", now),
            "orders@example.com",
            "Order receipt",
            "Your code is 111222.",
        ),
        ExtractableEmail(
            EmailMessageRef(ProviderId("gmail"), account_id, "2", now - timedelta(minutes=1)),
            "security@example.com",
            "Verification code",
            "Your code is 222333.",
        ),
    ]

    result = service.fetch(SearchCriteria(unseen_only=False))

    assert result.candidate.value == "222333"


def test_fetch_service_prefers_newer_candidate_when_scores_are_equal() -> None:
    service, provider = make_service()
    now = datetime.now(UTC)
    provider.search = lambda account_id, criteria: [  # type: ignore[method-assign]
        ExtractableEmail(
            EmailMessageRef(ProviderId("gmail"), account_id, "older", now - timedelta(minutes=2)),
            "security@example.com",
            "Verification code",
            "Your code is 111222.",
        ),
        ExtractableEmail(
            EmailMessageRef(ProviderId("gmail"), account_id, "newer", now),
            "security@example.com",
            "Verification code",
            "Your code is 222333.",
        ),
    ]

    result = service.fetch(SearchCriteria(unseen_only=False))

    assert result.candidate.value == "222333"
