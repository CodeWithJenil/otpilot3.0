# Developer Guide

## Repository Layout

```text
src/otpilot/
  cli/                 CLI entrypoint and command modules
  application/         Use-case services and infrastructure ports
  domain/              Models, errors, extraction, search, provider contracts, state
  providers/
    imap/              Generic IMAP transport and search strategy
    gmail/             Gmail defaults layered on generic IMAP
  infrastructure/      OS and third-party adapters
  config/              Non-secret application configuration models
  preferences/         User preference models
  state/               Future state store implementations
  cache/               OTP cache implementations
tests/                 Tests mirrored around architecture boundaries
docs/                  Supporting references
```

## Development Setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

On Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -e ".[dev]"
```

## Adding a Command

1. Add a command module under `src/otpilot/cli/commands/`.
2. Register it in `src/otpilot/cli/app.py`.
3. Put orchestration in an application service, not the command handler.
4. Update `README.md`, `docs/cli-reference.md`, `docs/troubleshooting.md`, and `CHANGELOG.md`.
5. Add tests with `typer.testing.CliRunner`.

## Adding a Provider

1. Implement or configure an `OtpSourceProvider`.
2. Reuse generic IMAP for IMAP-capable providers.
3. Register the provider in the provider registry composition.
4. Document provider setup, security behavior, and troubleshooting.
5. Add tests proving registration and boundary behavior.

## Adding Configuration

Configuration belongs in `src/otpilot/config/` when it affects correctness or integration. Preferences belong in `src/otpilot/preferences/` when they affect user experience.

Never add secret fields to either model.

Global hotkey implementations belong under `infrastructure/hotkeys/` and implement the
application `HotkeyListener` port. Application services must not import operating-system keyboard
libraries directly.

## Testing Strategy

- Unit tests for domain models, extraction, search, cache, and services.
- OTP extraction tests must cover HTML-only messages, malformed body parts, competing messages,
  sender/subject relevance, recency, and deterministic ties without using a live mailbox.
- CLI tests for command registration and output behavior.
- Security tests for redaction and config secret rejection.
- No network tests in the default suite.
