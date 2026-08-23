import typer

from otpilot.application.services import WatchService
from otpilot.cli.commands.fetch import build_service
from otpilot.domain.errors import OTPilotError
from otpilot.infrastructure.config_storage.toml import TomlConfigurationRepository


def build_watch_service() -> WatchService:
    config = TomlConfigurationRepository().load()
    return WatchService(
        fetch_service=build_service(),
        poll_interval_seconds=config.poll_interval_seconds,
        status=typer.echo,
    )


def command() -> None:
    """Poll for new OTP emails and copy new OTPs to the clipboard."""
    try:
        build_watch_service().run()
    except OTPilotError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
