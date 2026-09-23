# OTPilot Architecture

## Summary

OTPilot fetches OTPs from email accounts. Gmail is the first supported provider target, but the architecture treats Gmail as configuration on top of a generic IMAP transport.

The system is cross-platform (supporting Windows, macOS, and Linux X11) and local-only.

## Layered Design

```text
CLI
  commands, output formatting, argument parsing

Application
  FetchOtpService, WatchService, LoginService, LogoutService,
  SettingsService, DoctorService, ClipboardService, NotificationService

Domain
  OTP models, extraction pipeline, search criteria, provider contracts,
  state model, error hierarchy

Providers
  provider registry, generic IMAP provider, Gmail IMAP configuration

Infrastructure
  KeyringCredentialStore, config storage, preferences storage,
  clipboard, hotkeys, notifications, logging, platform detection
```

Note that `otpilot config` and `otpilot doctor` are scaffolded commands in current versions.

## Dependency Rule

Dependencies point inward:

```text
CLI -> Application -> Domain
Application -> Ports -> Infrastructure implementations
Providers -> Domain
Infrastructure -> Application ports and Domain models
```

The CLI must not connect directly to IMAP, credential stores, cache backends, or platform APIs. Providers must not import CLI modules.

## Provider Model

OTPilot uses a provider registry:

```text
Provider Registry
  -> Gmail provider config
      -> Generic IMAP provider
  -> Future Outlook provider config
      -> Generic IMAP provider
  -> Future Yahoo provider config
      -> Generic IMAP provider
  -> Future custom IMAP provider config
      -> Generic IMAP provider
```

Gmail lives in `src/otpilot/providers/gmail/` because Gmail owns defaults such as `imap.gmail.com`, SSL port `993`, and app-password documentation. IMAP transport lives in `src/otpilot/providers/imap/` because IMAP is reusable infrastructure for many email sources.

Each IMAP authentication or retrieval operation opens a short-lived connection, authenticates,
selects the configured mailbox read-only, and attempts logout in a `finally` block. Connections
use a 30-second timeout by default; cleanup errors never replace the preceding transport error.

## Extraction Model

OTPilot uses `OtpExtractor`, not an `OtpParser`.

The problem is not syntactic parsing. Emails contain unrelated text, order numbers, dates, shipment IDs, and support references. OTPilot must extract the most probable OTP:

```text
Email
  -> Candidate generation from plain text and HTML
  -> Context, sender, and subject scoring
  -> Deterministic best OTP selection
```

The extraction pipeline accepts common four-to-eight digit code formats only when they have
nearby OTP context. It avoids bare order, invoice, date, and amount values, and uses sender,
subject, score, message receipt time, and stable identifiers to select among candidates.

## Search Engine

Search is a first-class domain concept so OTPilot does not download every email.

Search flow:

```text
SearchCriteria
  -> SearchStrategy
  -> Provider query
  -> Limited message download
  -> Extraction
```

The generic IMAP search strategy supports `SINCE`, `UNSEEN`, `FROM`, `SUBJECT`, `TO`, and `BODY` terms. Providers may choose different strategy implementations while preserving the same application service contract.

## Cache Layer

OTPilot includes an `OtpCache` port and short-lived in-memory cache implementation.

Repeated requests, hotkeys, and watch-mode actions should first check cache freshness. A small TTL, typically 5-10 seconds, prevents repeated connect-authenticate-search-download-disconnect cycles while preserving freshness for OTP workflows.

## Configuration vs Preferences

Configuration and preferences are separate.

Configuration affects correctness and platform integration:

- provider
- account
- credential backend
- config directory

Preferences affect user experience:

- theme
- notifications
- auto paste

Secrets are not allowed in either model. Note that `otpilot config` and `otpilot doctor` remain scaffolded commands.

## Background Service & Hotkeys

`otpilot watch` is a thin CLI entrypoint over `WatchService`.

Watch-mode and hotkey internals compose:

```text
HotkeyService
  -> HotkeyListener port
  -> FetchOtpService
  -> ClipboardService
```

Global hotkey listening is implemented using a cross-platform `pynput` adapter in infrastructure (`KeyringCredentialStore` and `pynput` listener implementations stay in infrastructure, so the application layer has no direct dependency on OS-specific hooks).

- **macOS**: Requires Accessibility permissions for hotkey capturing.
- **Linux**: Supported on X11 display servers (Wayland is unsupported).

This keeps command handlers testable and keeps the listener replaceable in tests.

## State Management

Runtime state is represented by `RuntimeState`:

- authenticated
- connected
- background running
- provider available
- active provider

Commands and services should use this model instead of scattering status checks.

## Credential Design

Authentication uses IMAP over SSL with provider app passwords. OAuth is out of scope.

Credential storage target:

- `KeyringCredentialStore` backed by the system `keyring` (macOS Keychain, Windows Credential Manager, Linux Secret Service).

Credential values must never be stored in config files, preferences, logs, errors, tests, or documentation examples.

## Logging Design

Logging is local console logging only. The logging layer redacts secret-like fields before output.

No telemetry, analytics, remote logging, crash upload, or network diagnostics may be added without a public architecture decision and privacy documentation update.

## Error Hierarchy

All expected failures derive from `OTPilotError`.

Current hierarchy:

- `ConfigurationError`
- `PreferenceError`
- `CredentialError`
- `ProviderError`
- `ImapTransportError`
- `ExtractionError`
- `CacheError`
- `BackgroundServiceError`
- `FeatureNotImplementedError`

Errors may include structured `ErrorContext`, but context must be non-secret.

## Architectural Decisions

- Generic IMAP first: IMAP is a reusable transport, while Gmail is one provider configuration.
- Application layer required: CLI commands stay thin and testable.
- Extraction over parsing: OTP selection requires ranking candidates, not parsing one fixed format.
- Search before download: performance depends on provider-side filtering.
- Cache before refresh: hotkeys and repeated fetches need low latency.
- Config separate from preferences: operational correctness and UX settings evolve independently.
- Registry over hardcoded providers: future providers register without modifying CLI or core services.
- System keyring backend: standard `keyring` library provides cross-platform secure credential storage.
- Documentation gates changes: public behavior and docs must remain synchronized.
