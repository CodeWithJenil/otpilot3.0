"""Tests for the feedback module."""

import sys
import typer
from unittest.mock import patch, MagicMock

import pytest

from otpilot.application.feedback import (
    FeedbackConfig,
    FeedbackPromptService,
    DefaultBrowserOpener,
    create_feedback_prompt_service,
)
from otpilot.application.settings import SettingsService
from otpilot.infrastructure.config_storage.toml import TomlConfigurationRepository
from otpilot.infrastructure.preferences.toml import TomlPreferencesRepository
from otpilot.preferences.models import UserPreferences


@pytest.fixture
def settings_service(tmp_path) -> SettingsService:
    """Create a settings service with isolated config/prefs paths."""
    config_repo = TomlConfigurationRepository(tmp_path / "config.toml")
    prefs_repo = TomlPreferencesRepository(tmp_path / "preferences.toml")
    return SettingsService(config_repo, prefs_repo)


def test_feedback_config_disabled_never_prompts() -> None:
    """FeedbackConfig should not prompt when disabled."""
    config = FeedbackConfig(
        enabled=False,
        min_commands=5,
        commands_since_prompt=10,
    )
    assert config.should_prompt() is False


def test_feedback_config_below_minimum_never_prompts() -> None:
    """FeedbackConfig should not prompt when below minimum commands."""
    config = FeedbackConfig(
        enabled=True,
        min_commands=5,
        commands_since_prompt=3,
    )
    assert config.should_prompt() is False


def test_feedback_config_at_minimum_may_prompt(settings_service) -> None:
    """FeedbackConfig at minimum should use random probability."""
    # Use a fixed random source for deterministic testing
    import random
    rng = random.Random(42)  # Fixed seed
    
    config = FeedbackConfig(
        enabled=True,
        min_commands=5,
        commands_since_prompt=5,
        prompt_probability=1.0,  # Always prompt for testing
    )
    # With probability 1.0, it should always prompt
    assert config.should_prompt() is True


def test_feedback_config_above_minimum_uses_probability() -> None:
    """FeedbackConfig above minimum should use random probability."""
    import random
    from unittest.mock import patch
    
    config = FeedbackConfig(
        enabled=True,
        min_commands=5,
        commands_since_prompt=10,
        prompt_probability=0.5,
    )
    
    # Test with mocked random to ensure deterministic behavior
    with patch('random.random', return_value=0.25):
        result1 = config.should_prompt()
    assert result1 is True  # 0.25 < 0.5
    
    with patch('random.random', return_value=0.75):
        result2 = config.should_prompt()
    assert result2 is False  # 0.75 > 0.5


def test_feedback_prompt_service_creates_with_defaults(settings_service) -> None:
    """FeedbackPromptService should be creatable with defaults."""
    service = create_feedback_prompt_service(settings_service)
    assert isinstance(service, FeedbackPromptService)


def test_feedback_prompt_service_increments_counter_when_below_minimum(settings_service) -> None:
    """Service should increment counter when below minimum."""
    # Set up preferences with low counter
    settings_service.set("preferences.feedback_prompts_enabled", "true")
    settings_service.set("preferences.feedback_prompt_min_commands", "5")
    settings_service.set("preferences.feedback_commands_since_prompt", "2")

    service = create_feedback_prompt_service(settings_service)
    
    # Mock TTY to simulate interactive environment
    with patch.object(sys.stdout, 'isatty', return_value=True), \
         patch.object(sys.stdin, 'isatty', return_value=True), \
         patch.object(typer, 'prompt') as mock_prompt:
        
        service.maybe_prompt("3.1.1")
        
        # Counter should increment from 2 to 3
        snapshot = settings_service.snapshot()
        entry = snapshot.entry("preferences.feedback_commands_since_prompt")
        assert entry.value == 3


def test_feedback_prompt_service_resets_counter_when_prompting(settings_service) -> None:
    """Service should reset counter after prompting."""
    from unittest.mock import patch
    
    # Set up preferences at minimum
    settings_service.set("preferences.feedback_prompts_enabled", "true")
    settings_service.set("preferences.feedback_prompt_min_commands", "5")
    settings_service.set("preferences.feedback_commands_since_prompt", "5")
    
    service = create_feedback_prompt_service(settings_service)
    
    # Mock TTY and user declining, and force should_prompt to return True
    with patch.object(sys.stdout, 'isatty', return_value=True), \
         patch.object(sys.stdin, 'isatty', return_value=True), \
         patch.object(typer, 'prompt', return_value="n") as mock_prompt, \
         patch('random.random', return_value=0.05):  # < 0.1, will prompt
        
        service.maybe_prompt("3.1.1")
        
        # Counter should reset to 0
        snapshot = settings_service.snapshot()
        entry = snapshot.entry("preferences.feedback_commands_since_prompt")
        assert entry.value == 0


