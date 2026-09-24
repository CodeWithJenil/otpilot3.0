"""Non-secret configuration and preference management."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import ValidationError

from otpilot.application.ports import MutableConfigurationRepository, MutablePreferencesRepository
from otpilot.config.models import AppConfig
from otpilot.domain.errors import ConfigurationError, PreferenceError
from otpilot.preferences.models import UserPreferences

SettingSource = Literal["configured", "default", "unset", "derived"]

CONFIG_KEYS = (
    "provider.provider_id",
    "provider.account",
    "credential_backend.backend",
    "config_dir",
    "poll_interval_seconds",
    "hotkey",
)
PREFERENCE_KEYS = (
    "preferences.theme",
    "preferences.notifications_enabled",
    "preferences.auto_paste_enabled",
)
SUPPORTED_KEYS = CONFIG_KEYS + PREFERENCE_KEYS
SETTABLE_KEYS = tuple(key for key in SUPPORTED_KEYS if key != "config_dir")
_SECRET_TOKENS = {"password", "app_password", "token", "secret", "otp", "credentials"}
_KNOWN_PROVIDERS = {"gmail"}
_KNOWN_CREDENTIAL_BACKENDS = {"keyring"}


@dataclass(frozen=True, slots=True)
class SettingEntry:
    key: str
    value: object
    source: SettingSource
    redacted: bool = False

    def display_value(self) -> str:
        if self.redacted:
            return "********"
        if self.value is None:
            return "<unset>"
        if isinstance(self.value, bool):
            return "true" if self.value else "false"
        if isinstance(self.value, Path):
            return str(self.value)
        return str(self.value)


@dataclass(frozen=True, slots=True)
class SettingsSnapshot:
    config_path: Path
    preferences_path: Path
    config_exists: bool
    preferences_exists: bool
    entries: tuple[SettingEntry, ...]

    def entry(self, key: str) -> SettingEntry:
        for item in self.entries:
            if item.key == key:
                return item
        raise ConfigurationError(f"Unknown configuration key '{key}'.")


def _flatten(mapping: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    flattened: dict[str, Any] = {}
    for key, value in mapping.items():
        dotted = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, dict):
            flattened.update(_flatten(value, dotted))
        else:
            flattened[dotted] = value
    return flattened


def _is_secret_key(key: str) -> bool:
    parts = key.lower().split(".")
    return any(
        part in _SECRET_TOKENS or part.endswith("_password") or part.endswith("_token")
        for part in parts
    )


def _format_validation_error(exc: ValidationError) -> str:
    parts: list[str] = []
    for error in exc.errors():
        location = ".".join(str(item) for item in error.get("loc", ()))
        message = str(error.get("msg", "invalid value"))
        parts.append(f"{location}: {message}" if location else message)
    return "; ".join(parts) or "Invalid configuration value."


def _parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes", "on"}:
        return True
    if normalized in {"false", "0", "no", "off"}:
        return False
    raise ConfigurationError("Expected a boolean value (true/false).")


def _parse_value(key: str, value: str) -> object:
    if key == "poll_interval_seconds":
        try:
            return float(value)
        except ValueError as exc:
            raise ConfigurationError("poll_interval_seconds must be a number of seconds.") from exc
    if key == "provider.account":
        stripped = value.strip()
        return stripped or None
    if key == "provider.provider_id":
        provider_id = value.strip().lower()
        if provider_id not in _KNOWN_PROVIDERS:
            raise ConfigurationError(
                "Unsupported provider. The current release supports: gmail."
            )
        return provider_id
    if key == "credential_backend.backend":
        backend = value.strip().lower()
        if backend not in _KNOWN_CREDENTIAL_BACKENDS:
            raise ConfigurationError("Unsupported credential backend. Use 'keyring'.")
        return backend
    if key in {"preferences.notifications_enabled", "preferences.auto_paste_enabled"}:
        return _parse_bool(value)
    if key == "preferences.theme":
        theme = value.strip().lower()
        if theme not in {"system", "light", "dark"}:
            raise ConfigurationError("theme must be one of: system, light, dark.")
        return theme
    if key == "hotkey":
        return value
    raise ConfigurationError(f"Unknown configuration key '{key}'.")


def _nested_set(data: dict[str, Any], dotted_key: str, value: object) -> None:
    parts = dotted_key.split(".")
    cursor: dict[str, Any] = data
    for part in parts[:-1]:
        nested = cursor.get(part)
        if not isinstance(nested, dict):
            nested = {}
            cursor[part] = nested
        cursor = nested
    cursor[parts[-1]] = value


@dataclass(slots=True)
class SettingsService:
    config: MutableConfigurationRepository
    preferences: MutablePreferencesRepository

    def snapshot(self) -> SettingsSnapshot:
        config = self.config.load()
        preferences = self.preferences.load()
        declared_config = _flatten(dict(self.config.declared_mapping()))
        declared_preferences = {
            f"preferences.{key}": value
            for key, value in _flatten(dict(self.preferences.declared_mapping())).items()
        }
        values: dict[str, object] = {
            "provider.provider_id": config.provider.provider_id,
            "provider.account": config.provider.account,
            "credential_backend.backend": config.credential_backend.backend,
            "config_dir": config.config_dir or self.config.path.parent,
            "poll_interval_seconds": config.poll_interval_seconds,
            "hotkey": config.hotkey,
            "preferences.theme": preferences.theme,
            "preferences.notifications_enabled": preferences.notifications_enabled,
            "preferences.auto_paste_enabled": preferences.auto_paste_enabled,
        }
        entries: list[SettingEntry] = []
        for key in SUPPORTED_KEYS:
            source: SettingSource
            if key == "config_dir" and "config_dir" not in declared_config:
                source = "derived"
            elif key.startswith("preferences."):
                source = "configured" if key in declared_preferences else "default"
            elif key in declared_config:
                source = "configured"
            elif values[key] is None:
                source = "unset"
            else:
                source = "default"
            entries.append(
                SettingEntry(
                    key=key,
                    value=values[key],
                    source=source,
                    redacted=_is_secret_key(key),
                )
            )
        return SettingsSnapshot(
            config_path=self.config.path,
            preferences_path=self.preferences.path,
            config_exists=self.config.path.exists(),
            preferences_exists=self.preferences.path.exists(),
            entries=tuple(entries),
        )

    def get(self, key: str | None = None) -> SettingsSnapshot | SettingEntry:
        snapshot = self.snapshot()
        if key is None:
            return snapshot
        if key not in SUPPORTED_KEYS:
            raise ConfigurationError(
                f"Unknown configuration key '{key}'. Supported keys: {', '.join(SUPPORTED_KEYS)}."
            )
        return snapshot.entry(key)

    def set(self, key: str, value: str) -> SettingEntry:
        if key not in SETTABLE_KEYS:
            if key == "config_dir":
                raise ConfigurationError(
                    "config_dir is derived from the platform config path and cannot be changed "
                    "with `otpilot config set`. Use `otpilot config path` to view it."
                )
            raise ConfigurationError(
                f"Unknown configuration key '{key}'. Supported keys: {', '.join(SETTABLE_KEYS)}."
            )
        parsed = _parse_value(key, value)
        if key.startswith("preferences."):
            return self._set_preference(key, parsed)
        return self._set_config(key, parsed)

    def _set_config(self, key: str, parsed: object) -> SettingEntry:
        current = self.config.load()
        payload = current.model_dump(mode="python")
        _nested_set(payload, key, parsed)
        try:
            updated = AppConfig.model_validate(payload)
        except ValidationError as exc:
            raise ConfigurationError(_format_validation_error(exc)) from exc
        self.config.save(updated)
        return SettingEntry(
            key=key,
            value=parsed,
            source="configured",
            redacted=_is_secret_key(key),
        )

    def _set_preference(self, key: str, parsed: object) -> SettingEntry:
        field = key.removeprefix("preferences.")
        current = self.preferences.load()
        payload = current.model_dump(mode="python")
        payload[field] = parsed
        try:
            updated = UserPreferences.model_validate(payload)
        except ValidationError as exc:
            raise PreferenceError(_format_validation_error(exc)) from exc
        self.preferences.save(updated)
        return SettingEntry(
            key=key,
            value=parsed,
            source="configured",
            redacted=_is_secret_key(key),
        )

    def reset(self) -> None:
        self.config.clear()
        self.preferences.clear()
