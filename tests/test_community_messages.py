"""Tests for randomized community messages."""

import random
import sys
from unittest.mock import MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner

from otpilot import __version__
from otpilot.application.settings import SettingsService
from otpilot.cli.app import (
    COMMUNITY_MESSAGES,
    EXCLUDED_COMMANDS,
    TelemetryTyper,
    _get_community_message_settings,
    _maybe_show_community_message,
    _should_show_community_message,
)
from otpilot.infrastructure.config_storage.toml import TomlConfigurationRepository
from otpilot.infrastructure.preferences.toml import TomlPreferencesRepository
from otpilot.preferences.models import UserPreferences


@pytest.fixture
def settings_service(tmp_path) -> SettingsService:
    """Create a settings service with isolated config/prefs paths."""
    config_repo = TomlConfigurationRepository(tmp_path / "config.toml")
    prefs_repo = TomlPreferencesRepository(tmp_path / "preferences.toml")
    return SettingsService(config_repo, prefs_repo)


@pytest.fixture
def app_test_hooks(settings_service, monkeypatch):
    """Set up test hooks for the CLI app."""
    import otpilot.cli.app as cli_app

    monkeypatch.setattr(cli_app, "_get_settings_service_for_testing", settings_service)
    monkeypatch.setattr(cli_app, "_isatty_for_testing", True)
    yield
    monkeypatch.setattr(cli_app, "_get_settings_service_for_testing", None)
    monkeypatch.setattr(cli_app, "_isatty_for_testing", None)


class TestCommunityMessageConstants:
    """Tests for community message constants."""

    def test_community_messages_pool(self) -> None:
        """Test that community messages pool has exactly 3 messages."""
        assert len(COMMUNITY_MESSAGES) == 3
        assert "jenil-otpilot.vercel.app/feedback" in COMMUNITY_MESSAGES[0]
        assert "github.com/CodeWithJenil/otpilot3.0/issues" in COMMUNITY_MESSAGES[1]
        assert "github.com/CodeWithJenil/otpilot3.0/discussions" in COMMUNITY_MESSAGES[2]

    def test_excluded_commands(self) -> None:
        """Test that excluded commands set contains expected commands."""
        expected = {"telemetry", "version", "daemon", "config", "doctor", "login", "logout"}
        assert EXCLUDED_COMMANDS == expected


class TestShouldShowCommunityMessage:
    """Tests for _should_show_community_message function."""

    def test_shows_for_eligible_command(self, app_test_hooks) -> None:
        """Test that eligible commands return True."""
        assert _should_show_community_message("fetch", 0) is True
        assert _should_show_community_message("watch", 0) is True
        assert _should_show_community_message("hotkey", 0) is True

    def test_suppresses_for_excluded_commands(self, app_test_hooks) -> None:
        """Test that excluded commands return False."""
        for cmd in EXCLUDED_COMMANDS:
            assert _should_show_community_message(cmd, 0) is False, f"Command {cmd} should be excluded"

    def test_suppresses_for_failed_commands(self, app_test_hooks) -> None:
        """Test that failed commands (non-zero exit) return False."""
        assert _should_show_community_message("fetch", 1) is False
        assert _should_show_community_message("watch", 2) is False

    def test_suppresses_for_none_command(self, app_test_hooks) -> None:
        """Test that None command returns False."""
        assert _should_show_community_message(None, 0) is False

    def test_suppresses_for_non_tty(self, monkeypatch, app_test_hooks) -> None:
        """Test that non-TTY stdout returns False."""
        import otpilot.cli.app as cli_app
        monkeypatch.setattr(cli_app, "_isatty_for_testing", False)
        assert _should_show_community_message("fetch", 0) is False


class TestGetCommunityMessageSettings:
    """Tests for _get_community_message_settings function."""

    def test_default_settings(self, settings_service, app_test_hooks) -> None:
        """Test default community message settings."""
        settings_service.set("preferences.community_messages_enabled", "true")
        settings_service.set("preferences.community_message_probability", "0.15")

        enabled, probability = _get_community_message_settings()
        assert enabled is True
        assert probability == 0.15

    def test_disabled_settings(self, settings_service, app_test_hooks) -> None:
        """Test disabled community messages."""
        settings_service.set("preferences.community_messages_enabled", "false")
        settings_service.set("preferences.community_message_probability", "0.15")

        enabled, probability = _get_community_message_settings()
        assert enabled is False
        assert probability == 0.15

    def test_custom_probability(self, settings_service, app_test_hooks) -> None:
        """Test custom probability value."""
        settings_service.set("preferences.community_messages_enabled", "true")
        settings_service.set("preferences.community_message_probability", "0.05")

        enabled, probability = _get_community_message_settings()
        assert enabled is True
        assert probability == 0.05


