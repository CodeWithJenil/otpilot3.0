"""Tests for telemetry CLI commands."""

from typer.testing import CliRunner

from otpilot.cli.app import app

runner = CliRunner()


def _isolate_config(monkeypatch, tmp_path) -> None:
    """Point platformdirs at a temporary config home for this test."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))


def test_telemetry_status_disabled_by_default(monkeypatch, tmp_path) -> None:
    """Telemetry status should show disabled by default."""
    _isolate_config(monkeypatch, tmp_path)

    result = runner.invoke(app, ["telemetry", "status"])

    assert result.exit_code == 0
    assert "Telemetry: DISABLED" in result.stdout
    assert "otpilot telemetry enable" in result.stdout


def test_telemetry_enable_creates_installation_id(monkeypatch, tmp_path) -> None:
    """Telemetry enable should create installation ID and enable telemetry."""
    _isolate_config(monkeypatch, tmp_path)

    result = runner.invoke(app, ["telemetry", "enable"])

    assert result.exit_code == 0
    assert "Telemetry enabled." in result.stdout
    assert "Installation ID:" in result.stdout
    # Should show what is collected
    assert "Collected data (anonymous):" in result.stdout
    # Should show what is NOT collected
    assert "NOT collected:" in result.stdout

    # Verify status now shows enabled
    result = runner.invoke(app, ["telemetry", "status"])
    assert result.exit_code == 0
    assert "Telemetry: ENABLED" in result.stdout
    assert "Installation ID:" in result.stdout


def test_telemetry_disable_stops_transmission(monkeypatch, tmp_path) -> None:
    """Telemetry disable should stop transmission but preserve installation ID."""
    _isolate_config(monkeypatch, tmp_path)

    # Enable first
    runner.invoke(app, ["telemetry", "enable"])

    # Get the installation ID from status
    result = runner.invoke(app, ["telemetry", "status"])
    assert "Installation ID:" in result.stdout
    installation_id = result.stdout.split("Installation ID:")[1].strip()

    # Disable
    result = runner.invoke(app, ["telemetry", "disable"])
    assert result.exit_code == 0
    assert "Telemetry disabled." in result.stdout
    assert "preserved locally" in result.stdout

    # Status should show disabled but ID preserved
    result = runner.invoke(app, ["telemetry", "status"])
    assert result.exit_code == 0
    assert "Telemetry: DISABLED" in result.stdout
    assert installation_id not in result.stdout  # Not shown when disabled


def test_telemetry_reenable_preserves_installation_id(monkeypatch, tmp_path) -> None:
    """Re-enabling telemetry should preserve the existing installation ID."""
    _isolate_config(monkeypatch, tmp_path)

    # Enable
    runner.invoke(app, ["telemetry", "enable"])
    result = runner.invoke(app, ["telemetry", "status"])
    installation_id = result.stdout.split("Installation ID:")[1].strip()

    # Disable
    runner.invoke(app, ["telemetry", "disable"])

    # Re-enable
    runner.invoke(app, ["telemetry", "enable"])
    result = runner.invoke(app, ["telemetry", "status"])
    new_id = result.stdout.split("Installation ID:")[1].strip()

    # Should be the same ID
    assert new_id == installation_id


def test_telemetry_enable_shows_what_is_collected(monkeypatch, tmp_path) -> None:
    """Telemetry enable should clearly explain what data is collected."""
    _isolate_config(monkeypatch, tmp_path)

    result = runner.invoke(app, ["telemetry", "enable"])

    assert result.exit_code == 0
    # Check for key collected fields
    assert "Random installation ID" in result.stdout
    assert "Event names" in result.stdout
    assert "OTPilot version" in result.stdout
    assert "Python version" in result.stdout
    assert "Operating system" in result.stdout
    assert "CPU architecture" in result.stdout
    assert "UTC timestamp" in result.stdout

    # Check for key NOT collected fields
    assert "Email addresses" in result.stdout
    assert "OTP codes" in result.stdout
    assert "Credentials" in result.stdout
    assert "Clipboard contents" in result.stdout
    assert "IP addresses" in result.stdout
    assert "Command arguments" in result.stdout


def test_telemetry_commands_do_not_trigger_suggestion(monkeypatch, tmp_path) -> None:
    """Telemetry commands should not show the disabled suggestion."""
    _isolate_config(monkeypatch, tmp_path)

    # Run telemetry status (disabled by default)
    result = runner.invoke(app, ["telemetry", "status"])
    assert result.exit_code == 0
    # The suggestion is shown by the status command itself, not the global mechanism
    # But the global mechanism should not add an extra suggestion
    # Count occurrences - should only be once (from status command itself)
    assert result.stdout.count("otpilot telemetry enable") == 1


def test_telemetry_help_shows_all_commands(monkeypatch, tmp_path) -> None:
    """Telemetry help should show all subcommands."""
    _isolate_config(monkeypatch, tmp_path)

    result = runner.invoke(app, ["telemetry", "--help"])

    assert result.exit_code == 0
    assert "enable" in result.stdout
    assert "disable" in result.stdout
    assert "status" in result.stdout


def test_telemetry_invalid_subcommand_shows_help(monkeypatch, tmp_path) -> None:
    """Invalid telemetry subcommand should show help/error."""
    _isolate_config(monkeypatch, tmp_path)

    result = runner.invoke(app, ["telemetry", "invalid"])

    assert result.exit_code != 0


def test_telemetry_suggestion_not_in_machine_output(monkeypatch, tmp_path) -> None:
    """Telemetry suggestion should not appear in non-TTY (machine) output."""
    _isolate_config(monkeypatch, tmp_path)

    # CliRunner doesn't provide a TTY, so suggestion should not appear
    # for regular commands (but telemetry commands have their own output)
    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert "3.1.0" in result.stdout
    # Should not have telemetry suggestion in machine-readable output
    assert "Telemetry is currently disabled" not in result.stdout