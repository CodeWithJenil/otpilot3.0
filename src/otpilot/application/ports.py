"""Application-layer ports implemented by infrastructure adapters."""

from typing import Protocol

from otpilot.config.models import AppConfig
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


class PreferencesRepository(Protocol):
    def load(self) -> UserPreferences:
        """Load user preferences."""

    def save(self, preferences: UserPreferences) -> None:
        """Persist user preferences."""


class OtpCache(Protocol):
    def get(self, key: str) -> OtpResult | None:
        """Return a fresh cached OTP result if one exists."""

    def put(self, key: str, result: OtpResult, ttl_seconds: int) -> None:
        """Cache an OTP result for a short time window."""


class Clipboard(Protocol):
    def copy(self, value: str) -> None:
        """Copy a value into the local clipboard."""


class NotificationSink(Protocol):
    def send(self, title: str, body: str) -> None:
        """Send a local desktop notification."""