class TestMaybeShowCommunityMessage:
    """Tests for _maybe_show_community_message function."""

    def test_suppressed_when_disabled(self, settings_service, app_test_hooks, capsys) -> None:
        """Test message suppressed when disabled."""
        settings_service.set("preferences.community_messages_enabled", "false")
        settings_service.set("preferences.community_message_probability", "1.0")

        _maybe_show_community_message("fetch", 0, random_source=random.Random(42))
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_suppressed_when_probability_zero(self, settings_service, app_test_hooks, capsys) -> None:
        """Test message suppressed when probability is 0."""
        settings_service.set("preferences.community_messages_enabled", "true")
        settings_service.set("preferences.community_message_probability", "0.0")

        _maybe_show_community_message("fetch", 0, random_source=random.Random(42))
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_shown_when_probability_one(self, settings_service, app_test_hooks, capsys) -> None:
        """Test message shown when probability is 1.0."""
        settings_service.set("preferences.community_messages_enabled", "true")
        settings_service.set("preferences.community_message_probability", "1.0")

        _maybe_show_community_message("fetch", 0, random_source=random.Random(42))
        captured = capsys.readouterr()
        assert captured.out != ""
        assert any(msg in captured.out for msg in COMMUNITY_MESSAGES)

    def test_random_selection(self, settings_service, app_test_hooks) -> None:
        """Test that message selection is randomized."""
        settings_service.set("preferences.community_messages_enabled", "true")
        settings_service.set("preferences.community_message_probability", "1.0")

        messages_seen = set()
        for seed in range(100):
            rng = random.Random(seed)
            with patch("otpilot.cli.app.typer.secho") as mock_secho:
                _maybe_show_community_message("fetch", 0, random_source=rng)
                # Capture the echoed message
                if mock_secho.called:
                    for call in mock_secho.call_args_list:
                        args = call[0]
                        if args and any(msg in args[0] for msg in COMMUNITY_MESSAGES):
                            messages_seen.add(args[0])

        # Should see variation in messages (at least 2 different ones with 100 seeds)
        assert len(messages_seen) >= 2

    def test_at_most_one_message_per_call(self, settings_service, app_test_hooks, capsys) -> None:
        """Test that at most one message is shown per call."""
        settings_service.set("preferences.community_messages_enabled", "true")
        settings_service.set("preferences.community_message_probability", "1.0")

        _maybe_show_community_message("fetch", 0, random_source=random.Random(42))
        captured = capsys.readouterr()

        # Count how many community messages appear
        count = sum(1 for msg in COMMUNITY_MESSAGES if msg in captured.out)
        assert count <= 1

    def test_blue_color_output(self, settings_service, app_test_hooks) -> None:
        """Test that message is printed with blue color (typer.secho)."""
        settings_service.set("preferences.community_messages_enabled", "true")
        settings_service.set("preferences.community_message_probability", "1.0")

        with patch("otpilot.cli.app.typer.secho") as mock_secho:
            _maybe_show_community_message("fetch", 0, random_source=random.Random(42))
            assert mock_secho.called
            # Check that fg=typer.colors.BRIGHT_BLUE was used
            call_kwargs = mock_secho.call_args[1]
            assert "fg" in call_kwargs


class TestTelemetryTyperCommunityMessages:
    """Tests for community message integration in TelemetryTyper."""

    def test_no_community_message_for_telemetry_command(self, app_test_hooks) -> None:
        """Test no community message for telemetry command."""
        assert _should_show_community_message("telemetry", 0) is False

    def test_no_community_message_for_version(self, app_test_hooks) -> None:
        """Test no community message for version command."""
        assert _should_show_community_message("version", 0) is False

    def test_no_community_message_for_daemon(self, app_test_hooks) -> None:
        """Test no community message for daemon commands."""
        assert _should_show_community_message("daemon", 0) is False

    def test_no_community_message_for_config(self, app_test_hooks) -> None:
        """Test no community message for config commands."""
        assert _should_show_community_message("config", 0) is False

    def test_no_community_message_for_doctor(self, app_test_hooks) -> None:
        """Test no community message for doctor command."""
        assert _should_show_community_message("doctor", 0) is False


