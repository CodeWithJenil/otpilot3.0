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
