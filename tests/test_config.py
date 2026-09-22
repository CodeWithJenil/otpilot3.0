import pytest
from pydantic import ValidationError

from otpilot.config.models import AppConfig
from otpilot.infrastructure.config_storage.toml import TomlConfigurationRepository


def test_config_rejects_secret_fields() -> None:
    with pytest.raises(ValidationError):
        AppConfig.model_validate({"password": "never-store-this"})


def test_config_has_conservative_watch_poll_default() -> None:
    assert AppConfig().poll_interval_seconds == 30.0


def test_config_has_default_hotkey() -> None:
    assert AppConfig().hotkey == "ctrl+shift+o"


def test_config_accepts_custom_hotkey() -> None:
    assert AppConfig(hotkey="Alt+F9").hotkey == "alt+f9"


def test_config_normalizes_hotkey_case_and_whitespace() -> None:
    assert AppConfig(hotkey=" Control + Shift + O ").hotkey == "ctrl+shift+o"


@pytest.mark.parametrize("hotkey", ["", "   ", "ctrl++o", "ctrl+shift"])
def test_config_rejects_invalid_hotkey(hotkey: str) -> None:
    with pytest.raises(ValidationError):
        AppConfig(hotkey=hotkey)


def test_toml_configuration_persists_custom_hotkey(tmp_path) -> None:
    repository = TomlConfigurationRepository(tmp_path / "config.toml")
    repository.save(AppConfig(hotkey="alt+f9"))

    assert repository.load().hotkey == "alt+f9"
