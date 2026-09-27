"""Telemetry CLI commands."""

from __future__ import annotations

import typer

from otpilot.application.settings import SettingsService
from otpilot.application.telemetry import generate_installation_id
from otpilot.infrastructure.config_storage.toml import TomlConfigurationRepository
from otpilot.infrastructure.preferences.toml import TomlPreferencesRepository
from otpilot.preferences.models import UserPreferences

app = typer.Typer(
    name="telemetry",
    help="Manage anonymous usage telemetry.",
    no_args_is_help=True,
)


def _get_settings_service() -> SettingsService:
    """Get a settings service with real repositories."""
    return SettingsService(
        TomlConfigurationRepository(),
        TomlPreferencesRepository(),
    )


def _get_preferences(settings: SettingsService) -> UserPreferences:
    """Get current preferences from settings."""
    snapshot = settings.snapshot()
    prefs_entry = snapshot.entry("preferences")
    prefs = prefs_entry.value if prefs_entry.value is not None else None
    if prefs is None:
        prefs = UserPreferences()
    return prefs  # type: ignore[return-value]


@app.command("enable")
def enable() -> None:
    """Enable anonymous telemetry collection."""
    settings = _get_settings_service()
    prefs = _get_preferences(settings)

    # Generate installation ID if needed
    installation_id = prefs.telemetry_installation_id
    if not installation_id:
        installation_id = generate_installation_id()

    # Enable telemetry - set individual preference keys
    settings.set("preferences.telemetry_enabled", "true")
    settings.set("preferences.telemetry_installation_id", installation_id)

    typer.echo("Telemetry enabled.")
    typer.echo("")
    typer.echo("OTPilot will now send anonymous usage data to help improve the product.")
    typer.echo("")
    typer.echo("Collected data (anonymous):")
    typer.echo("  • Random installation ID (generated locally)")
    typer.echo("  • Event names (e.g., 'app_started', 'command_executed')")
    typer.echo("  • OTPilot version")
    typer.echo("  • Python version (major.minor)")
    typer.echo("  • Operating system (windows/macos/linux)")
    typer.echo("  • CPU architecture (e.g., x86_64, arm64)")
    typer.echo("  • UTC timestamp")
    typer.echo("")
    typer.echo("NOT collected:")
    typer.echo("  • Email addresses, email contents, OTP codes")
    typer.echo("  • Credentials, passwords, access tokens")
    typer.echo("  • Clipboard contents, file paths, usernames")
    typer.echo("  • IP addresses, exact location, hostnames")
    typer.echo("  • Command arguments or any sensitive data")
    typer.echo("")
    typer.echo("You can disable telemetry at any time with:")
    typer.echo("  otpilot telemetry disable")
    typer.echo("")
    typer.echo(f"Installation ID: {installation_id}")


@app.command("disable")
def disable() -> None:
    """Disable telemetry collection."""
    settings = _get_settings_service()

    # Disable telemetry but preserve installation ID
    settings.set("preferences.telemetry_enabled", "false")

    typer.echo("Telemetry disabled.")
    typer.echo("Future telemetry transmission has been stopped.")
    typer.echo("Your anonymous installation ID is preserved locally.")


@app.command("status")
def status() -> None:
    """Show telemetry status."""
    settings = _get_settings_service()
    prefs = _get_preferences(settings)

    if prefs.telemetry_enabled:
        typer.echo("Telemetry: ENABLED")
        if prefs.telemetry_installation_id:
            typer.echo(f"Installation ID: {prefs.telemetry_installation_id}")
    else:
        typer.echo("Telemetry: DISABLED")
        typer.echo("")
        typer.echo("Enable anonymous telemetry to help improve OTPilot:")
        typer.echo("  otpilot telemetry enable")


def get_telemetry_suggestion() -> str | None:
    """Get the telemetry suggestion message if telemetry is disabled.

    Returns None if telemetry is enabled or if the suggestion should not be shown.
    """
    settings = _get_settings_service()
    prefs = _get_preferences(settings)

    if prefs.telemetry_enabled:
        return None

    return (
        "\nAnonymous telemetry is disabled.\n"
        "You can optionally help improve OTPilot by sending anonymous usage data. "
        "No emails, OTPs, credentials, or clipboard contents are collected.\n"
        "  otpilot telemetry enable"
    )