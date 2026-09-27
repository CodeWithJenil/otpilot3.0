# Privacy

OTPilot is designed to run locally.

## Guarantees

- No servers required for core functionality.
- **Telemetry is optional and opt-in** (disabled by default).
- No analytics or crash reporting without explicit consent.
- No cloud sync.
- No remote logging.
- No OAuth grants.
- No credential storage in config files.

## Data Processed Locally

OTPilot may process:

- email account address
- provider configuration
- IMAP search results
- email snippets or bodies needed for OTP extraction
- extracted OTP candidates
- short-lived cached OTP results

## Data Storage

Non-secret configuration and preferences are stored locally. Credentials are stored only in the operating system credential vault (macOS Keychain, Windows Credential Manager, Linux Secret Service via `keyring`).

## Optional Telemetry

OTPilot includes an **optional, opt-in telemetry** system to help measure actual usage (separate from PyPI download statistics).

### Telemetry Principles

- **Disabled by default** — must be explicitly enabled with `otpilot telemetry enable`
- **Anonymous** — uses a randomly generated UUID (not derived from hardware, hostname, or identity)
- **Minimal** — collects only: installation ID, event name, version, Python version, OS, architecture, timestamp, and optionally the command name (from a strict allowlist)
- **No sensitive data** — never collects emails, OTPs, credentials, clipboard contents, file paths, usernames, IP addresses, or command arguments
- **Asynchronous** — sent in a background thread, never blocks commands
- **Failure-tolerant** — network errors never cause OTPilot commands to fail
- **Easy to disable** — `otpilot telemetry disable` stops transmission immediately

### What IS Collected (if enabled)

| Field | Example |
|-------|---------|
| `installation_id` | `a1b2c3d4-e5f6-7890-abcd-ef1234567890` |
| `event` | `app_started`, `command_executed` |
| `version` | `3.0.1` |
| `python_version` | `3.12` |
| `os` | `macos`, `linux`, `windows` |
| `architecture` | `x86_64`, `arm64` |
| `timestamp` | `2026-09-27T10:15:00Z` |
| `command` (optional) | `fetch`, `watch`, `hotkey` |

### What is NOT Collected

- Email addresses, email contents, OTP codes
- Credentials, passwords, access tokens
- Clipboard contents, file paths, usernames
- IP addresses (beyond inherent HTTP metadata), exact location, hostnames
- Command arguments or any sensitive data

### Managing Telemetry

```bash
# Check status
otpilot telemetry status

# Enable (shows exactly what will be collected)
otpilot telemetry enable

# Disable (preserves installation ID locally)
otpilot telemetry disable
```

## Future Changes

Any change that sends data outside the local machine requires updates to `README.md`, `architecture.md`, `security.md`, `privacy.md`, and `CHANGELOG.md`.