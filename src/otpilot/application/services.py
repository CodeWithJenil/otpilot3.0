"""Application services that keep CLI, providers, and infrastructure decoupled."""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from time import sleep

from otpilot.application.ports import (
    Clipboard,
    ConfigurationRepository,
    CredentialStore,
    NotificationSink,
    OtpCache,
    PreferencesRepository,
)
from otpilot.domain.errors import (
    ClipboardError,
    CredentialError,
    ExtractionError,
    ProviderError,
)
from otpilot.domain.extraction import OtpExtractor
from otpilot.domain.models import AccountId, OtpResult, ProviderId
from otpilot.domain.providers import ProviderRegistry
from otpilot.domain.search import SearchCriteria
from otpilot.domain.state import RuntimeState


@dataclass(slots=True)
class FetchOtpService:
    providers: ProviderRegistry
    cache: OtpCache
    credentials: CredentialStore
    config: ConfigurationRepository
    extractor: OtpExtractor
    clipboard: Clipboard | None = None

    def fetch(
        self,
        criteria: SearchCriteria | None = None,
        *,
        copy_to_clipboard: bool = False,
    ) -> OtpResult:
        active_config = self.config.load()
        account = active_config.provider.account
        if not account:
            raise CredentialError("No email account is configured. Run `otpilot login <email>`.")
        account_id = AccountId(account)
        stored = self.credentials.get_app_password(account_id)
        if stored is None:
            raise CredentialError("No credentials are stored for the configured account.")
        username, app_password = stored
        provider = self.providers.get(ProviderId(active_config.provider.provider_id))
        if provider is None:
            raise ProviderError("The configured email provider is unavailable.")
        active_criteria = criteria or SearchCriteria(since=datetime.now(UTC))
        provider.authenticate(account_id, username, app_password)
        candidates = [
            self.extractor.extract_best(email)
            for email in provider.search(account_id, active_criteria)
        ]
        best = max(
            (candidate for candidate in candidates if candidate is not None),
            key=lambda candidate: (
                candidate.score,
                candidate.source.received_at or datetime.min.replace(tzinfo=UTC),
            ),
            default=None,
        )
        if best is None:
            raise ExtractionError("No valid OTP was found in the matching messages.")
        result = OtpResult(candidate=best)
        if copy_to_clipboard:
            self.copy_result(result)
        self.cache.put(account, result, ttl_seconds=30)
        return result

    def copy_result(self, result: OtpResult) -> None:
        if self.clipboard is None:
            raise ClipboardError("Clipboard support is unavailable.")
        try:
            self.clipboard.copy(result.candidate.value)
        except ClipboardError:
            raise
        except Exception as exc:
            raise ClipboardError("Unable to copy the OTP to the clipboard.") from exc


@dataclass(slots=True)
class WatchService:
    fetch_service: FetchOtpService
    poll_interval_seconds: float = 30.0
    sleep: Callable[[float], None] = field(default=sleep)
    status: Callable[[str], None] = field(default=lambda message: None)

    def run(self) -> None:
        processed_message_ids: set[str] = set()
        self.status("Watching for new OTPs...")
        try:
            while True:
                try:
                    result = self.fetch_service.fetch()
                except ExtractionError:
                    result = None
                except ProviderError as exc:
                    self.status(f"Temporary provider failure; retrying: {exc}")
                    result = None
                if result is not None:
                    message_id = result.candidate.source.message_id
                    if message_id not in processed_message_ids:
                        self.fetch_service.copy_result(result)
                        processed_message_ids.add(message_id)
                        self.status("New OTP copied to clipboard.")
                self.sleep(self.poll_interval_seconds)
        except KeyboardInterrupt:
            self.status("Watch stopped.")


@dataclass(slots=True)
class LoginService:
    credentials: CredentialStore
    config: ConfigurationRepository

    def login(self, email: str, app_password: str) -> None:
        account_id = AccountId(email)
        self.credentials.save_app_password(account_id, email, app_password)
        current = self.config.load()
        current.provider.account = email
        self.config.save(current)


@dataclass(slots=True)
class LogoutService:
    credentials: CredentialStore

    def logout(self, account: str) -> None:
        self.credentials.delete_app_password(AccountId(account))


@dataclass(slots=True)
class SettingsService:
    config: ConfigurationRepository
    preferences: PreferencesRepository


@dataclass(slots=True)
class DoctorService:
    config: ConfigurationRepository

    def inspect(self) -> RuntimeState:
        return RuntimeState(
            authenticated=False,
            connected=False,
            background_running=False,
            provider_available=False,
        )


@dataclass(slots=True)
class ClipboardService:
    clipboard: Clipboard


@dataclass(slots=True)
class NotificationService:
    notifications: NotificationSink
