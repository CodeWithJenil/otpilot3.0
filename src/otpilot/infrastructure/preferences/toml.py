"""Non-secret TOML preference storage."""

import tomllib
from pathlib import Path
from typing import Any

import platformdirs
from pydantic import ValidationError

from otpilot.domain.errors import PreferenceError
from otpilot.infrastructure.config_storage.toml import dump_toml_atomic, load_toml_mapping
from otpilot.preferences.models import UserPreferences


class TomlPreferencesRepository:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path(platformdirs.user_config_path("otpilot")) / "preferences.toml"

    def load(self) -> UserPreferences:
        if not self.path.exists():
            return UserPreferences()
        try:
            return UserPreferences.model_validate(self.declared_mapping())
        except (OSError, tomllib.TOMLDecodeError, ValidationError, PreferenceError) as exc:
            raise PreferenceError("Unable to load OTPilot preferences.") from exc

    def declared_mapping(self) -> dict[str, Any]:
        try:
            return load_toml_mapping(self.path)
        except (OSError, tomllib.TOMLDecodeError) as exc:
            raise PreferenceError("Unable to load OTPilot preferences.") from exc

    def save(self, preferences: UserPreferences) -> None:
        try:
            dump_toml_atomic(self.path, preferences.model_dump(mode="json", exclude_none=True))
        except OSError as exc:
            raise PreferenceError("Unable to save OTPilot preferences.") from exc

    def clear(self) -> None:
        try:
            self.path.unlink(missing_ok=True)
        except OSError as exc:
            raise PreferenceError("Unable to reset OTPilot preferences.") from exc
