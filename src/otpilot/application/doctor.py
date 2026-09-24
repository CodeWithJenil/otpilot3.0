"""Local diagnostics for installation, configuration, and runtime prerequisites."""

from __future__ import annotations

from dataclasses import dataclass, field

from otpilot.application.ports import (
    CredentialStore,
    MutableConfigurationRepository,
    MutablePreferencesRepository,
    PlatformDiagnostics,
)
from otpilot.config.models import AppConfig
from otpilot.domain.diagnostics import CheckStatus, DiagnosticCheck, DiagnosticReport
from otpilot.domain.errors import (
    ConfigurationError,
    CredentialError,
    ImapTransportError,
    PreferenceError,
)
from otpilot.domain.models import AccountId, ProviderId
from otpilot.domain.providers import ProviderRegistry
from otpilot.domain.state import RuntimeState

_CONNECTIVITY_TIMEOUT_NOTE = "IMAP checks use the provider timeout and do not download messages."


@dataclass(slots=True)
class DoctorService:
    config: MutableConfigurationRepository
    credentials: CredentialStore
    providers: ProviderRegistry
    platform: PlatformDiagnostics
    preferences: MutablePreferencesRepository | None = None
    test_connectivity: bool = True
    _checks: list[DiagnosticCheck] = field(default_factory=list, init=False, repr=False)

    def inspect(self) -> DiagnosticReport:
        self._checks = []
        self._extend_probe("Environment", self.platform.environment_checks)
        self._extend_probe(
            "Configuration",
            lambda: self.platform.configuration_support_checks(self.config.path),
        )
        config, config_ok = self._configuration_validity()
        self._preferences_validity()
        self._append_probe("Credentials", self.platform.keyring_check)
        stored: tuple[str, str] | None = None
        if config_ok and config is not None:
            stored = self._credential_presence(config.provider.account)
            self._provider_availability(config.provider.provider_id)
            self._connectivity(config.provider.provider_id, config.provider.account, stored)
        else:
            self._checks.append(
                DiagnosticCheck(
                    "Connectivity",
                    "Gmail IMAP",
                    CheckStatus.SKIP,
                    "Gmail connection not tested because configuration is invalid.",
                )
            )
        self._append_probe("Clipboard", self.platform.clipboard_check)
        self._append_probe("Hotkeys", self.platform.hotkey_check)
        self._extend_probe("Dependencies", self.platform.dependency_checks)
        runtime = RuntimeState(
            authenticated=stored is not None,
            connected=any(
                check.category == "Connectivity" and check.status is CheckStatus.PASS
                for check in self._checks
            ),
            background_running=False,
            provider_available=any(
                check.name == "Provider" and check.status is CheckStatus.PASS
                for check in self._checks
            ),
            active_provider=(
                ProviderId(config.provider.provider_id)
                if config_ok and config is not None
                else None
            ),
        )
        return DiagnosticReport(checks=tuple(self._checks), runtime=runtime)

    def _configuration_validity(self) -> tuple[AppConfig | None, bool]:
        try:
            loaded = self.config.load()
        except ConfigurationError:
            self._checks.append(
                DiagnosticCheck(
                    "Configuration",
                    "File",
                    CheckStatus.FAIL,
                    "Configuration file is invalid or malformed.",
                    "Fix or remove the configuration file, then run `otpilot config` again.",
                )
            )
            return None, False
        if not self.config.path.exists():
            self._checks.append(
                DiagnosticCheck(
                    "Configuration",
                    "File",
                    CheckStatus.PASS,
                    "No configuration file yet; built-in defaults will be used.",
                    "Run `otpilot login <email>` and `otpilot config set` to persist settings.",
                )
            )
        else:
            self._checks.append(
                DiagnosticCheck(
                    "Configuration",
                    "File",
                    CheckStatus.PASS,
                    f"Configuration file is valid: {self.config.path}",
                )
            )
        if loaded.provider.account is None:
            self._checks.append(
                DiagnosticCheck(
                    "Configuration",
                    "Account",
                    CheckStatus.WARN,
                    "No email account is configured.",
                    "Run `otpilot login <email>` to store credentials and select an account.",
                )
            )
        else:
            self._checks.append(
                DiagnosticCheck(
                    "Configuration",
                    "Account",
                    CheckStatus.PASS,
                    f"Active account: {loaded.provider.account}",
                )
            )
        return loaded, True

    def _preferences_validity(self) -> None:
        if self.preferences is None:
            return
        try:
            self.preferences.load()
        except PreferenceError:
            self._checks.append(
                DiagnosticCheck(
                    "Configuration",
                    "Preferences",
                    CheckStatus.FAIL,
                    "Preferences file is invalid or malformed.",
                    "Fix or remove preferences.toml, then retry.",
                )
            )
            return
        if not self.preferences.path.exists():
            self._checks.append(
                DiagnosticCheck(
                    "Configuration",
                    "Preferences",
                    CheckStatus.PASS,
                    "No preferences file yet; built-in defaults will be used.",
                )
            )
            return
        self._checks.append(
            DiagnosticCheck(
                "Configuration",
                "Preferences",
                CheckStatus.PASS,
                f"Preferences file is valid: {self.preferences.path}",
            )
        )

    def _extend_probe(self, category: str, producer: object) -> None:
        try:
            checks = producer()  # type: ignore[operator]
        except Exception:
            self._checks.append(
                DiagnosticCheck(
                    category,
                    "Probe",
                    CheckStatus.FAIL,
                    f"{category} diagnostics failed unexpectedly.",
                )
            )
            return
        self._checks.extend(list(checks))

    def _append_probe(self, category: str, producer: object) -> None:
        try:
            check = producer()  # type: ignore[operator]
        except Exception:
            self._checks.append(
                DiagnosticCheck(
                    category,
                    "Probe",
                    CheckStatus.FAIL,
                    f"{category} diagnostics failed unexpectedly.",
                )
            )
            return
        self._checks.append(check)

    def _credential_presence(self, account: str | None) -> tuple[str, str] | None:
        if not account:
            self._checks.append(
                DiagnosticCheck(
                    "Credentials",
                    "Gmail",
                    CheckStatus.WARN,
                    "Gmail credentials are not configured.",
                    "Run `otpilot login <email>` with a Gmail app password.",
                )
            )
            return None
        try:
            stored = self.credentials.get_app_password(AccountId(account))
        except CredentialError:
            self._checks.append(
                DiagnosticCheck(
                    "Credentials",
                    "Gmail",
                    CheckStatus.FAIL,
                    "Credential storage could not be read for the configured account.",
                    "Verify the OS keyring is available, then run `otpilot login <email>` again.",
                )
            )
            return None
        if stored is None:
            self._checks.append(
                DiagnosticCheck(
                    "Credentials",
                    "Gmail",
                    CheckStatus.WARN,
                    "No credentials are stored for the configured account.",
                    "Run `otpilot login <email>` to store a Gmail app password in the OS vault.",
                )
            )
            return None
        self._checks.append(
            DiagnosticCheck(
                "Credentials",
                "Gmail",
                CheckStatus.PASS,
                "Credentials are stored for the configured account.",
            )
        )
        return stored

    def _provider_availability(self, provider_id: str) -> None:
        provider = self.providers.get(ProviderId(provider_id))
        if provider is None:
            self._checks.append(
                DiagnosticCheck(
                    "Configuration",
                    "Provider",
                    CheckStatus.FAIL,
                    f"Configured provider '{provider_id}' is not registered.",
                    "Set provider.provider_id to 'gmail' with `otpilot config set`.",
                )
            )
            return
        self._checks.append(
            DiagnosticCheck(
                "Configuration",
                "Provider",
                CheckStatus.PASS,
                f"Provider '{provider_id}' is available.",
            )
        )

    def _connectivity(
        self,
        provider_id: str,
        account: str | None,
        stored: tuple[str, str] | None,
    ) -> None:
        if not self.test_connectivity:
            self._checks.append(
                DiagnosticCheck(
                    "Connectivity",
                    "Gmail IMAP",
                    CheckStatus.SKIP,
                    "Gmail connection not tested (--offline).",
                )
            )
            return
        if stored is None or account is None:
            self._checks.append(
                DiagnosticCheck(
                    "Connectivity",
                    "Gmail IMAP",
                    CheckStatus.SKIP,
                    "Gmail connection not tested because credentials are unavailable.",
                    "Store credentials with `otpilot login` before testing IMAP connectivity.",
                )
            )
            return
        provider = self.providers.get(ProviderId(provider_id))
        if provider is None:
            self._checks.append(
                DiagnosticCheck(
                    "Connectivity",
                    "Gmail IMAP",
                    CheckStatus.SKIP,
                    "Gmail connection not tested because the provider is unavailable.",
                )
            )
            return
        username, app_password = stored
        try:
            provider.authenticate(AccountId(account), username, app_password)
        except ImapTransportError as exc:
            self._checks.append(
                DiagnosticCheck(
                    "Connectivity",
                    "Gmail IMAP",
                    CheckStatus.FAIL,
                    f"Gmail IMAP connection failed: {exc}",
                    "Confirm IMAP is enabled, the app password is valid, "
                    "and the network allows imap.gmail.com:993.",
                )
            )
            return
        except Exception:
            self._checks.append(
                DiagnosticCheck(
                    "Connectivity",
                    "Gmail IMAP",
                    CheckStatus.FAIL,
                    "Gmail IMAP connection failed.",
                    "Confirm IMAP is enabled and retry. " + _CONNECTIVITY_TIMEOUT_NOTE,
                )
            )
            return
        self._checks.append(
            DiagnosticCheck(
                "Connectivity",
                "Gmail IMAP",
                CheckStatus.PASS,
                "Gmail IMAP login succeeded. No messages were retrieved.",
            )
        )
