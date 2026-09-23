"""Tests for package metadata, imports, and CLI entry point."""

from typer.testing import CliRunner

from otpilot import __version__
from otpilot.cli.app import app


def test_package_version_is_set() -> None:
    assert __version__ == "3.0.0"


def test_package_imports_cleanly() -> None:
    import otpilot
    import otpilot.application.ports
    import otpilot.application.services
    import otpilot.cli.app
    import otpilot.config.models
    import otpilot.domain.errors
    import otpilot.domain.extraction
    import otpilot.domain.models
    import otpilot.domain.otp
    import otpilot.domain.providers
    import otpilot.domain.search
    import otpilot.domain.state
    import otpilot.infrastructure.clipboard.pyperclip_adapter
    import otpilot.infrastructure.config_storage.toml
    import otpilot.infrastructure.credentials.keyring_store
    import otpilot.infrastructure.hotkeys.pynput_adapter
    import otpilot.providers.gmail.config
    import otpilot.providers.imap.provider
    import otpilot.providers.imap.search
    import otpilot.providers.registry

    assert otpilot.__version__


def test_cli_entry_point_help() -> None:
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "otpilot" in result.stdout.lower()


def test_cli_version_reports_current() -> None:
    result = CliRunner().invoke(app, ["version"])
    assert result.exit_code == 0
    assert "3.0.0" in result.stdout


def test_all_commands_registered() -> None:
    result = CliRunner().invoke(app, ["--help"])
    for command in ("fetch", "watch", "hotkey", "login", "logout", "config", "doctor", "version"):
        assert command in result.stdout


def test_main_module_runnable() -> None:
    """Verify python -m otpilot entry point module exists."""
    from otpilot import __main__  # noqa: F401
