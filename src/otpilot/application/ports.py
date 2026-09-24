"""Application-layer ports implemented by infrastructure adapters."""

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Protocol

from otpilot.config.models import AppConfig
from otpilot.domain.diagnostics import DiagnosticCheck
from otpilot.domain.models import AccountId, OtpResult
from otpilot.preferences.models import UserPreferences


class CredentialStore(Protocol):
    def save_app_password(self, account_id: AccountId, username: str, app_password: str) -> None:
        """Store an app password in the operating system credential vault."""

    def get_app_password(self, account_id: AccountId) -> tuple[str, str] | None:
        """Return the stored username and app password for an account."""

    def delete_app_password(self, account_id: AccountId) -> None:
        """Remove a stored app password."""


class ConfigurationRepository(Protocol):
    def load(self) -> AppConfig:
        """Load non-secret application configuration."""

    def save(self, config: AppConfig) -> None:
        """Persist non-secret application configuration."""


class MutableConfigurationRepository(ConfigurationRepository, Protocol):
    path: Path

    def declared_mapping(self) -> Mapping[str, object]:
        """Return the raw TOML mapping, or an empty mapping when the file is missing."""

    def clear(self) -> None:
        """Delete the configuration file without touching stored credentials."""


class PreferencesRepository(Protocol):
    def load(self) -> UserPreferences:
        """Load user preferences."""

    def save(self, preferences: UserPreferences) -> None:
        """Persist user preferences."""


class MutablePreferencesRepository(PreferencesRepository, Protocol):
    path: Path

    def declared_mapping(self) -> Mapping[str, object]:
        """Return the raw preferences mapping, or an empty mapping when missing."""

    def clear(self) -> None:
        """Delete the preferences file without touching stored credentials."""


class PlatformDiagnostics(Protocol):
    """Read-only environment probes used by `otpilot doctor`."""

    def environment_checks(self) -> list[DiagnosticCheck]:
        """Python, OS, architecture, and package version checks."""

    def configuration_support_checks(self, config_path: Path) -> list[DiagnosticCheck]:
        """Config directory writability and file permission checks."""

    def keyring_check(self) -> DiagnosticCheck:
        """Credential backend availability without reading stored secrets."""

    def clipboard_check(self) -> DiagnosticCheck:
        """Clipboard backend availability without writing clipboard contents."""

    def hotkey_check(self) -> DiagnosticCheck:
        """Hotkey environment support without registering a listener."""

    def dependency_checks(self) -> list[DiagnosticCheck]:
        """Importability of required runtime dependencies."""


class OtpCache(Protocol):
    def get(self, key: str) -> OtpResult | None:
        """Return a fresh cached OTP result if one exists."""

    def put(self, key: str, result: OtpResult, ttl_seconds: int) -> None:
        """Cache an OTP result for a short time window."""


class Clipboard(Protocol):
    def copy(self, value: str) -> None:
        """Copy a value into the local clipboard."""


class HotkeyListener(Protocol):
    """Register a global hotkey through a platform-specific adapter."""

    def register(self, hotkey: str, callback: Callable[[], None]) -> None:
        """Register the callback for a hotkey."""

    def run(self) -> None:
        """Block until the listener is interrupted."""

    def shutdown(self) -> None:
        """Unregister the hotkey and release listener resources."""


class NotificationSink(Protocol):
    def send(self, title: str, body: str) -> None:
        """Send a local desktop notification."""
