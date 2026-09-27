"""Tests for telemetry preferences and configuration."""

import pytest
from pydantic import ValidationError

from otpilot.preferences.models import UserPreferences


def test_preferences_default_telemetry_disabled() -> None:
    """Telemetry should be disabled by default."""
    prefs = UserPreferences()
    assert prefs.telemetry_enabled is False
    assert prefs.telemetry_installation_id is None


def test_preferences_accept_telemetry_enabled() -> None:
    """Preferences should accept telemetry_enabled=True."""
    prefs = UserPreferences(telemetry_enabled=True)
    assert prefs.telemetry_enabled is True


def test_preferences_accept_installation_id() -> None:
    """Preferences should accept a telemetry installation ID."""
    installation_id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    prefs = UserPreferences(telemetry_installation_id=installation_id)
    assert prefs.telemetry_installation_id == installation_id


def test_preferences_reject_invalid_installation_id() -> None:
    """Preferences should reject non-UUID installation IDs."""
    with pytest.raises(ValidationError):
        UserPreferences(telemetry_installation_id="not-a-uuid")


def test_preferences_extra_forbidden() -> None:
    """Preferences should forbid extra fields."""
    with pytest.raises(ValidationError):
        UserPreferences(unknown_field="value")


def test_preferences_persist_telemetry_fields(tmp_path) -> None:
    """Telemetry fields should persist through model serialization."""
    installation_id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    prefs = UserPreferences(
        telemetry_enabled=True,
        telemetry_installation_id=installation_id,
    )
    data = prefs.model_dump(mode="json")
    assert data["telemetry_enabled"] is True
    assert data["telemetry_installation_id"] == installation_id

    # Round-trip
    prefs2 = UserPreferences.model_validate(data)
    assert prefs2.telemetry_enabled is True
    assert prefs2.telemetry_installation_id == installation_id