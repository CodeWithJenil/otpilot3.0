# Changelog

## 3.1.0 - 2026-09-27

### Added
- **Optional opt-in telemetry system** with privacy-first design:
  - New CLI commands: `otpilot telemetry enable`, `otpilot telemetry disable`, `otpilot telemetry status`
  - Anonymous installation ID (UUID v4) generated locally on first enable, persisted in preferences
  - Asynchronous, non-blocking HTTP transmission via background thread (2s connect / 5s total timeout)
  - Failure-tolerant: network errors never cause OTPilot commands to fail
  - Strict allowlist for events (`app_started`, `command_executed`, `telemetry_enabled`, `telemetry_disabled`) and commands (`fetch`, `watch`, `hotkey`, `login`, `logout`, `config`, `doctor`, `version`, `telemetry`)
  - Payload includes only: OTPilot version, Python version, OS, CPU architecture, installation ID, event type, timestamp, optional command name
  - Explicitly excludes: emails, OTPs, credentials, clipboard contents, file paths, usernames, hostnames, exact location, command arguments
  - End-of-command suggestion when telemetry is disabled (TTY only, not for telemetry commands)
- **Telemetry backend** on Vercel with Neon PostgreSQL storage:
  - POST `/api/telemetry` endpoint with strict schema validation
  - GET `/api/telemetry-query` endpoint for querying stored events
  - Single `telemetry_events` table with indexes on installation_id, event, received_at, command
- **Website Telemetry & Privacy section** integrated into home page:
  - Terminal-style panel matching OTPilot visual identity
  - Status display, collected/never-collected breakdown, CLI commands, expandable payload example
  - Responsive design with scroll animations and reduced-motion support

### Changed
- Updated `UserPreferences` model with `telemetry_enabled` (default: false) and `telemetry_installation_id` fields
- Extended `SettingsService` with telemetry preference keys and parsing logic
- Enhanced CLI entrypoint (`TelemetryTyper`) with async telemetry dispatch and end-of-command suggestion
- Updated website to v3.1 with Telemetry & Privacy section
- Updated privacy documentation across README, privacy.md, docs/cli-reference.md, docs/configuration.md, and website

### Privacy
- Telemetry is opt-in only (disabled by default)
- No sensitive data collected (emails, OTPs, credentials, clipboard, paths, hostnames, IPs, command arguments)
- Installation ID randomly generated (UUID v4), not derived from hardware/identity
- Easy to disable: `otpilot telemetry disable` preserves installation ID locally
- Transparent: `otpilot telemetry enable` shows exactly what data is collected

## 3.0.0 - 2026-09-25

### Added
- Redesigned interactive `otpilot config` editor with explicit state machine (`ConfigController`): MENU, EDIT_TEXT, EDIT_NUMBER, SELECT_OPTION, CAPTURE_HOTKEY, CONFIRM_RESET, EXIT states.
- Reliable Return and Escape handling on macOS: bare Escape distinguished from escape sequences; both `\r` and `\n` normalized to confirm action.
- Synchronous keyboard input with no background threads; Windows support via `msvcrt`.
- Hotkey capture: Esc cancels, 30-second timeout, captured combinations validated before saving, macOS input-monitoring blocks reported with actionable accessibility message.
- Automatic fallback to non-interactive mode when stdin is not a TTY; clean error messages (exit code 1) for repository failures.
- First PyPI public release (`pip install otpilot`).
- Cross-platform support for Windows, macOS, and Linux X11.
- Standardized credential backend using system `keyring` (macOS Keychain, Linux Secret Service, Windows Credential Manager).
- Security hardening: `otpilot fetch --copy` copies OTP to clipboard without printing the value to terminal output.
- Packaging improvements: PEP 517/518 build setup, PyPI metadata and classifiers.
- Implemented `otpilot config` with interactive and `--non-interactive` modes for non-secret configuration and preference management.
- Implemented `otpilot doctor` with comprehensive diagnostics across Environment, Configuration, Credentials, Connectivity, Clipboard, Hotkeys, and Dependencies.
- Comprehensive test coverage for `config` and `doctor` CLI commands.
- Updated documentation: CLI reference, configuration guide, and troubleshooting guide.

### Changed
- Replaced previous `InteractiveConfigEditor` monolithic implementation with clean `ConfigController` state machine architecture.
- Removed obsolete background keyboard threads and callback-based event dispatch.

### Fixed
- macOS Return key (`\r`) now correctly confirms input in interactive config.
- macOS hotkey capture Ctrl-combinations and virtual key codes now work correctly.
- Configuration validation errors shown inline without clearing user input buffer.

## 0.1.0

- Added architecture scaffold.
- Added CLI command surfaces for `fetch`, `watch`, `login`, `logout`, `config`, `doctor`, and `version`.
- Added generic IMAP provider boundary with Gmail configuration.
- Added extraction, search, cache, state, config, preferences, and application service boundaries.
- Added security, privacy, architecture, developer, installation, roadmap, CLI, configuration, troubleshooting, and dependency documentation.
- Implemented credential-backed Gmail IMAP fetching and candidate-based OTP extraction.
- Implemented optional `fetch --copy` clipboard integration through `pyperclip`.
- Implemented synchronous watch polling with message-ID deduplication and transient provider retry.
- Implemented a configurable Windows global hotkey (`ctrl+shift+o` by default) that fetches and copies OTPs without displaying their values.

## 0.1.0

- Added architecture scaffold.
- Added CLI command surfaces for `fetch`, `watch`, `login`, `logout`, `config`, `doctor`, and `version`.
- Added generic IMAP provider boundary with Gmail configuration.
- Added extraction, search, cache, state, config, preferences, and application service boundaries.
- Added security, privacy, architecture, developer, installation, roadmap, CLI, configuration, troubleshooting, and dependency documentation.
- Implemented credential-backed Gmail IMAP fetching and candidate-based OTP extraction.
- Implemented optional `fetch --copy` clipboard integration through `pyperclip`.
- Implemented synchronous watch polling with message-ID deduplication and transient provider retry.
- Implemented a configurable Windows global hotkey (`ctrl+shift+o` by default) that fetches and copies OTPs without displaying their values.
