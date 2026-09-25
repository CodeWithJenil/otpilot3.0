# Privacy Policy

**Project:** otpilot  
**Scope:** Personal use  
**Version:** 3.0.0  
**Last updated:** September 2026

---

## Overview

`otpilot` is a local-first, privacy-focused CLI application. It does not collect, transmit, or store any data on external servers. All data processed by `otpilot` stays exclusively on your local machine.

---

## Data Processed

| Data | Purpose | Stored? | Sent Externally? |
|---|---|---|---|
| Gmail emails | Search for OTP codes via IMAP/SSL | No | No |
| App Password | Authenticate IMAP connection | Yes (OS credential vault only) | No |
| OTP code | Copy to local clipboard | No | No |

---

## What Is NOT Collected

- Email content is processed in-memory and never written to disk.
- No telemetry, usage tracking, crash reporting, or diagnostics.
- No credentials or passwords are saved in configuration files or plain text.
- No data is sent to any third-party service other than your configured IMAP server (e.g. Gmail over TLS/SSL).

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

The only network communication performed by `otpilot` is direct IMAP over SSL (`imap.gmail.com:993`) between your machine and your email provider. This communication is protected by standard TLS encryption.

No other network requests or external connections are made.