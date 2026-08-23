import pytest
from pydantic import ValidationError

from otpilot.config.models import AppConfig


def test_config_rejects_secret_fields() -> None:
    with pytest.raises(ValidationError):
        AppConfig.model_validate({"password": "never-store-this"})


def test_config_has_conservative_watch_poll_default() -> None:
    assert AppConfig().poll_interval_seconds == 30.0
