"""Tests for the `otpilot config` CLI command.

Interactive editing requires a real TTY; under the CLI runner (no TTY) the
command must fall back to non-interactive display.  Full interactive flows
are covered in ``test_config_ui.py`` and ``test_config_pty.py``.
"""

import platformdirs
from typer.testing import CliRunner

from otpilot.cli.app import app
from otpilot.infrastructure.config_storage.toml import TomlConfigurationRepository
from otpilot.infrastructure.preferences.toml import TomlPreferencesRepository

runner = CliRunner()


def _isolate_config(monkeypatch, tmp_path) -> None:
    """Point platformdirs at a temporary config home for this test.

    ``platformdirs`` ignores ``XDG_CONFIG_HOME`` on macOS, so ``HOME`` is
    overridden as well.
    """
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))


def test_config_command_shows_effective_configuration(monkeypatch, tmp_path) -> None:
    _isolate_config(monkeypatch, tmp_path)

    result = runner.invoke(app, ["config"])

    assert result.exit_code == 0
    assert "OTPilot Settings" in result.stdout
    assert "Provider" in result.stdout
    assert "Credential" in result.stdout
    assert "Watch" in result.stdout
    assert "Hotkeys" in result.stdout
    assert "Preferences" in result.stdout


def test_config_non_interactive_flag(monkeypatch, tmp_path) -> None:
    _isolate_config(monkeypatch, tmp_path)

    result = runner.invoke(app, ["config", "--non-interactive"])

    assert result.exit_code == 0
    assert "non-interactive mode" in result.stdout


def test_config_non_tty_falls_back_to_non_interactive(monkeypatch, tmp_path) -> None:
    """Without a TTY the command must not attempt interactive editing."""
    _isolate_config(monkeypatch, tmp_path)

    # CliRunner stdin is not a TTY, so the fallback path runs.
    result = runner.invoke(app, ["config"])

    assert result.exit_code == 0
    assert "non-interactive mode" in result.stdout
    assert "Goodbye" not in result.stdout


def test_config_invalid_config_file_exits_cleanly(monkeypatch, tmp_path) -> None:
    _isolate_config(monkeypatch, tmp_path)
    config_path = TomlConfigurationRepository().path
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("not [valid toml")

    result = runner.invoke(app, ["config"])

    assert result.exit_code == 1
    assert "Error" in result.stdout
    assert "Traceback" not in result.stdout


def test_config_invalid_preferences_file_exits_cleanly(monkeypatch, tmp_path) -> None:
    _isolate_config(monkeypatch, tmp_path)
    preferences_path = TomlPreferencesRepository().path
    preferences_path.parent.mkdir(parents=True, exist_ok=True)
    preferences_path.write_text("not [valid toml")

    result = runner.invoke(app, ["config"])

    assert result.exit_code == 1
    assert "Error" in result.stdout
    assert "Traceback" not in result.stdout


def test_config_secret_values_are_redacted(monkeypatch, tmp_path) -> None:
    """Displaying configuration must not expose secret values."""
    _isolate_config(monkeypatch, tmp_path)

    result = runner.invoke(app, ["config"])

    assert result.exit_code == 0
    assert "app_password" not in result.stdout


def test_config_keyboard_interrupt(monkeypatch, tmp_path) -> None:
    """Ctrl+C input must not crash the command."""
    _isolate_config(monkeypatch, tmp_path)

    result = runner.invoke(app, ["config"], input="\x03")

    assert result.exit_code == 0


def test_config_displays_all_settable_keys(monkeypatch, tmp_path) -> None:
    _isolate_config(monkeypatch, tmp_path)

    result = runner.invoke(app, ["config"])

    assert result.exit_code == 0
    for label in (
        "Provider ID",
        "Account",
        "Backend",
        "Poll Interval",
        "Hotkey",
        "Theme",
        "Notifications",
        "Auto Paste",
        "Reset to Defaults",
        "Exit",
    ):
        assert label in result.stdout


def test_platformdirs_respects_isolated_home(monkeypatch, tmp_path) -> None:
    """Guard the isolation strategy used by these tests."""
    _isolate_config(monkeypatch, tmp_path)

    path = platformdirs.user_config_path("otpilot")

    assert str(tmp_path) in str(path)
