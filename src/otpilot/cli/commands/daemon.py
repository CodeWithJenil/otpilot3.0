"""CLI commands for daemon management."""

import sys
import time
import typer

from otpilot.application.settings import SettingsService
from otpilot.application.services import WatchService
from otpilot.cli.commands.fetch import build_service
from otpilot.domain.errors import OTPilotError
from otpilot.infrastructure.config_storage.toml import TomlConfigurationRepository
from otpilot.infrastructure.daemon import create_daemon_manager
from otpilot.infrastructure.preferences.toml import TomlPreferencesRepository


def _build_settings_service() -> SettingsService:
    return SettingsService(
        TomlConfigurationRepository(),
        TomlPreferencesRepository(),
    )


def build_daemon_watch_service() -> WatchService:
    """Build a WatchService configured for daemon mode."""
    config = TomlConfigurationRepository().load()
    return WatchService(
        fetch_service=build_service(),
        poll_interval_seconds=config.poll_interval_seconds,
        status=lambda message: None,  # Silent in daemon mode
    )


def run_internal() -> None:
    """Run the daemon's internal watch loop. This is called by the platform-specific service."""
    try:
        build_daemon_watch_service().run()
    except KeyboardInterrupt:
        pass
    except OTPilotError:
        # Log error and exit
        sys.exit(1)
    except Exception:
        sys.exit(1)


app = typer.Typer(
    name="daemon",
    help="Manage the OTPilot background daemon.",
    no_args_is_help=True,
)


def _get_daemon_manager():
    """Get the platform-specific daemon manager."""
    try:
        return create_daemon_manager()
    except OTPilotError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc


def _print_status(status) -> None:
    """Print daemon status in a consistent format."""
    typer.echo(f"Installed: {'Yes' if status.installed else 'No'}")
    typer.echo(f"Running:   {'Yes' if status.running else 'No'}")
    if status.pid:
        typer.echo(f"PID:       {status.pid}")
    typer.echo(f"Autostart: {'Enabled' if status.autostart_enabled else 'Disabled'}")
    if status.error:
        typer.secho(f"Error:     {status.error}", fg=typer.colors.RED)


@app.command("install")
def install_cmd(
    autostart: bool = typer.Option(False, "--autostart", help="Enable autostart on login."),
) -> None:
    """Install the daemon (create service files)."""
    manager = _get_daemon_manager()
    try:
        manager.install(autostart=autostart)
        typer.secho("Daemon installed successfully.", fg=typer.colors.GREEN)
        if autostart:
            typer.echo("Autostart enabled.")
    except OTPilotError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc


@app.command("uninstall")
def uninstall_cmd() -> None:
    """Uninstall the daemon (remove service files)."""
    manager = _get_daemon_manager()
    try:
        manager.uninstall()
        typer.secho("Daemon uninstalled successfully.", fg=typer.colors.GREEN)
    except OTPilotError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc


@app.command("start")
def start_cmd() -> None:
    """Start the daemon."""
    manager = _get_daemon_manager()
    try:
        manager.start()
        typer.secho("Daemon started.", fg=typer.colors.GREEN)
    except OTPilotError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc


@app.command("stop")
def stop_cmd() -> None:
    """Stop the daemon."""
    manager = _get_daemon_manager()
    try:
        manager.stop()
        typer.secho("Daemon stopped.", fg=typer.colors.GREEN)
    except OTPilotError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc


@app.command("restart")
def restart_cmd() -> None:
    """Restart the daemon."""
    manager = _get_daemon_manager()
    try:
        manager.restart()
        typer.secho("Daemon restarted.", fg=typer.colors.GREEN)
    except OTPilotError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc


@app.command("status")
def status_cmd() -> None:
    """Show daemon status."""
    manager = _get_daemon_manager()
    try:
        status = manager.status()
        _print_status(status)
    except OTPilotError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc


@app.command("enable-autostart")
def enable_autostart_cmd() -> None:
    """Enable daemon autostart on login."""
    manager = _get_daemon_manager()
    try:
        if hasattr(manager, "enable_autostart"):
            manager.enable_autostart()
        else:
            manager.install(autostart=True)
        typer.secho("Autostart enabled.", fg=typer.colors.GREEN)
    except OTPilotError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc


@app.command("disable-autostart")
def disable_autostart_cmd() -> None:
    """Disable daemon autostart on login."""
    manager = _get_daemon_manager()
    try:
        if hasattr(manager, "disable_autostart"):
            manager.disable_autostart()
        else:
            # For platforms without explicit disable, we can't easily disable
            typer.echo("Autostart disable not supported on this platform.", err=True)
            raise typer.Exit(code=1)
        typer.secho("Autostart disabled.", fg=typer.colors.GREEN)
    except OTPilotError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc


@app.command("run-internal", hidden=True)
def run_internal_cmd() -> None:
    """Internal command to run the daemon watch loop. Not for direct use."""
    run_internal()