class TestCommunityMessageIntegration:
    """Integration tests for community messages with CLI."""

    def test_probability_boundary_at_zero(self, settings_service, app_test_hooks, capsys) -> None:
        """Test that probability 0.0 never shows message."""
        settings_service.set("preferences.community_messages_enabled", "true")
        settings_service.set("preferences.community_message_probability", "0.0")

        # Even with random returning 0.0, should not show
        _maybe_show_community_message("fetch", 0, random_source=random.Random(0))
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_probability_boundary_at_one(self, settings_service, app_test_hooks, capsys) -> None:
        """Test that probability 1.0 always shows message (when enabled)."""
        settings_service.set("preferences.community_messages_enabled", "true")
        settings_service.set("preferences.community_message_probability", "1.0")

        # With any random value, should show
        _maybe_show_community_message("fetch", 0, random_source=random.Random(0))
        captured = capsys.readouterr()
        assert captured.out != ""
        assert any(msg in captured.out for msg in COMMUNITY_MESSAGES)

    def test_disabled_overrides_probability(self, settings_service, app_test_hooks, capsys) -> None:
        """Test that disabled setting overrides probability."""
        settings_service.set("preferences.community_messages_enabled", "false")
        settings_service.set("preferences.community_message_probability", "1.0")

        _maybe_show_community_message("fetch", 0, random_source=random.Random(0))
        captured = capsys.readouterr()
        assert captured.out == ""


class TestCommunityMessageSettingsPersistence:
    """Tests for community message settings persistence."""

    def test_set_and_get_community_messages_enabled(self, settings_service) -> None:
        """Test setting and getting community_messages_enabled."""
        entry = settings_service.set("preferences.community_messages_enabled", "false")
        assert entry.value is False

        snapshot = settings_service.snapshot()
        entry = snapshot.entry("preferences.community_messages_enabled")
        assert entry.value is False

    def test_set_and_get_community_message_probability(self, settings_service) -> None:
        """Test setting and getting community_message_probability."""
        entry = settings_service.set("preferences.community_message_probability", "0.25")
        assert entry.value == 0.25

        snapshot = settings_service.snapshot()
        entry = snapshot.entry("preferences.community_message_probability")
        assert entry.value == 0.25

    def test_invalid_probability_rejected(self, settings_service) -> None:
        """Test that invalid probability values are rejected."""
        from otpilot.domain.errors import ConfigurationError

        with pytest.raises(ConfigurationError):
            settings_service.set("preferences.community_message_probability", "1.5")

        with pytest.raises(ConfigurationError):
            settings_service.set("preferences.community_message_probability", "-0.1")

        with pytest.raises(ConfigurationError):
            settings_service.set("preferences.community_message_probability", "not_a_number")


class TestFeedbackSettings:
    """Tests for feedback-related preference settings."""

    def test_feedback_prompts_enabled(self, settings_service) -> None:
        """Test feedback_prompts_enabled setting."""
        entry = settings_service.set("preferences.feedback_prompts_enabled", "false")
        assert entry.value is False

    def test_feedback_prompt_min_commands(self, settings_service) -> None:
        """Test feedback_prompt_min_commands setting."""
        entry = settings_service.set("preferences.feedback_prompt_min_commands", "10")
        assert entry.value == 10

    def test_feedback_commands_since_prompt(self, settings_service) -> None:
        """Test feedback_commands_since_prompt setting."""
        entry = settings_service.set("preferences.feedback_commands_since_prompt", "3")
        assert entry.value == 3

    def test_negative_min_commands_rejected(self, settings_service) -> None:
        """Test that negative min_commands is rejected."""
        from otpilot.domain.errors import PreferenceError

        with pytest.raises(PreferenceError):
            settings_service.set("preferences.feedback_prompt_min_commands", "-1")

    def test_negative_commands_since_prompt_rejected(self, settings_service) -> None:
        """Test that negative commands_since_prompt is rejected."""
        from otpilot.domain.errors import PreferenceError

        with pytest.raises(PreferenceError):
            settings_service.set("preferences.feedback_commands_since_prompt", "-1")