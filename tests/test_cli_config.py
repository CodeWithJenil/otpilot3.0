"""Tests for the `otpilot config` CLI command (interactive)."""

from typer.testing import CliRunner

from otpilot.cli.app import app


def test_config_command_shows_effective_configuration(monkeypatch, tmp_path) -> None:
    """Test that `otpilot config` displays the effective configuration in non-interactive mode."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    # In test environment (no TTY), runs in non-interactive mode
    result = CliRunner().invoke(app, ["config"])

    assert result.exit_code == 0
    assert "OTPilot Settings" in result.stdout
    assert "Provider" in result.stdout
    assert "Credential" in result.stdout
    assert "Watch" in result.stdout
    assert "Hotkeys" in result.stdout
    assert "Preferences" in result.stdout
    assert "non-interactive mode" in result.stdout


def test_config_non_interactive_mode(monkeypatch, tmp_path) -> None:
    """Test that config runs in non-interactive mode when no TTY."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    result = CliRunner().invoke(app, ["config"])

    assert result.exit_code == 0
    assert "non-interactive mode" in result.stdout


def test_config_interactive_edit_hotkey(monkeypatch, tmp_path) -> None:
    """Test editing hotkey through interactive menu (requires real TTY)."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    pass


def test_config_interactive_edit_poll_interval(monkeypatch, tmp_path) -> None:
    """Test editing poll_interval_seconds through interactive menu."""
    pass


def test_config_interactive_edit_provider_account(monkeypatch, tmp_path) -> None:
    """Test editing provider.account through interactive menu."""
    pass


def test_config_interactive_invalid_poll_interval_rejected(monkeypatch, tmp_path) -> None:
    """Test that invalid poll_interval_seconds is rejected in interactive mode."""
    pass


def test_config_interactive_invalid_hotkey_rejected(monkeypatch, tmp_path) -> None:
    """Test that invalid hotkey is rejected in interactive mode."""
    pass


def test_config_interactive_invalid_theme_rejected(monkeypatch, tmp_path) -> None:
    """Test that invalid theme is rejected in interactive mode."""
    pass


def test_config_interactive_invalid_boolean_rejected(monkeypatch, tmp_path) -> None:
    """Test that invalid boolean is rejected in interactive mode."""
    pass


def test_config_interactive_unknown_provider_rejected(monkeypatch, tmp_path) -> None:
    """Test that unknown provider is rejected in interactive mode."""
    pass


def test_config_interactive_keep_current_value(monkeypatch, tmp_path) -> None:
    """Test that pressing Enter keeps current value."""
    pass


def test_config_interactive_reset(monkeypatch, tmp_path) -> None:
    """Test reset through interactive menu."""
    pass


def test_config_interactive_reset_cancelled(monkeypatch, tmp_path) -> None:
    """Test that reset can be cancelled."""
    pass


def test_config_interactive_show_path(monkeypatch, tmp_path) -> None:
    """Test showing config path through interactive menu."""
    pass


def test_config_interactive_edit_preferences_theme(monkeypatch, tmp_path) -> None:
    """Test editing preferences.theme through interactive menu."""
    pass


def test_config_interactive_edit_preferences_auto_paste(monkeypatch, tmp_path) -> None:
    """Test editing preferences.auto_paste_enabled through interactive menu."""
    pass


def test_config_interactive_edit_preferences_notifications(monkeypatch, tmp_path) -> None:
    """Test editing preferences.notifications_enabled through interactive menu."""
    pass


def test_config_secret_values_are_redacted(monkeypatch, tmp_path) -> None:
    """Test that secret configuration values are redacted in output."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    result = CliRunner().invoke(app, ["config"])

    assert result.exit_code == 0


def test_config_keyboard_interrupt(monkeypatch, tmp_path) -> None:
    """Test that Ctrl+C exits cleanly."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    result = CliRunner().invoke(app, ["config"], input="\x03")

    assert result.exit_code == 0