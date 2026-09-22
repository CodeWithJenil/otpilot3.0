"""Application services that keep CLI, providers, and infrastructure decoupled."""

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import Lock
from time import sleep

from otpilot.application.ports import (
    Clipboard,
    ConfigurationRepository,
    CredentialStore,
    HotkeyListener,
    NotificationSink,
    OtpCache,
    PreferencesRepository,
)
from otpilot.domain.errors import (
    ClipboardError,
    CredentialError,
    ExtractionError,
    OTPilotError,
    ProviderError,
)
from otpilot.domain.extraction import OtpExtractor
from otpilot.domain.models import AccountId, OtpResult, ProviderId
from otpilot.domain.providers import ProviderRegistry
from otpilot.domain.search import SearchCriteria
from otpilot.domain.state import RuntimeState


def _received_at_sort_key(received_at: datetime | None) -> datetime:
    if received_at is None:
        return datetime.min.replace(tzinfo=UTC)
    if received_at.tzinfo is None:
        return received_at.replace(tzinfo=UTC)
    return received_at.astimezone(UTC)


@dataclass(slots=True)
class FetchOtpService:
    providers: ProviderRegistry
    cache: OtpCache
    credentials: CredentialStore
    config: ConfigurationRepository
    extractor: OtpExtractor
    clipboard: Clipboard | None = None

    def validate_ready(self) -> None:
        """Verify non-network prerequisites required to fetch an OTP."""
        active_config = self.config.load()
        account = active_config.provider.account
        if not account:
            raise CredentialError("No email account is configured. Run `otpilot login <email>`.")
        account_id = AccountId(account)
        if self.credentials.get_app_password(account_id) is None:
            raise CredentialError("No credentials are stored for the configured account.")
        if self.providers.get(ProviderId(active_config.provider.provider_id)) is None:
            raise ProviderError("The configured email provider is unavailable.")

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
                _received_at_sort_key(candidate.source.received_at),
                candidate.source.message_id,
                candidate.value,
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
class HotkeyService:
    """Fetch and copy OTPs in response to global hotkey events."""

    fetch_service: FetchOtpService
    listener: HotkeyListener
    hotkey: str
    status: Callable[[str], None] = field(default=lambda message: None)
    _active: Lock = field(default_factory=Lock, init=False, repr=False)
    _executor: ThreadPoolExecutor = field(
        default_factory=lambda: ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="otpilot-hotkey"
        ),
        init=False,
        repr=False,
    )

    def run(self) -> None:
        registered = False
        try:
            self.fetch_service.validate_ready()
            self.listener.register(self.hotkey, self.trigger)
            registered = True
            self.status(f"Hotkey active: {self._display_hotkey()}")
            self.status("Press Ctrl+C to stop.")
            self.listener.run()
        except KeyboardInterrupt:
            return
        finally:
            if registered:
                self.listener.shutdown()
            self._executor.shutdown(wait=True)

    def trigger(self) -> None:
        """Schedule one fetch so a hook callback returns without waiting for I/O."""
        if not self._active.acquire(blocking=False):
            return
        try:
            self._executor.submit(self._fetch_and_copy)
        except RuntimeError:
            self._active.release()

    def _fetch_and_copy(self) -> None:
        try:
            result = self.fetch_service.fetch()
            self.fetch_service.copy_result(result)
        except OTPilotError as exc:
            self.status(f"OTP fetch failed: {exc}")
        except Exception:
            self.status("OTP fetch failed: An unexpected error occurred.")
        else:
            self.status("OTP copied to clipboard.")
        finally:
            self._active.release()

    def _display_hotkey(self) -> str:
        return "+".join(part.capitalize() for part in self.hotkey.split("+"))


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
