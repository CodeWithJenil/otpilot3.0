"""Application-wide error hierarchy."""

from dataclasses import dataclass


@dataclass(slots=True)
class ErrorContext:
    """Structured, non-secret context safe for diagnostics."""

    code: str
    detail: str | None = None


class OTPilotError(Exception):
    """Base class for all expected OTPilot failures."""

    def __init__(self, message: str, *, context: ErrorContext | None = None) -> None:
        super().__init__(message)
        self.context = context


class FeatureNotImplementedError(OTPilotError):
    """Raised when a scaffolded feature has a stable interface but no behavior yet."""


class ConfigurationError(OTPilotError):
    """Raised for invalid non-secret configuration."""


class PreferenceError(OTPilotError):
    """Raised for invalid user preferences."""


class CredentialError(OTPilotError):
    """Raised for credential backend, lookup, or deletion failures."""


class ProviderError(OTPilotError):
    """Raised when an email provider cannot satisfy a request."""


class ImapTransportError(ProviderError):
    """Raised for IMAP connection, authentication, or protocol failures."""


class ExtractionError(OTPilotError):
    """Raised when OTP extraction cannot produce a usable result."""


class CacheError(OTPilotError):
    """Raised when cache access fails."""


class ClipboardError(OTPilotError):
    """Raised when the local clipboard cannot be updated."""


class BackgroundServiceError(OTPilotError):
    """Raised by watch-mode background services."""
