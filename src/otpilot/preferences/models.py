"""User-facing preferences that do not affect provider correctness."""

from pydantic import BaseModel, ConfigDict


class UserPreferences(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hotkey: str | None = None
    theme: str = "system"
    notifications_enabled: bool = True
    auto_paste_enabled: bool = False

