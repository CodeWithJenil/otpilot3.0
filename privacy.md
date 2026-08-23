# Privacy

OTPilot is designed to run locally.

## Guarantees

- No servers.
- No telemetry.
- No analytics.
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

Non-secret configuration and preferences are stored locally. Credentials are stored only in the operating system credential vault.

## Future Changes

Any change that sends data outside the local machine requires updates to `README.md`, `architecture.md`, `security.md`, `privacy.md`, and `CHANGELOG.md`.

