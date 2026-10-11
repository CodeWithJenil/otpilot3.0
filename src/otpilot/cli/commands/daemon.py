"""CLI commands for daemon management."""

import sys
import time
import typer

from otpilot.application.services import FetchOtpService, WatchService
from otpilot.application.settings import SettingsService
from otpilot.cache.memory import InMemoryOtpCache
from otpilot.domain.errors import OTPilotError
from otpilot.domain.extraction import OtpExtractor
from otpilot.domain.otp import ContextOtpCandidateScorer, EmailOtpCandidateGenerator
from otpilot.infrastructure.clipboard.pyperclip_adapter import PyperclipClipboard
from otpilot.infrastructure.config_storage.toml import TomlConfigurationRepository
from otpilot.infrastructure.credentials.keyring_store import KeyringCredentialStore
from otpilot.infrastructure.daemon import create_daemon_manager
from otpilot.infrastructure.preferences.toml import TomlPreferencesRepository
from otpilot.providers.registry import build_provider_registry


def _build_settings_service() -> SettingsService:
    return SettingsService(
        TomlConfigurationRepository(),
        TomlPreferencesRepository(),
    )


def build_daemon_watch_service() -> WatchService:
    """Build a WatchService configured for daemon mode.

    Resolves the configured provider, authenticates it, and wires it into
    ``WatchService.idle_provider`` so the IMAP IDLE loop is used automatically.
    Falls back to the polling loop if no account is configured yet (e.g. the
    daemon is installed before ``otpilot login`` has been run).
    """
    import logging
    logger = logging.getLogger("otpilot.daemon")

    config_repo = TomlConfigurationRepository()
    config = config_repo.load()
    credentials = KeyringCredentialStore()
    registry = build_provider_registry(session_renewal_hours=config.session_renewal_hours)


    fetch_service = FetchOtpService(
        providers=registry,
        cache=InMemoryOtpCache(),
        credentials=credentials,
        config=config_repo,
        extractor=OtpExtractor(EmailOtpCandidateGenerator(), ContextOtpCandidateScorer()),
        clipboard=PyperclipClipboard(),
    )

    # Try to resolve account and authenticate the provider for IDLE.
    idle_provider = None
    idle_account_id = None
    account = config.provider.account
    if account:
        from otpilot.domain.models import AccountId, ProviderId
        account_id = AccountId(account)
        provider = registry.get(ProviderId(config.provider.provider_id))
        stored = credentials.get_app_password(account_id) if provider is not None else None
        if provider is not None and stored is not None:
            username, app_password = stored
            try:
                provider.authenticate(account_id, username, app_password)
                idle_provider = provider
                idle_account_id = account_id
                logger.info("IMAP IDLE mode enabled for account %s.", account)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Could not authenticate provider; falling back to polling: %s", exc)

    return WatchService(
        fetch_service=fetch_service,
        poll_interval_seconds=config.poll_interval_seconds,
        status=lambda message: None,  # Silent in daemon mode
        hotkey_enabled=config.hotkey_enabled,
        idle_provider=idle_provider,
        idle_account_id=idle_account_id,
    )


def run_internal() -> None:
    """Run the daemon's internal watch loop. This is called by the platform-specific service."""
    # Set up logging to stderr only (avoid file permission issues in launchd/service environments)
    import logging
    import signal
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stderr)]
    )
    logger = logging.getLogger('otpilot.daemon')
    logger.info('Starting daemon run_internal')

    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit(0))
    
    try:
        logger.info('Building watch service')
        watch_service = build_daemon_watch_service()
        logger.info('Watch service built, calling run()')
        watch_service.run()
        logger.info('Watch service run() returned')
    except KeyboardInterrupt:
        logger.info('KeyboardInterrupt caught')
        pass
    except OTPilotError as e:
        logger.error(f'OTPilotError: {e}')
        sys.exit(1)
    except Exception as e:
        logger.exception(f'Unexpected error: {e}')
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
    if status.state:
        typer.echo(f"State:     {status.state}")
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