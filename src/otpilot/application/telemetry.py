"""Telemetry abstraction following ports-and-adapters architecture."""

from __future__ import annotations

import json
import platform
import sys
import threading
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol
from urllib import request
from urllib.error import URLError

from otpilot.application.settings import SettingsService
from otpilot.preferences.models import UserPreferences


class TelemetryPort(Protocol):
    """Port for telemetry transmission."""

    def send(self, event: str, payload: dict[str, Any] | None = None) -> None:
        """Send a telemetry event asynchronously."""
        ...


@dataclass(frozen=True)
class TelemetryEvent:
    """A telemetry event with standard fields."""

    installation_id: str
    event: str
    version: str
    python_version: str
    os: str
    architecture: str
    timestamp: str
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = {
            "installation_id": self.installation_id,
            "event": self.event,
            "version": self.version,
            "python_version": self.python_version,
            "os": self.os,
            "architecture": self.architecture,
            "timestamp": self.timestamp,
        }
        if self.extra:
            data.update(self.extra)
        return data


class NoOpTelemetry:
    """No-op telemetry implementation for when telemetry is disabled."""

    def send(self, event: str, payload: dict[str, Any] | None = None) -> None:
        pass


class HttpTelemetryAdapter:
    """HTTP-based telemetry adapter with async, non-blocking transmission."""

    ENDPOINT = "https://jenil-otpilot.vercel.app/api/telemetry"
    CONNECT_TIMEOUT = 2.0  # seconds
    TOTAL_TIMEOUT = 5.0  # seconds
    MAX_PAYLOAD_SIZE = 1024  # bytes

    def __init__(
        self,
        settings_service: SettingsService,
        endpoint: str | None = None,
    ) -> None:
        self._settings = settings_service
        self._endpoint = endpoint or self.ENDPOINT
        self._executor = threading.Thread
        self._shutdown = False

    def send(self, event: str, payload: dict[str, Any] | None = None) -> None:
        """Send telemetry event asynchronously."""
        if self._shutdown:
            return

        # Get installation ID from preferences
        prefs = self._get_preferences()
        if not prefs.telemetry_enabled:
            return

        installation_id = prefs.telemetry_installation_id
        if not installation_id:
            # Should not happen if enable flow is correct, but guard anyway
            return

        # Build event
        telemetry_event = self._build_event(installation_id, event, payload)
        event_data = telemetry_event.to_dict()

        # Validate payload size
        json_data = json.dumps(event_data, separators=(",", ":")).encode("utf-8")
        if len(json_data) > self.MAX_PAYLOAD_SIZE:
            return

        # Dispatch in background thread
        thread = self._executor(target=self._send_async, args=(json_data,), daemon=True)
        thread.start()

    def _get_preferences(self) -> UserPreferences:
        """Get current preferences from settings service."""
        snapshot = self._settings.snapshot()
        entry = snapshot.entry("preferences")
        if entry.value is None:
            return UserPreferences()
        return entry.value  # type: ignore[return-value]

    def _build_event(
        self,
        installation_id: str,
        event: str,
        payload: dict[str, Any] | None,
    ) -> TelemetryEvent:
        """Build a telemetry event with standard fields."""
        return TelemetryEvent(
            installation_id=installation_id,
            event=event,
            version=self._get_version(),
            python_version=f"{sys.version_info.major}.{sys.version_info.minor}",
            os=self._get_os_name(),
            architecture=platform.machine().lower(),
            timestamp=datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
            extra=payload or {},
        )

    def _get_version(self) -> str:
        """Get OTPilot version."""
        try:
            from otpilot import __version__
            return __version__
        except Exception:
            return "unknown"

    def _get_os_name(self) -> str:
        """Normalize OS name."""
        system = platform.system().lower()
        if system == "darwin":
            return "macos"
        return system

    def _send_async(self, json_data: bytes) -> None:
        """Send HTTP request in background thread."""
        if self._shutdown:
            return

        req = request.Request(
            self._endpoint,
            data=json_data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": f"otpilot/{self._get_version()}",
            },
            method="POST",
        )

        try:
            # Use urllib with timeout
            with request.urlopen(req, timeout=self.CONNECT_TIMEOUT) as response:
                # Read and discard response to avoid resource warnings
                response.read()
        except (URLError, TimeoutError, OSError, ValueError):
            # Silently ignore all network errors - telemetry must never break OTPilot
            pass

    def shutdown(self) -> None:
        """Signal shutdown to prevent new sends."""
        self._shutdown = True


def create_telemetry_adapter(
    settings_service: SettingsService, endpoint: str | None = None
) -> TelemetryPort:
    """Factory to create the appropriate telemetry adapter based on configuration."""
    prefs = _get_preferences_from_settings(settings_service)
    if not prefs.telemetry_enabled:
        return NoOpTelemetry()
    return HttpTelemetryAdapter(settings_service, endpoint)


def _get_preferences_from_settings(settings_service: SettingsService) -> UserPreferences:
    """Extract preferences from settings service."""
    snapshot = settings_service.snapshot()
    entry = snapshot.entry("preferences")
    if entry.value is None:
        return UserPreferences()
    return entry.value  # type: ignore[return-value]


def generate_installation_id() -> str:
    """Generate a cryptographically random installation ID."""
    return str(uuid.uuid4())


ALLOWED_COMMAND_EVENTS = {
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


def is_command_allowed_for_telemetry(command: str) -> bool:
    """Check if a command name is in the allowlist for telemetry."""
    return command in ALLOWED_COMMAND_EVENTS