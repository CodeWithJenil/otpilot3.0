"""Application services and ports."""

from otpilot.application.doctor import DoctorService
from otpilot.application.ports import (
    Clipboard,
    ConfigurationRepository,
    CredentialStore,
    HotkeyListener,
    MutableConfigurationRepository,
    MutablePreferencesRepository,
    NotificationSink,
    OtpCache,
    PlatformDiagnostics,
    PreferencesRepository,
)
from otpilot.application.services import (
    ClipboardService,
    FetchOtpService,
    HotkeyService,
    LoginService,
    LogoutService,
    NotificationService,
    WatchService,
)
from otpilot.application.settings import SettingEntry, SettingsService, SettingsSnapshot
from otpilot.application.telemetry import (
    ALLOWED_COMMAND_EVENTS,
    HttpTelemetryAdapter,
    NoOpTelemetry,
    TelemetryEvent,
    TelemetryPort,
    create_telemetry_adapter,
    generate_installation_id,
    is_command_allowed_for_telemetry,
)

__all__ = [
    "ALLOWED_COMMAND_EVENTS",
    "Clipboard",
    "ClipboardService",
    "ConfigurationRepository",
    "CredentialStore",
    "DoctorService",
    "FetchOtpService",
    "HotkeyListener",
    "HotkeyService",
    "HttpTelemetryAdapter",
    "LoginService",
    "LogoutService",
    "MutableConfigurationRepository",
    "MutablePreferencesRepository",
    "NoOpTelemetry",
    "NotificationService",
    "NotificationSink",
    "OtpCache",
    "PlatformDiagnostics",
    "PreferencesRepository",
    "SettingEntry",
    "SettingsService",
    "SettingsSnapshot",
    "TelemetryEvent",
    "TelemetryPort",
    "WatchService",
    "create_telemetry_adapter",
    "generate_installation_id",
    "is_command_allowed_for_telemetry",
]