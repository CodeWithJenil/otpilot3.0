# Security

## Authentication

OTPilot does not use OAuth. Email access uses IMAP over SSL with provider app passwords.

For Gmail, users provide:

- Gmail address
- Google App Password

## Credential Storage

Passwords must be stored in the operating system credential vault.

V1 target:

- Windows Credential Manager

Future targets:

- macOS Keychain
- Linux Secret Service

Passwords must never be stored in:

- config files
- preference files
- logs
- exception messages
- test fixtures
- documentation examples

## Logging

Logging must redact credential-like fields. Logs are local only and must not be uploaded or transmitted.

## Network

The only product network access planned for v1 is user-configured IMAP over SSL. OTPilot must not add telemetry, analytics, crash reporting, update checks, or hosted service calls.

## Reporting Vulnerabilities

Until a formal security policy is added, report vulnerabilities through the project issue tracker without including real credentials, OTPs, email content, or private account details.

