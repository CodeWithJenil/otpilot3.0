from typer.testing import CliRunner

from otpilot.cli.app import app
from otpilot.cli.commands import fetch, watch
from otpilot.domain.models import AccountId, EmailMessageRef, OtpCandidate, OtpResult, ProviderId

candidate = OtpCandidate(
    value="482913",
    score=5.0,
    source=EmailMessageRef(ProviderId("gmail"), AccountId("account"), "1"),
    reason="test",
)


def test_version_command() -> None:
    result = CliRunner().invoke(app, ["version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.stdout


def test_fetch_command_is_registered() -> None:
    result = CliRunner().invoke(app, ["fetch"])
    assert result.exit_code == 1
    assert "No email account is configured" in result.stderr


def test_fetch_command_displays_service_result(monkeypatch) -> None:
    class FakeService:
        def fetch(self, *, copy_to_clipboard: bool = False):
            return OtpResult(candidate)

    monkeypatch.setattr(fetch, "build_service", lambda: FakeService())
    result = CliRunner().invoke(app, ["fetch"])

    assert result.exit_code == 0
    assert result.stdout.strip() == "482913"


def test_fetch_command_confirms_copy(monkeypatch) -> None:
    class FakeService:
        def fetch(self, *, copy_to_clipboard: bool = False):
            assert copy_to_clipboard is True
            return OtpResult(candidate)

    monkeypatch.setattr(fetch, "build_service", lambda: FakeService())
    result = CliRunner().invoke(app, ["fetch", "--copy"])

    assert result.exit_code == 0
    assert result.stdout.splitlines() == ["OTP: 482913", "Copied to clipboard."]


def test_watch_command_invokes_watch_service(monkeypatch) -> None:
    called = False

    class FakeService:
        def run(self) -> None:
            nonlocal called
            called = True

    monkeypatch.setattr(watch, "build_watch_service", lambda: FakeService())
    result = CliRunner().invoke(app, ["watch"])

    assert result.exit_code == 0
    assert called is True
