"""Non-secret TOML configuration storage."""

import tomllib
from pathlib import Path

import platformdirs
import tomli_w
from pydantic import ValidationError

from otpilot.config.models import AppConfig
from otpilot.domain.errors import ConfigurationError


class TomlConfigurationRepository:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path(platformdirs.user_config_path("otpilot")) / "config.toml"

    def load(self) -> AppConfig:
        if not self.path.exists():
            return AppConfig()
        try:
            with self.path.open("rb") as config_file:
                return AppConfig.model_validate(tomllib.load(config_file))
        except (OSError, tomllib.TOMLDecodeError, ValidationError) as exc:
            raise ConfigurationError("Unable to load OTPilot configuration.") from exc

    def save(self, config: AppConfig) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("wb") as config_file:
                tomli_w.dump(config.model_dump(mode="json", exclude_none=True), config_file)
        except OSError as exc:
            raise ConfigurationError("Unable to save OTPilot configuration.") from exc
