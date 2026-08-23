# Roadmap

## Phase 1: Architecture Scaffold

- Package layout.
- CLI command surfaces.
- Application services.
- Domain contracts.
- Generic IMAP provider boundary.
- Gmail provider configuration.
- Search strategy boundary.
- Extraction pipeline boundary.
- Short-lived cache boundary.
- Config and preference separation.
- Documentation system.

## Phase 2: Local Configuration and Credentials

- Config file loading and saving.
- Preference file loading and saving.
- Windows Credential Manager integration.
- `otpilot login`.
- `otpilot logout`.
- credential redaction tests.

## Phase 3: Gmail via IMAP

- IMAP SSL connection.
- app-password authentication.
- IMAP search query execution.
- limited email download.
- resilient provider errors.
- `otpilot doctor` provider diagnostics.

## Phase 4: OTP Extraction

- candidate generation.
- candidate scoring.
- best OTP selection.
- expiry handling.
- false-positive tests.

## Phase 5: Watch Mode

- background service.
- hotkey listener.
- command dispatcher.
- short TTL cache.
- clipboard integration.
- local notifications.

## Phase 6: Additional Providers and Platforms

- custom IMAP provider.
- Outlook IMAP configuration.
- Yahoo IMAP configuration.
- Proton Bridge configuration.
- macOS Keychain.
- Linux Secret Service.

