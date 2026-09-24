"""Non-secret TOML configuration storage."""

from __future__ import annotations

import os
import tomllib
from collections.abc import Mapping
from contextlib import suppress
from pathlib import Path
from typing import Any

import platformdirs
import tomli_w
from pydantic import ValidationError

from otpilot.config.models import AppConfig
from otpilot.domain.errors import ConfigurationError


def dump_toml_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    """Write TOML to `path` via a temporary file so failed writes leave the original intact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        with temporary.open("wb") as handle:
            tomli_w.dump(dict(payload), handle)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except OSError:
        with suppress(OSError):
            temporary.unlink(missing_ok=True)
        raise


def load_toml_mapping(path: Path) -> dict[str, Any]:
    """Return the TOML table at `path`, or an empty mapping when the file is absent."""
    if not path.exists():
        return {}
    with path.open("rb") as handle:
        loaded = tomllib.load(handle)
    if not isinstance(loaded, dict):
        raise tomllib.TOMLDecodeError("TOML document must be a table.", "", 0)
    return loaded


class TomlConfigurationRepository:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path(platformdirs.user_config_path("otpilot")) / "config.toml"

    def load(self) -> AppConfig:
        if not self.path.exists():
            return AppConfig()
        try:
            return AppConfig.model_validate(self.declared_mapping())
        except (OSError, tomllib.TOMLDecodeError, ValidationError, ConfigurationError) as exc:
            raise ConfigurationError("Unable to load OTPilot configuration.") from exc

    def declared_mapping(self) -> dict[str, Any]:
        try:
            return load_toml_mapping(self.path)
        except (OSError, tomllib.TOMLDecodeError) as exc:
            raise ConfigurationError("Unable to load OTPilot configuration.") from exc

    def save(self, config: AppConfig) -> None:
        try:
            dump_toml_atomic(self.path, config.model_dump(mode="json", exclude_none=True))
        except OSError as exc:
            raise ConfigurationError("Unable to save OTPilot configuration.") from exc

    def clear(self) -> None:
        try:
            self.path.unlink(missing_ok=True)
        except OSError as exc:
            raise ConfigurationError("Unable to reset OTPilot configuration.") from exc
