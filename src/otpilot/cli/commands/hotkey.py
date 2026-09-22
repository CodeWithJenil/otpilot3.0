"""Global hotkey command composition."""

import typer

from otpilot.application.services import HotkeyService
from otpilot.cli.commands.fetch import build_service
from otpilot.domain.errors import OTPilotError
from otpilot.infrastructure.config_storage.toml import TomlConfigurationRepository
from otpilot.infrastructure.hotkeys import PynputHotkeyListener


def build_hotkey_service() -> HotkeyService:
    config = TomlConfigurationRepository().load()
    return HotkeyService(
        fetch_service=build_service(),
        listener=PynputHotkeyListener(),
        hotkey=config.hotkey,
        status=typer.echo,
    )


def command() -> None:
    """Fetch and copy an OTP whenever the configured global hotkey is pressed."""
    try:
        build_hotkey_service().run()
    except OTPilotError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
