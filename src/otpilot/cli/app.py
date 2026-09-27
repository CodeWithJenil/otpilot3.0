"""OTPilot CLI entrypoint."""

import os
import sys
from typing import Any

import typer

from otpilot import __version__
from otpilot.application.settings import SettingsService
from otpilot.application.telemetry import create_telemetry_adapter, is_command_allowed_for_telemetry
from otpilot.cli.commands import config, doctor, fetch, hotkey, login, logout, telemetry, watch
from otpilot.infrastructure.config_storage.toml import TomlConfigurationRepository
from otpilot.infrastructure.preferences.toml import TomlPreferencesRepository


def _build_settings_service() -> SettingsService:
    return SettingsService(
        TomlConfigurationRepository(),
        TomlPreferencesRepository(),
    )


def _get_telemetry_endpoint() -> str | None:
    """Get telemetry endpoint from environment variable for local testing."""
    return os.environ.get("OTPILOT_TELEMETRY_ENDPOINT")


def _send_telemetry_event(event: str, command_name: str | None = None) -> None:
    """Send a telemetry event asynchronously if enabled."""
    settings = _build_settings_service()
    endpoint = _get_telemetry_endpoint()
    adapter = create_telemetry_adapter(settings, endpoint)
    extra = {}
    if command_name and is_command_allowed_for_telemetry(command_name):
        extra["command"] = command_name
    adapter.send(event, extra if extra else None)


def _get_telemetry_suggestion() -> str | None:
    """Get the telemetry suggestion if telemetry is disabled."""
    settings = _build_settings_service()
    snapshot = settings.snapshot()
    prefs_entry = snapshot.entry("preferences")
    prefs = prefs_entry.value if prefs_entry.value is not None else None

    if prefs is None:
        from otpilot.preferences.models import UserPreferences

        prefs = UserPreferences()

    # prefs is UserPreferences but typed as object; use getattr for safety
    if getattr(prefs, "telemetry_enabled", False):
        return None

    return (
        "\nAnonymous telemetry is disabled.\n"
        "You can optionally help improve OTPilot by sending anonymous usage data. "
        "No emails, OTPs, credentials, or clipboard contents are collected.\n"
        "  otpilot telemetry enable"
    )


class TelemetryTyper(typer.Typer):
    """Typer app that sends telemetry and shows suggestions."""

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        # Check if this is a telemetry command (to avoid recursive suggestions)
        is_telemetry_cmd = len(args) > 0 and args[0] in ("telemetry",)

        # Send app_started telemetry
        command_name = args[0] if args else None
        if command_name and not is_telemetry_cmd:
            _send_telemetry_event("app_started", command_name)

        # Run the actual command
        try:
            result = super().__call__(*args, **kwargs)
        except SystemExit:
            # Re-raise SystemExit (from typer.Exit)
            raise
        except Exception:
            # Send error telemetry? No, per requirements we shouldn't send exception details
            raise

        # Send command_executed telemetry (success)
        if command_name and not is_telemetry_cmd:
            _send_telemetry_event("command_executed", command_name)

        # Print telemetry suggestion for human-readable output
        # Only for non-telemetry commands and when output is to TTY
        if not is_telemetry_cmd and sys.stdout.isatty():
            suggestion = _get_telemetry_suggestion()
            if suggestion:
                typer.echo(suggestion)

        return result


app = TelemetryTyper(
    name="otpilot",
    help="Local-first OTP extraction from email accounts.",
    no_args_is_help=True,
)
app.command("fetch")(fetch.command)
app.command("watch")(watch.command)
app.command("hotkey")(hotkey.command)
app.command("login")(login.command)
app.command("logout")(logout.command)
app.add_typer(config.app, name="config")
app.command("doctor")(doctor.command)
app.add_typer(telemetry.app, name="telemetry")


@app.command("version")
def version() -> None:
    """Show the installed OTPilot version."""
    typer.echo(__version__)


def main() -> None:
    app()
