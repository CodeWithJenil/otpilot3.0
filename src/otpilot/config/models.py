"""Non-secret application configuration."""

import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _validate_hotkey(value: str) -> str:
    parts = [part.strip().lower() for part in value.split("+")]
    if not value.strip() or any(not part for part in parts):
        raise ValueError("Hotkey must not be empty.")
    aliases = {"control": "ctrl", "windows": "win"}
    normalized = [aliases.get(part, part) for part in parts]
    modifiers = {"alt", "ctrl", "shift", "win"}
    if len(normalized) < 2 or normalized[-1] in modifiers:
        raise ValueError("Hotkey must include one or more modifiers and a non-modifier key.")
    if any(part not in modifiers for part in normalized[:-1]) or len(set(normalized)) != len(
        normalized
    ):
        raise ValueError("Hotkey modifiers must be unique and precede the final key.")
    if not re.fullmatch(
        r"(?:[a-z0-9]|f(?:[1-9]|1[0-9]|2[0-4])|space|enter|tab|esc)", normalized[-1]
    ):
        raise ValueError(
            "Hotkey final key must be a letter, digit, supported function key, or named key."
        )
    return "+".join(normalized)


class ProviderConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_id: str = "gmail"
    account: str | None = None


class CredentialBackendConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    backend: str = "windows-credential-manager"


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: ProviderConfig = Field(default_factory=ProviderConfig)
    credential_backend: CredentialBackendConfig = Field(default_factory=CredentialBackendConfig)
    config_dir: Path | None = None
    poll_interval_seconds: float = Field(default=30.0, gt=0, le=3600)
    hotkey: str = "ctrl+shift+o"

    @field_validator("hotkey")
    @classmethod
    def validate_hotkey(cls, value: str) -> str:
        """Accept a safe, keyboard-library-compatible key combination."""
        return _validate_hotkey(value)