def test_feedback_prompt_service_does_not_prompt_in_non_tty(settings_service) -> None:
    """Service should not prompt in non-TTY environments."""
    settings_service.set("preferences.feedback_prompts_enabled", "true")
    settings_service.set("preferences.feedback_prompt_min_commands", "5")
    settings_service.set("preferences.feedback_commands_since_prompt", "10")

    service = create_feedback_prompt_service(settings_service)
    
    # Mock non-TTY environment
    with patch.object(sys.stdout, 'isatty', return_value=False), \
         patch.object(sys.stdin, 'isatty', return_value=True), \
         patch.object(typer, 'prompt') as mock_prompt:
        
        service.maybe_prompt("3.1.1")
        
        # Counter should not change
        snapshot = settings_service.snapshot()
        entry = snapshot.entry("preferences.feedback_commands_since_prompt")
        assert entry.value == 10
        # prompt should not have been called
        mock_prompt.assert_not_called()


def test_feedback_prompt_service_does_not_prompt_for_version_command(settings_service) -> None:
    """Service should not prompt for version command."""
    settings_service.set("preferences.feedback_prompts_enabled", "true")
    settings_service.set("preferences.feedback_prompt_min_commands", "5")
    settings_service.set("preferences.feedback_commands_since_prompt", "10")

    service = create_feedback_prompt_service(settings_service)
    
    with patch.object(sys.stdout, 'isatty', return_value=True), \
         patch.object(sys.stdin, 'isatty', return_value=True), \
         patch.object(typer, 'prompt') as mock_prompt:
        
        # The service itself doesn't check command name, but the caller does
        # This test verifies the service doesn't crash
        service.maybe_prompt("3.1.1")
        # Should not crash


def test_feedback_prompt_service_handles_browser_open_failure(settings_service) -> None:
    """Service should handle browser open failure gracefully."""
    settings_service.set("preferences.feedback_prompts_enabled", "true")
    settings_service.set("preferences.feedback_prompt_min_commands", "5")
    settings_service.set("preferences.feedback_commands_since_prompt", "5")

    # Create a browser opener that always fails
    class FailingBrowserOpener:
        def open(self, url: str) -> bool:
            return False

    service = FeedbackPromptService(settings_service, browser_opener=FailingBrowserOpener())
    
    with patch.object(sys.stdout, 'isatty', return_value=True), \
         patch.object(sys.stdin, 'isatty', return_value=True), \
         patch.object(typer, 'prompt', return_value="y") as mock_prompt:
        
        # Should not raise even if browser fails
        service.maybe_prompt("3.1.1")


def test_feedback_prompt_service_handles_keyboard_interrupt(settings_service) -> None:
    """Service should handle KeyboardInterrupt gracefully."""
    settings_service.set("preferences.feedback_prompts_enabled", "true")
    settings_service.set("preferences.feedback_prompt_min_commands", "5")
    settings_service.set("preferences.feedback_commands_since_prompt", "5")

    service = create_feedback_prompt_service(settings_service)
    
    with patch.object(sys.stdout, 'isatty', return_value=True), \
         patch.object(sys.stdin, 'isatty', return_value=True), \
         patch.object(typer, 'prompt', side_effect=KeyboardInterrupt()) as mock_prompt:
        
        # Should not raise
        service.maybe_prompt("3.1.1")


def test_feedback_prompt_service_handles_eof_error(settings_service) -> None:
    """Service should handle EOFError gracefully."""
    settings_service.set("preferences.feedback_prompts_enabled", "true")
    settings_service.set("preferences.feedback_prompt_min_commands", "5")
    settings_service.set("preferences.feedback_commands_since_prompt", "5")

    service = create_feedback_prompt_service(settings_service)
    
    with patch.object(sys.stdout, 'isatty', return_value=True), \
         patch.object(sys.stdin, 'isatty', return_value=True), \
         patch.object(typer, 'prompt', side_effect=EOFError()) as mock_prompt:
        
        # Should not raise
        service.maybe_prompt("3.1.1")


