"""OTPilot CLI entrypoint."""

import os
import random
import sys
from typing import Any

import typer

from otpilot import __version__
from otpilot.application.settings import SettingsService
from otpilot.application.telemetry import create_telemetry_adapter, is_command_allowed_for_telemetry
from otpilot.cli.commands import config, daemon, doctor, fetch, hotkey, login, logout, telemetry, watch
from otpilot.infrastructure.config_storage.toml import TomlConfigurationRepository
from otpilot.infrastructure.preferences.toml import TomlPreferencesRepository
from otpilot.preferences.models import UserPreferences


COMMUNITY_MESSAGES = (
    "Enjoying OTPilot? Share your review: https://jenil-otpilot.vercel.app/feedback",
    "Found a bug or issue? Report it here: https://github.com/CodeWithJenil/otpilot3.0/issues",
    "Have an idea or question? Join the discussion: https://github.com/CodeWithJenil/otpilot3.0/discussions",
)

EXCLUDED_COMMANDS = {
    "telemetry",
    "version",
    "daemon",
    "config",
    "doctor",
    "login",
    "logout",
}

MACHINE_READABLE_COMMANDS = {
    "fetch",  # Can be used with --copy for scripting
}


# Test hooks - can be overridden in tests
_get_settings_service_for_testing: SettingsService | None = None
_isatty_for_testing: bool | None = None


def _build_settings_service() -> SettingsService:
    return SettingsService(
        TomlConfigurationRepository(),
        TomlPreferencesRepository(),
    )


def _get_settings_service() -> SettingsService:
    """Get settings service, using test hook if available."""
    if _get_settings_service_for_testing is not None:
        return _get_settings_service_for_testing
    return _build_settings_service()


def _is_tty() -> bool:
    """Check if stdout is a TTY, using test hook if available."""
    if _isatty_for_testing is not None:
        return _isatty_for_testing
    return sys.stdout.isatty()


def _get_telemetry_endpoint() -> str | None:
    """Get telemetry endpoint from environment variable for local testing."""
    return os.environ.get("OTPILOT_TELEMETRY_ENDPOINT")


def _send_telemetry_event(event: str, command_name: str | None = None) -> None:
    """Send a telemetry event asynchronously if enabled."""
    settings = _get_settings_service()
    endpoint = _get_telemetry_endpoint()
    adapter = create_telemetry_adapter(settings, endpoint)
    extra = {}
    if command_name and is_command_allowed_for_telemetry(command_name):
        extra["command"] = command_name
    adapter.send(event, extra if extra else None)


def _get_telemetry_suggestion() -> str | None:
    """Get the telemetry suggestion if telemetry is disabled."""
    settings = _get_settings_service()
    snapshot = settings.snapshot()
    prefs_entry = snapshot.entry("preferences")
    prefs = prefs_entry.value if prefs_entry.value is not None else None

    if prefs is None:
        prefs = UserPreferences()

    if getattr(prefs, "telemetry_enabled", False):
        return None

    return (
        "\nAnonymous telemetry is disabled.\n"
        "You can optionally help improve OTPilot by sending anonymous usage data. "
        "No emails, OTPs, credentials, or clipboard contents are collected.\n"
        "  otpilot telemetry enable"
    )


def _should_show_community_message(command_name: str | None, exit_code: int) -> bool:
    """Determine if a community message should be shown after a command."""
    if command_name is None:
        return False
    if command_name in EXCLUDED_COMMANDS:
        return False
    if exit_code != 0:
        return False
    if not _is_tty():
        return False
    return True


def _get_community_message_settings() -> tuple[bool, float]:
    """Get community message settings from preferences."""
    settings = _get_settings_service()
    snapshot = settings.snapshot()
    prefs_entry = snapshot.entry("preferences")
    prefs = prefs_entry.value if prefs_entry.value is not None else None

    if prefs is None:
        prefs = UserPreferences()

    enabled = getattr(prefs, "community_messages_enabled", True)
    probability = getattr(prefs, "community_message_probability", 0.15)
    return enabled, probability


def _maybe_show_community_message(command_name: str | None, exit_code: int, random_source: random.Random | None = None) -> None:
    """Show a randomized community message if conditions are met."""
    if not _should_show_community_message(command_name, exit_code):
        return

    enabled, probability = _get_community_message_settings()
    if not enabled:
        return

    rng = random_source or random.Random()
    if rng.random() >= probability:
        return

    message = rng.choice(COMMUNITY_MESSAGES)
    # Print with a blank line before for separation
    typer.echo("")
    typer.secho(message, fg=typer.colors.BRIGHT_BLUE)


class TelemetryTyper(typer.Typer):
    """Typer app that sends telemetry, shows suggestions, and community messages."""

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        # Check if this is a telemetry command (to avoid recursive suggestions)
        is_telemetry_cmd = len(args) > 0 and args[0] in ("telemetry",)

        # Send app_started telemetry
        command_name = args[0] if args else None
        if command_name and not is_telemetry_cmd:
            _send_telemetry_event("app_started", command_name)

        # Run the actual command
        exit_code = 0
        try:
            result = super().__call__(*args, **kwargs)
        except SystemExit as exc:
            exit_code = exc.code if isinstance(exc.code, int) else 1
            raise
        except Exception:
            exit_code = 1
            raise

        # Send command_executed telemetry (success)
        if command_name and not is_telemetry_cmd:
            _send_telemetry_event("command_executed", command_name)

        # Print telemetry suggestion for human-readable output
        # Only for non-telemetry commands and when output is to TTY
        if not is_telemetry_cmd and _is_tty():
            suggestion = _get_telemetry_suggestion()
            if suggestion:
                typer.echo(suggestion)

        # Print community message after successful command
        if not is_telemetry_cmd and _is_tty():
            _maybe_show_community_message(command_name, exit_code)

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
app.add_typer(daemon.app, name="daemon")


@app.command("version")
def version() -> None:
    """Show the installed OTPilot version."""
    typer.echo(__version__)


def main() -> None:
    app()