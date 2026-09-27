"""Tests for the telemetry end-of-command suggestion."""

from unittest.mock import Mock, patch

from typer.testing import CliRunner

from otpilot.application.settings import SettingsService
from otpilot.cli.app import _get_telemetry_suggestion, _send_telemetry_event
from otpilot.infrastructure.config_storage.toml import TomlConfigurationRepository
from otpilot.infrastructure.preferences.toml import TomlPreferencesRepository


def test_get_telemetry_suggestion_returns_none_when_enabled(tmp_path) -> None:
    """_get_telemetry_suggestion should return None when telemetry is enabled."""
    config_repo = TomlConfigurationRepository(tmp_path / "config.toml")
    prefs_repo = TomlPreferencesRepository(tmp_path / "preferences.toml")
    settings = SettingsService(config_repo, prefs_repo)

    settings.set("preferences.telemetry_enabled", "true")
    settings.set("preferences.telemetry_installation_id", "a1b2c3d4-e5f6-7890-abcd-ef1234567890")

    # Need to patch the internal function to use our settings
    with patch("otpilot.cli.app._build_settings_service", return_value=settings):
        suggestion = _get_telemetry_suggestion()
    assert suggestion is None


def test_get_telemetry_suggestion_returns_message_when_disabled(tmp_path) -> None:
    """_get_telemetry_suggestion should return suggestion message when disabled."""
    config_repo = TomlConfigurationRepository(tmp_path / "config.toml")
    prefs_repo = TomlPreferencesRepository(tmp_path / "preferences.toml")
    settings = SettingsService(config_repo, prefs_repo)

    # Default is disabled
    with patch("otpilot.cli.app._build_settings_service", return_value=settings):
        suggestion = _get_telemetry_suggestion()
    assert suggestion is not None
    assert "Anonymous telemetry is disabled" in suggestion
    assert "otpilot telemetry enable" in suggestion


def test_send_telemetry_event_uses_adapter() -> None:
    """_send_telemetry_event should use the telemetry adapter."""
    with patch("otpilot.cli.app.create_telemetry_adapter") as mock_create:
        mock_adapter = Mock()
        mock_create.return_value = mock_adapter

        _send_telemetry_event("test_event", "fetch")

        mock_create.assert_called_once()
        mock_adapter.send.assert_called_once_with("test_event", {"command": "fetch"})


def test_send_telemetry_event_no_command_when_not_allowed() -> None:
    """_send_telemetry_event should not include command if not in allowlist."""
    with patch("otpilot.cli.app.create_telemetry_adapter") as mock_create:
        mock_adapter = Mock()
        mock_create.return_value = mock_adapter

        _send_telemetry_event("test_event", "rm -rf /")

        mock_create.assert_called_once()
        mock_adapter.send.assert_called_once_with("test_event", None)


def test_send_telemetry_event_includes_command_when_allowed() -> None:
    """_send_telemetry_event should include command when in allowlist."""
    with patch("otpilot.cli.app.create_telemetry_adapter") as mock_create:
        mock_adapter = Mock()
        mock_create.return_value = mock_adapter

        _send_telemetry_event("test_event", "fetch")

        mock_create.assert_called_once()
        mock_adapter.send.assert_called_once_with("test_event", {"command": "fetch"})


def test_telemetry_suggestion_not_shown_for_telemetry_commands(monkeypatch, tmp_path) -> None:
    """Telemetry commands should not show the disabled suggestion."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))

    from otpilot.cli.app import app
    runner = CliRunner()

    # Run telemetry status (disabled by default)
    result = runner.invoke(app, ["telemetry", "status"])
    assert result.exit_code == 0
    # The suggestion is shown by the status command itself, not the global mechanism
    # But the global mechanism should not add an extra suggestion
    # Count occurrences - should only be once (from status command itself)
    assert result.stdout.count("otpilot telemetry enable") == 1


def test_telemetry_suggestion_not_in_machine_output(monkeypatch, tmp_path) -> None:
    """Telemetry suggestion should not appear in non-TTY (machine) output."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))

    from otpilot.cli.app import app
    runner = CliRunner()

    # CliRunner doesn't provide a TTY, so suggestion should not appear
    # for regular commands (but telemetry commands have their own output)
    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert "3.1.0" in result.stdout
    # Should not have telemetry suggestion in machine-readable output
    assert "Telemetry is currently disabled" not in result.stdout


def test_telemetry_disabled_suggestion_format(tmp_path) -> None:
    """Test that the disabled suggestion has the correct format."""
    config_repo = TomlConfigurationRepository(tmp_path / "config.toml")
    prefs_repo = TomlPreferencesRepository(tmp_path / "preferences.toml")
    settings = SettingsService(config_repo, prefs_repo)

    with patch("otpilot.cli.app._build_settings_service", return_value=settings):
        suggestion = _get_telemetry_suggestion()

    assert suggestion is not None
    assert suggestion.startswith("\nAnonymous telemetry is disabled.")
    assert "You can optionally help improve OTPilot by sending anonymous usage data" in suggestion
    assert "No emails, OTPs, credentials, or clipboard contents are collected" in suggestion
    assert "otpilot telemetry enable" in suggestion


def test_telemetry_suggestion_none_when_enabled(tmp_path) -> None:
    """Test that suggestion is None when telemetry is enabled."""
    config_repo = TomlConfigurationRepository(tmp_path / "config.toml")
    prefs_repo = TomlPreferencesRepository(tmp_path / "preferences.toml")
    settings = SettingsService(config_repo, prefs_repo)

    settings.set("preferences.telemetry_enabled", "true")
    settings.set("preferences.telemetry_installation_id", "a1b2c3d4-e5f6-7890-abcd-ef1234567890")

    with patch("otpilot.cli.app._build_settings_service", return_value=settings):
        suggestion = _get_telemetry_suggestion()

    assert suggestion is None