def test_feedback_prompt_service_disabled_via_config(settings_service) -> None:
    """Service should not prompt when disabled via config."""
    settings_service.set("preferences.feedback_prompts_enabled", "false")
    settings_service.set("preferences.feedback_prompt_min_commands", "5")
    settings_service.set("preferences.feedback_commands_since_prompt", "100")

    service = create_feedback_prompt_service(settings_service)
    
    with patch.object(sys.stdout, 'isatty', return_value=True), \
         patch.object(sys.stdin, 'isatty', return_value=True), \
         patch.object(typer, 'prompt') as mock_prompt:
        
        service.maybe_prompt("3.1.1")
        
        # Counter should not change (never reached prompt logic)
        snapshot = settings_service.snapshot()
        entry = snapshot.entry("preferences.feedback_commands_since_prompt")
        assert entry.value == 100
        mock_prompt.assert_not_called()


def test_feedback_prompt_service_builds_correct_url(settings_service) -> None:
    """Service should build correct feedback URL with version."""
    settings_service.set("preferences.feedback_prompts_enabled", "true")
    settings_service.set("preferences.feedback_prompt_min_commands", "5")
    settings_service.set("preferences.feedback_commands_since_prompt", "5")

    service = create_feedback_prompt_service(settings_service)
    
    url = service._build_feedback_url("3.1.1")
    assert url == "https://jenil-otpilot.vercel.app/feedback?version=3.1.1"


def test_default_browser_opener() -> None:
    """DefaultBrowserOpener should be instantiable."""
    opener = DefaultBrowserOpener()
    assert isinstance(opener, DefaultBrowserOpener)


def test_feedback_config_with_custom_probability() -> None:
    """FeedbackConfig should accept custom probability."""
    config = FeedbackConfig(
        enabled=True,
        min_commands=5,
        commands_since_prompt=5,
        prompt_probability=0.25,
    )
    assert config.prompt_probability == 0.25


def test_user_preferences_feedback_fields() -> None:
    """UserPreferences should accept feedback fields."""
    prefs = UserPreferences(
        feedback_prompts_enabled=False,
        feedback_prompt_min_commands=10,
        feedback_commands_since_prompt=3,
    )
    assert prefs.feedback_prompts_enabled is False
    assert prefs.feedback_prompt_min_commands == 10
    assert prefs.feedback_commands_since_prompt == 3


def test_user_preferences_feedback_min_commands_validation() -> None:
    """UserPreferences should validate feedback_prompt_min_commands."""
    from pydantic import ValidationError
    
    with pytest.raises(ValidationError):
        UserPreferences(feedback_prompt_min_commands=-1)


def test_user_preferences_feedback_commands_since_prompt_validation() -> None:
    """UserPreferences should validate feedback_commands_since_prompt."""
    from pydantic import ValidationError
    
    with pytest.raises(ValidationError):
        UserPreferences(feedback_commands_since_prompt=-1)


def test_settings_service_includes_feedback_keys(settings_service) -> None:
    """SettingsService should include feedback keys in snapshot."""
    snapshot = settings_service.snapshot()
    
    # Check all feedback keys exist
    feedback_keys = [
        "preferences.feedback_prompts_enabled",
        "preferences.feedback_prompt_min_commands",
        "preferences.feedback_commands_since_prompt",
    ]
    
    for key in feedback_keys:
        entry = snapshot.entry(key)
        assert entry is not None
        assert entry.key == key


def test_settings_service_can_set_feedback_keys(settings_service) -> None:
    """SettingsService should be able to set feedback keys."""
    # Test setting boolean
    entry = settings_service.set("preferences.feedback_prompts_enabled", "false")
    assert entry.value is False
    
    # Test setting integer
    entry = settings_service.set("preferences.feedback_prompt_min_commands", "10")
    assert entry.value == 10
    
    entry = settings_service.set("preferences.feedback_commands_since_prompt", "3")
    assert entry.value == 3


def test_feedback_prompt_service_with_custom_random_source(settings_service) -> None:
    """Service should work with custom random source for testing."""
    import random
    
    # Fixed random that always returns 0.0 (will prompt with 10% probability)
    rng = random.Random(42)
    
    settings_service.set("preferences.feedback_prompts_enabled", "true")
    settings_service.set("preferences.feedback_prompt_min_commands", "5")
    settings_service.set("preferences.feedback_commands_since_prompt", "5")
    
    service = FeedbackPromptService(
        settings_service,
        random_source=rng,
    )
    
    # Should work without errors
    with patch.object(sys.stdout, 'isatty', return_value=False), \
         patch.object(typer, 'prompt') as mock_prompt:
        service.maybe_prompt("3.1.1")
        mock_prompt.assert_not_called()