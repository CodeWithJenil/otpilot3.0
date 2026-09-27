"""User-facing preferences that do not affect provider correctness."""

import re

from pydantic import BaseModel, ConfigDict, field_validator


class UserPreferences(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hotkey: str | None = None
    theme: str = "system"
    notifications_enabled: bool = True
    auto_paste_enabled: bool = False
    telemetry_enabled: bool = False
    telemetry_installation_id: str | None = None

    @field_validator("telemetry_installation_id")
    @classmethod
    def validate_installation_id(cls, value: str | None) -> str | None:
        """Validate installation ID is a valid UUID format."""
        if value is None:
            return None
        uuid_regex = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I
        )
        if not uuid_regex.match(value):
            raise ValueError("Installation ID must be a valid UUID")
        return value