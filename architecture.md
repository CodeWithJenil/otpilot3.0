# OTPilot Architecture

## Summary

OTPilot fetches OTPs from email accounts. Gmail is the first supported provider target, but the architecture treats Gmail as configuration on top of a generic IMAP transport.

The system is Windows-first and local-only. macOS and Linux support are future targets through platform-specific infrastructure adapters.

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
  Windows Credential Manager, config storage, preferences storage,
  clipboard, hotkeys, notifications, logging, platform detection
```

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

## Extraction Model

OTPilot uses `OtpExtractor`, not an `OtpParser`.

The problem is not syntactic parsing. Emails contain unrelated text, order numbers, dates, shipment IDs, and support references. OTPilot must extract the most probable OTP:

```text
Email
  -> Candidate generation
  -> Candidate scoring
  -> Best OTP
```

The scaffold defines `CandidateGenerator`, `CandidateScorer`, `ExtractableEmail`, and `OtpExtractor`. The concrete extraction algorithm is deferred to a later phase.

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

- hotkey
- theme
- notifications
- auto paste

Secrets are not allowed in either model.

## Background Service

`otpilot watch` is a thin CLI entrypoint over `WatchService`.

Watch-mode internals are expected to compose:

```text
Background Service
  -> Hotkey Listener
  -> Command Dispatcher
  -> FetchOtpService
  -> ClipboardService
  -> NotificationService
```

This prevents watch mode from becoming a large command handler.

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

V1 credential storage target:

- Windows Credential Manager

Future credential storage targets:

- macOS Keychain
- Linux Secret Service

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
- Documentation gates changes: public behavior and docs must remain synchronized.

