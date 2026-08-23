import typer

from otpilot.application.services import FetchOtpService
from otpilot.cache.memory import InMemoryOtpCache
from otpilot.domain.errors import OTPilotError
from otpilot.domain.extraction import OtpExtractor
from otpilot.domain.otp import ContextOtpCandidateScorer, EmailOtpCandidateGenerator
from otpilot.infrastructure.clipboard.pyperclip_adapter import PyperclipClipboard
from otpilot.infrastructure.config_storage.toml import TomlConfigurationRepository
from otpilot.infrastructure.credentials.windows import WindowsCredentialManagerStore
from otpilot.providers.registry import build_provider_registry


def build_service() -> FetchOtpService:
    return FetchOtpService(
        providers=build_provider_registry(),
        cache=InMemoryOtpCache(),
        credentials=WindowsCredentialManagerStore(),
        config=TomlConfigurationRepository(),
        extractor=OtpExtractor(EmailOtpCandidateGenerator(), ContextOtpCandidateScorer()),
        clipboard=PyperclipClipboard(),
    )


def command(
    copy: bool = typer.Option(False, "--copy", help="Copy the OTP when available."),
) -> None:
    """Fetch the most probable OTP from the active email account."""
    try:
        result = build_service().fetch(copy_to_clipboard=copy)
    except OTPilotError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    if copy:
        typer.echo(f"OTP: {result.candidate.value}")
        typer.echo("Copied to clipboard.")
    else:
        typer.echo(result.candidate.value)
