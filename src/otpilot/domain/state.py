"""Runtime state model for CLI and background service coordination."""

from dataclasses import dataclass

from otpilot.domain.models import ProviderId


@dataclass(frozen=True, slots=True)
class RuntimeState:
    authenticated: bool
    connected: bool
    background_running: bool
    provider_available: bool
    active_provider: ProviderId | None = None

