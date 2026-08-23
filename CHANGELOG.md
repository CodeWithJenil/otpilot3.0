# Changelog

## 0.1.0

- Added architecture scaffold.
- Added CLI command surfaces for `fetch`, `watch`, `login`, `logout`, `config`, `doctor`, and `version`.
- Added generic IMAP provider boundary with Gmail configuration.
- Added extraction, search, cache, state, config, preferences, and application service boundaries.
- Added security, privacy, architecture, developer, installation, roadmap, CLI, configuration, troubleshooting, and dependency documentation.
- Implemented credential-backed Gmail IMAP fetching and candidate-based OTP extraction.
- Implemented optional `fetch --copy` clipboard integration through `pyperclip`.
- Implemented synchronous watch polling with message-ID deduplication and transient provider retry.
