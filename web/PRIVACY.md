# Privacy Policy

**Project:** otpilot  
**Scope:** Personal use  
**Version:** 3.1.0  
**Last updated:** September 2026

---

## Overview

`otpilot` is a local-first, privacy-focused CLI application. Its primary operation—fetching OTP codes from email via IMAP—is completely local and does not involve any external servers operated by the OTPilot project.

**Optional telemetry** is available as an **opt-in** feature to help the project understand real-world usage. Telemetry is **disabled by default** and must be explicitly enabled by the user.

---

## Data Processed Locally (Core Functionality)

| Data | Purpose | Stored? | Sent Externally? |
|---|---|---|---|
| Gmail emails | Search for OTP codes via IMAP/SSL | No | No |
| App Password | Authenticate IMAP connection | Yes (OS credential vault only) | No |
| OTP code | Copy to local clipboard | No | No |

---

## Optional Telemetry (Opt-In Only)

If you explicitly enable telemetry (`otpilot telemetry enable`), OTPilot sends **anonymous operational metadata** to the OTPilot project endpoint (`https://jenil-otpilot.vercel.app/api/telemetry`).

### What IS Collected (Telemetry)

| Field | Description | Example |
|---|---|---|
| `installation_id` | Random UUID generated locally on first enable | `a1b2c3d4-e5f6-7890-abcd-ef1234567890` |
| `event` | Event name from allowlist | `app_started`, `command_executed` |
| `version` | OTPilot version | `3.0.1` |
| `python_version` | Python major.minor | `3.12` |
| `os` | Operating system | `macos`, `linux`, `windows` |
| `architecture` | CPU architecture | `x86_64`, `arm64` |
| `timestamp` | UTC timestamp | `2026-09-27T10:15:00Z` |
| `command` (optional) | Command name from allowlist | `fetch`, `watch`, `hotkey` |

### What is NOT Collected (Telemetry)

- Email addresses or email contents
- OTP codes
- IMAP credentials, passwords, or access tokens
- Clipboard contents
- File paths
- Usernames
- IP addresses (beyond what the HTTP request inherently reveals to the server)
- Exact geographic location
- Hostnames
- Arbitrary environment variables
- Command arguments (which may contain secrets)
- Personally identifiable information
- Raw exception messages (which could contain sensitive data)

### Telemetry Guarantees

- **Opt-in only**: Telemetry is **disabled by default**. You must run `otpilot telemetry enable` to activate it.
- **Easy to disable**: Run `otpilot telemetry disable` at any time to stop transmission. The installation ID is preserved locally.
- **Asynchronous & non-blocking**: Telemetry is sent in a background thread. It **never blocks** or slows down your OTPilot commands.
- **Failure-tolerant**: Network failures, timeouts, or server errors are silently ignored. A telemetry failure **never causes an OTPilot command to fail**.
- **Minimal payload**: Maximum 1 KB per event. Short timeouts (2s connect, 5s total). No infinite retries.
- **HTTPS only**: All telemetry is sent over TLS.
- **No sensitive data in logs**: Telemetry payloads and installation IDs are not logged by default.

### Installation ID Lifecycle

- Generated **only when you enable telemetry** using a cryptographically random UUID (RFC 4122).
- Stored in your local preferences file (not in config, not in keyring).
- **Persists across OTPilot runs**.
- **Preserved** when you disable telemetry. If you re-enable later, the same ID is reused.
- **Not derived from** MAC address, hostname, username, email, machine serial number, or hardware identifiers.

### How to Enable Telemetry

```bash
otpilot telemetry enable
```

This command will:
1. Generate a random installation ID (if not already present)
2. Enable telemetry in your preferences
3. Show you exactly what data will be collected
4. Confirm that telemetry is now active

### How to Disable Telemetry

```bash
otpilot telemetry disable
```

This command will:
1. Disable telemetry transmission immediately
2. Preserve your installation ID locally (so re-enabling doesn't create a new identity)
3. Not delete any other configuration

### How to Check Status

```bash
otpilot telemetry status
```

Shows whether telemetry is enabled and displays your installation ID (if enabled).

---

## Credential Storage

`otpilot` stores your email account credentials only in your operating system's native credential vault using `keyring`:

| OS | Credential Vault |
|---|---|
| macOS | Keychain |
| Windows | Windows Credential Manager |
| Linux | Secret Service / D-Bus (libsecret) |

You can remove stored credentials at any time by running `otpilot logout <email>`.

---

## Network Communication

**Core functionality**: The only network communication is direct IMAP over SSL (`imap.gmail.com:993`) between your machine and your email provider. This communication is protected by standard TLS encryption.

**Telemetry (opt-in only)**: If enabled, anonymous operational metadata is sent via HTTPS POST to `https://jenil-otpilot.vercel.app/api/telemetry`.

No other network requests or external connections are made.

---

## Data Retention

Telemetry events are retained for a limited period for aggregate analysis. Individual installation IDs are not linked to personal identities.

---

## Contact

For privacy questions, see the project repository: https://github.com/CodeWithJenil/otpilot3.0