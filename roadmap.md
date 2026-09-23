# Roadmap

## Phase 1: Architecture Scaffold (Completed in v3.0.0)

- [x] Package layout.
- [x] CLI command surfaces.
- [x] Application services.
- [x] Domain contracts.
- [x] Generic IMAP provider boundary.
- [x] Gmail provider configuration.
- [x] Search strategy boundary.
- [x] Extraction pipeline boundary.
- [x] Short-lived cache boundary.
- [x] Config and preference separation.
- [x] Documentation system.

## Phase 2: Local Configuration and Credentials (Completed in v3.0.0)

- [x] Config file loading and saving.
- [x] Preference file loading and saving.
- [x] System credential vault integration via `keyring` (macOS Keychain, Windows Credential Manager, Linux Secret Service).
- [x] `otpilot login`.
- [x] `otpilot logout`.
- [x] credential redaction tests.

## Phase 3: Gmail via IMAP (Completed in v3.0.0)

- [x] IMAP SSL connection.
- [x] app-password authentication.
- [x] IMAP search query execution.
- [x] limited email download.
- [x] resilient provider errors.
- [x] provider diagnostics boundary (`otpilot doctor` scaffold).

## Phase 4: OTP Extraction (Completed in v3.0.0)

- [x] candidate generation.
- [x] candidate scoring.
- [x] best OTP selection.
- [x] expiry handling.
- [x] false-positive tests.

## Phase 5: Watch Mode and Global Hotkey (Completed in v3.0.0)

- [x] background service.
- [x] cross-platform hotkey listener via `pynput`.
- [x] command dispatcher.
- [x] short TTL cache.
- [x] clipboard integration (`otpilot fetch --copy`).
- [x] local notifications boundary.

## Phase 6: Additional Providers and Platforms (Future / Planned)

- [ ] custom IMAP provider.
- [ ] Outlook IMAP configuration.
- [ ] Yahoo IMAP configuration.
- [ ] Proton Bridge configuration.
- [ ] Wayland support for Linux.
