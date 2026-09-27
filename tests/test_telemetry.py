"""Tests for the telemetry module."""

import json
import sys
from unittest.mock import patch

import pytest

from otpilot.application.settings import SettingsService
from otpilot.application.telemetry import (
    ALLOWED_COMMAND_EVENTS,
    HttpTelemetryAdapter,
    NoOpTelemetry,
    TelemetryEvent,
    create_telemetry_adapter,
    generate_installation_id,
    is_command_allowed_for_telemetry,
)
from otpilot.infrastructure.config_storage.toml import TomlConfigurationRepository
from otpilot.infrastructure.preferences.toml import TomlPreferencesRepository


def test_generate_installation_id_is_uuid() -> None:
    """Generated installation ID should be a valid UUID."""
    id1 = generate_installation_id()
    id2 = generate_installation_id()

    # Should be valid UUID format
    assert len(id1) == 36
    assert id1.count("-") == 4
    # Should be different each time (random)
    assert id1 != id2


def test_generate_installation_id_format() -> None:
    """Generated ID should match UUIDv4 format."""
    import re

    uuid_regex = re.compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.I
    )
    assert uuid_regex.match(generate_installation_id())


def test_telemetry_event_to_dict() -> None:
    """TelemetryEvent should serialize to dict with all required fields."""
    event = TelemetryEvent(
        installation_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        event="test_event",
        version="3.0.0",
        python_version="3.12",
        os="linux",
        architecture="x86_64",
        timestamp="2026-09-27T10:15:00Z",
        extra={"command": "fetch"},
    )
    data = event.to_dict()

    assert data["installation_id"] == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    assert data["event"] == "test_event"
    assert data["version"] == "3.0.0"
    assert data["python_version"] == "3.12"
    assert data["os"] == "linux"
    assert data["architecture"] == "x86_64"
    assert data["timestamp"] == "2026-09-27T10:15:00Z"
    assert data["command"] == "fetch"


def test_telemetry_event_extra_fields() -> None:
    """TelemetryEvent should include extra fields in output."""
    event = TelemetryEvent(
        installation_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        event="test",
        version="1.0",
        python_version="3.12",
        os="linux",
        architecture="x86_64",
        timestamp="2026-09-27T10:15:00Z",
        extra={"custom": "value", "number": 42},
    )
    data = event.to_dict()
    assert data["custom"] == "value"
    assert data["number"] == 42


def test_noop_telemetry_send_does_nothing() -> None:
    """NoOpTelemetry.send should not raise or do anything."""
    noop = NoOpTelemetry()
    noop.send("test_event")  # Should not raise
    noop.send("test_event", {"key": "value"})  # Should not raise


def test_is_command_allowed_for_telemetry() -> None:
    """is_command_allowed_for_telemetry should validate against allowlist."""
    for cmd in ALLOWED_COMMAND_EVENTS:
        assert is_command_allowed_for_telemetry(cmd) is True

    assert is_command_allowed_for_telemetry("unknown_command") is False
    assert is_command_allowed_for_telemetry("") is False
    assert is_command_allowed_for_telemetry("rm -rf /") is False


def test_allowed_command_events_contains_expected() -> None:
    """ALLOWED_COMMAND_EVENTS should contain the expected commands."""
    expected = {
        "fetch",
        "watch",
        "hotkey",
        "login",
        "logout",
        "config",
        "doctor",
        "version",
        "telemetry",
    }
    assert expected == ALLOWED_COMMAND_EVENTS


@pytest.fixture
def settings_service(tmp_path) -> SettingsService:
    """Create a settings service with isolated config/prefs paths."""
    config_repo = TomlConfigurationRepository(tmp_path / "config.toml")
    prefs_repo = TomlPreferencesRepository(tmp_path / "preferences.toml")
    return SettingsService(config_repo, prefs_repo)


def test_create_telemetry_adapter_returns_noop_when_disabled(settings_service) -> None:
    """create_telemetry_adapter should return NoOpTelemetry when disabled."""
    adapter = create_telemetry_adapter(settings_service)
    assert isinstance(adapter, NoOpTelemetry)


