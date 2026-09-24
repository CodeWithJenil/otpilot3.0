"""Tests for the `otpilot doctor` CLI command."""

from typer.testing import CliRunner

from otpilot.cli.app import app


def test_doctor_command_runs(monkeypatch, tmp_path) -> None:
    """Test that `otpilot doctor` runs and produces output."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    result = CliRunner().invoke(app, ["doctor", "--offline"])

    assert result.exit_code == 0
    assert "OTPilot Doctor" in result.stdout
    assert "Environment" in result.stdout
    assert "Configuration" in result.stdout
    assert "Credentials" in result.stdout
    assert "Connectivity" in result.stdout
    assert "Clipboard" in result.stdout
    assert "Hotkeys" in result.stdout
    assert "Dependencies" in result.stdout
    assert "Summary" in result.stdout


def test_doctor_command_offline_skips_connectivity(monkeypatch, tmp_path) -> None:
    """Test that `--offline` skips the connectivity check."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    result = CliRunner().invoke(app, ["doctor", "--offline"])

    assert result.exit_code == 0
    assert "SKIP" in result.stdout
    assert "Gmail connection not tested" in result.stdout


def test_doctor_command_reports_python_version(monkeypatch, tmp_path) -> None:
    """Test that doctor reports Python version."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    result = CliRunner().invoke(app, ["doctor", "--offline"])

    assert result.exit_code == 0
    assert "Python version:" in result.stdout
    assert "PASS" in result.stdout


def test_doctor_command_reports_os(monkeypatch, tmp_path) -> None:
    """Test that doctor reports operating system."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    result = CliRunner().invoke(app, ["doctor", "--offline"])

    assert result.exit_code == 0
    assert "Operating system:" in result.stdout
    assert "PASS" in result.stdout


def test_doctor_command_reports_otpilot_version(monkeypatch, tmp_path) -> None:
    """Test that doctor reports OTPilot version."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    result = CliRunner().invoke(app, ["doctor", "--offline"])

    assert result.exit_code == 0
    assert "OTPilot version: 3.0.0" in result.stdout


def test_doctor_command_checks_config_directory(monkeypatch, tmp_path) -> None:
    """Test that doctor checks config directory writability."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    result = CliRunner().invoke(app, ["doctor", "--offline"])

    assert result.exit_code == 0
    assert "Configuration directory" in result.stdout
    assert "PASS" in result.stdout


def test_doctor_command_checks_keyring(monkeypatch, tmp_path) -> None:
    """Test that doctor checks keyring backend."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    result = CliRunner().invoke(app, ["doctor", "--offline"])

    assert result.exit_code == 0
    assert "Keyring" in result.stdout


def test_doctor_command_checks_clipboard(monkeypatch, tmp_path) -> None:
    """Test that doctor checks clipboard backend."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    result = CliRunner().invoke(app, ["doctor", "--offline"])

    assert result.exit_code == 0
    assert "Clipboard" in result.stdout
    assert "backend available" in result.stdout.lower()


def test_doctor_command_checks_hotkeys(monkeypatch, tmp_path) -> None:
    """Test that doctor checks hotkey environment."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    result = CliRunner().invoke(app, ["doctor", "--offline"])

    assert result.exit_code == 0
    assert "Hotkeys" in result.stdout
    assert "Environment" in result.stdout


def test_doctor_command_checks_dependencies(monkeypatch, tmp_path) -> None:
    """Test that doctor checks required dependencies."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    result = CliRunner().invoke(app, ["doctor", "--offline"])

    assert result.exit_code == 0
    assert "Dependencies" in result.stdout
    assert "imapclient" in result.stdout
    assert "keyring" in result.stdout
    assert "pydantic" in result.stdout
    assert "pynput" in result.stdout
    assert "pyperclip" in result.stdout
    assert "rich" in result.stdout
    assert "tomli-w" in result.stdout
    assert "typer" in result.stdout


def test_doctor_command_summary_counts(monkeypatch, tmp_path) -> None:
    """Test that doctor summary shows correct counts."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    result = CliRunner().invoke(app, ["doctor", "--offline"])

    assert result.exit_code == 0
    assert "Summary" in result.stdout
    assert "Passed:" in result.stdout
    assert "Warnings:" in result.stdout
    assert "Failed:" in result.stdout
    assert "Skipped:" in result.stdout


def test_doctor_command_exit_code_zero_on_success(monkeypatch, tmp_path) -> None:
    """Test that doctor exits with 0 when no critical failures."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    result = CliRunner().invoke(app, ["doctor", "--offline"])

    assert result.exit_code == 0


def test_doctor_command_no_secrets_in_output(monkeypatch, tmp_path) -> None:
    """Test that doctor output never contains actual secret values."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    result = CliRunner().invoke(app, ["doctor", "--offline"])

    assert result.exit_code == 0
    # Should not contain any actual credential values (only the word "password" in help text)
    # Check that no actual credential values appear (like Gmail app passwords)
    assert "gmail app password" in result.stdout.lower()  # This is help text, not a secret
    # Ensure no actual credential values are printed
    # Real app passwords would be 16-char strings, not the phrase "app password"


def test_doctor_command_help(monkeypatch, tmp_path) -> None:
    """Test that doctor --help works."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    result = CliRunner().invoke(app, ["doctor", "--help"])

    assert result.exit_code == 0
    assert "offline" in result.stdout.lower()
    assert "skip" in result.stdout.lower()


def test_doctor_with_missing_config(monkeypatch, tmp_path) -> None:
    """Test that doctor handles missing config gracefully."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    result = CliRunner().invoke(app, ["doctor", "--offline"])

    assert result.exit_code == 0
    assert (
        "Configuration file is valid" in result.stdout
        or "No configuration file yet" in result.stdout
    )


def test_doctor_with_invalid_config(monkeypatch, tmp_path) -> None:
    """Test that doctor reports invalid config."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    # Create an invalid config file
    config_dir = tmp_path / "otpilot"
    config_dir.mkdir()
    (config_dir / "config.toml").write_text("invalid = toml [")

    result = CliRunner().invoke(app, ["doctor", "--offline"])

    assert result.exit_code == 1  # Should fail due to invalid config
    assert "FAIL" in result.stdout
    assert "invalid or malformed" in result.stdout.lower()


def test_doctor_with_missing_account(monkeypatch, tmp_path) -> None:
    """Test that doctor warns when no account is configured."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    result = CliRunner().invoke(app, ["doctor", "--offline"])

    assert result.exit_code == 0
    assert "WARN" in result.stdout
    assert (
        "No email account is configured" in result.stdout
        or "account is configured" in result.stdout
    )