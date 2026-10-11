from dataclasses import dataclass

import pytest

from otpilot.application.services import WatchService
from otpilot.domain.errors import CredentialError, ExtractionError, ProviderError
from otpilot.domain.models import AccountId, EmailMessageRef, OtpCandidate, OtpResult, ProviderId


def make_result(message_id: str = "message-1") -> OtpResult:
    return OtpResult(
        OtpCandidate(
            value="482731",
            score=5.0,
            source=EmailMessageRef(
                ProviderId("gmail"),
                AccountId("account"),
                message_id,
            ),
            reason="test",
        )
    )


@dataclass
class FakeFetchService:
    outcomes: list[object]
    copied: list[str]

    def fetch(self):
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    def copy_result(self, result: OtpResult) -> None:
        self.copied.append(result.candidate.value)


def stop_after_first_poll(interval: float) -> None:
    raise KeyboardInterrupt


def test_watch_copies_new_message_once_and_stops_cleanly() -> None:
    service = FakeFetchService([make_result(), make_result()], [])
    statuses: list[str] = []

    WatchService(service, sleep=stop_after_first_poll, status=statuses.append).run()

    assert service.copied == ["482731"]
    assert statuses == [
        "Watching for new OTPs...",
        "New OTP copied to clipboard.",
        "Watch stopped.",
    ]


def test_watch_retries_after_transient_provider_failure() -> None:
    service = FakeFetchService([ProviderError("temporary"), make_result()], [])
    sleep_calls = 0

    def sleep_once(interval: float) -> None:
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls == 2:
            raise KeyboardInterrupt

    statuses: list[str] = []
    WatchService(service, sleep=sleep_once, status=statuses.append).run()

    assert service.copied == ["482731"]
    assert any("Temporary provider failure" in status for status in statuses)


def test_watch_continues_when_no_otp_is_found() -> None:
    service = FakeFetchService([ExtractionError("none")], [])

    WatchService(service, sleep=stop_after_first_poll).run()

    assert service.copied == []


def test_watch_terminates_on_fatal_credential_failure() -> None:
    service = FakeFetchService([CredentialError("missing credentials")], [])

    with pytest.raises(CredentialError):
        WatchService(service, sleep=stop_after_first_poll).run()


# ──────────────────────────────────────────────────────────────────────────────
# IMAP IDLE branch tests
# ──────────────────────────────────────────────────────────────────────────────

from dataclasses import dataclass, field as dc_field
from typing import Generator

from otpilot.domain.extraction import ExtractableEmail, OtpExtractor
from otpilot.domain.models import EmailMessageRef as Ref
from otpilot.domain.otp import ContextOtpCandidateScorer, EmailOtpCandidateGenerator
from otpilot.domain.search import SearchCriteria


def make_email(message_id: str = "uid-1", otp: str = "482731") -> ExtractableEmail:
    return ExtractableEmail(
        source=Ref(ProviderId("gmail"), AccountId("account"), message_id),
        sender="sender@example.com",
        subject=f"Your OTP is {otp}",
        text_body=f"Your OTP is {otp}",
        html_body=None,
    )


@dataclass
class FakeIdleProvider:
    """Yields a fixed sequence of emails then raises KeyboardInterrupt."""
    emails: list[ExtractableEmail]

    def idle_fetch(
        self, account_id: object, criteria: object
    ) -> Generator[ExtractableEmail, None, None]:
        yield from self.emails
        raise KeyboardInterrupt


@dataclass
class FakeIdleFetchService:
    """Minimal FetchOtpService lookalike for IDLE-branch tests."""
    copied: list[str] = dc_field(default_factory=list)
    _extractor: OtpExtractor = dc_field(
        default_factory=lambda: OtpExtractor(
            EmailOtpCandidateGenerator(), ContextOtpCandidateScorer()
        )
    )

    @property
    def extractor(self) -> OtpExtractor:
        return self._extractor

    def copy_result(self, result: OtpResult) -> None:
        self.copied.append(result.candidate.value)


def _idle_watch(emails: list[ExtractableEmail]) -> tuple[list[str], list[str]]:
    """Helper: run WatchService in IDLE mode, return (copied, statuses)."""
    fetch_svc = FakeIdleFetchService()
    statuses: list[str] = []
    provider = FakeIdleProvider(emails)
    WatchService(
        fetch_service=fetch_svc,  # type: ignore[arg-type]
        idle_provider=provider,
        idle_account_id=AccountId("account"),
        status=statuses.append,
    ).run()
    return fetch_svc.copied, statuses


def test_idle_watch_copies_new_otp() -> None:
    """A single new email with an OTP is copied exactly once."""
    copied, statuses = _idle_watch([make_email("uid-1", "123456")])
    assert copied == ["123456"]
    assert "New OTP copied to clipboard." in statuses
    assert "Watch stopped." in statuses


def test_idle_watch_duplicate_message_copied_once() -> None:
    """The same UID yielded twice must only trigger one clipboard write."""
    email = make_email("uid-dup", "999888")
    copied, _ = _idle_watch([email, email])
    assert copied == ["999888"]


def test_idle_watch_email_without_otp_is_skipped() -> None:
    """An email body containing no OTP produces no clipboard write."""
    no_otp = ExtractableEmail(
        source=Ref(ProviderId("gmail"), AccountId("account"), "uid-no-otp"),
        sender="s@example.com",
        subject="Hello",
        text_body="No code here at all.",
        html_body=None,
    )
    copied, _ = _idle_watch([no_otp])
    assert copied == []


def test_idle_watch_multiple_messages_all_copied() -> None:
    """Multiple distinct messages each trigger exactly one clipboard write."""
    emails = [make_email(f"uid-{i}", str(100000 + i)) for i in range(3)]
    copied, _ = _idle_watch(emails)
    assert len(copied) == 3
    assert "100000" in copied
    assert "100002" in copied


def test_idle_watch_stops_on_keyboard_interrupt() -> None:
    """KeyboardInterrupt from inside the generator terminates the loop cleanly."""
    _, statuses = _idle_watch([])
    assert "Watch stopped." in statuses


def test_idle_watch_falls_back_to_poll_when_no_idle_provider() -> None:
    """When idle_provider is None the polling branch is used (regression guard)."""
    svc = FakeFetchService([make_result("poll-msg"), make_result("poll-msg")], [])
    WatchService(svc, sleep=stop_after_first_poll).run()
    assert svc.copied == ["482731"]