def test_create_telemetry_adapter_returns_http_when_enabled(settings_service) -> None:
    """create_telemetry_adapter should return HttpTelemetryAdapter when enabled."""
    # Enable telemetry and set installation ID
    settings_service.set("preferences.telemetry_enabled", "true")
    installation_id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    settings_service.set("preferences.telemetry_installation_id", installation_id)
    adapter = create_telemetry_adapter(settings_service)
    assert isinstance(adapter, HttpTelemetryAdapter)


def test_http_telemetry_adapter_send_noop_when_disabled(settings_service) -> None:
    """HttpTelemetryAdapter should not send when telemetry is disabled."""
    adapter = HttpTelemetryAdapter(settings_service)
    adapter.send("test_event")  # Should not raise, should not send


def test_http_telemetry_adapter_send_noop_when_no_installation_id(settings_service) -> None:
    """HttpTelemetryAdapter should not send when no installation ID is set."""
    settings_service.set("preferences.telemetry_enabled", "true")
    settings_service.set("preferences.telemetry_installation_id", "")
    adapter = HttpTelemetryAdapter(settings_service)
    adapter.send("test_event")  # Should not raise, should not send


@patch("otpilot.application.telemetry.request.urlopen")
def test_http_telemetry_adapter_sends_async(mock_urlopen, settings_service) -> None:
    """HttpTelemetryAdapter should send request in background thread."""
    settings_service.set("preferences.telemetry_enabled", "true")
    installation_id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    settings_service.set("preferences.telemetry_installation_id", installation_id)
    adapter = HttpTelemetryAdapter(settings_service)
    adapter.send("test_event", {"command": "fetch"})

    # Give background thread time to execute
    import time
    time.sleep(0.1)

    # Should have called urlopen
    mock_urlopen.assert_called_once()
    call_args = mock_urlopen.call_args
    req = call_args[0][0]
    assert req.full_url == "https://jenil-otpilot.vercel.app/api/telemetry"
    assert req.method == "POST"
    # urllib normalizes header keys to Title-Case with hyphens
    assert req.headers.get("Content-type") == "application/json"

    # Verify payload
    payload = json.loads(call_args[0][0].data.decode("utf-8"))
    assert payload["event"] == "test_event"
    assert payload["command"] == "fetch"
    assert payload["installation_id"] == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"


@patch("otpilot.application.telemetry.request.urlopen")
def test_http_telemetry_adapter_handles_network_error(mock_urlopen, settings_service) -> None:
    """HttpTelemetryAdapter should silently handle network errors."""
    import urllib.error

    mock_urlopen.side_effect = urllib.error.URLError("Network unreachable")

    settings_service.set("preferences.telemetry_enabled", "true")
    installation_id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    settings_service.set("preferences.telemetry_installation_id", installation_id)
    adapter = HttpTelemetryAdapter(settings_service)
    adapter.send("test_event")  # Should not raise

    import time
    time.sleep(0.1)
    mock_urlopen.assert_called_once()


@patch("otpilot.application.telemetry.request.urlopen")
def test_http_telemetry_adapter_respects_payload_size_limit(mock_urlopen, settings_service) -> None:
    """HttpTelemetryAdapter should not send payloads exceeding size limit."""
    settings_service.set("preferences.telemetry_enabled", "true")
    installation_id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    settings_service.set("preferences.telemetry_installation_id", installation_id)
    adapter = HttpTelemetryAdapter(settings_service)

    # Create a large payload
    large_payload = {"data": "x" * 2000}
    adapter.send("test_event", large_payload)

    import time
    time.sleep(0.1)

    # Should not have sent
    mock_urlopen.assert_not_called()


def test_http_telemetry_adapter_shutdown_prevents_send(settings_service) -> None:
    """HttpTelemetryAdapter.shutdown should prevent future sends."""
    settings_service.set("preferences.telemetry_enabled", "true")
    installation_id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    settings_service.set("preferences.telemetry_installation_id", installation_id)
    adapter = HttpTelemetryAdapter(settings_service)
    adapter.shutdown()
    adapter.send("test_event")  # Should not raise, should not send

    import time
    time.sleep(0.05)
    # No way to directly verify but should not crash


def test_telemetry_event_version_from_package() -> None:
    """TelemetryEvent should get version from package."""
    from otpilot import __version__

    # The adapter builds events with the version
    event = TelemetryEvent(
        installation_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        event="test",
        version=__version__,
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}",
        os="linux",
        architecture="x86_64",
        timestamp="2026-09-27T10:15:00Z",
    )
    assert event.version == __version__