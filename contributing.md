# Contributing

OTPilot is privacy-first infrastructure. Contributions must preserve local-only operation, no telemetry, no OAuth, and secure credential storage.

## Pull Request Requirements

A pull request is incomplete if any public API, CLI command, configuration option, architecture decision, or user-facing behavior changes without updating the corresponding documentation.

Required documentation updates may include:

- `README.md`
- `architecture.md`
- `docs/cli-reference.md`
- `docs/configuration.md`
- `developer-guide.md`
- `security.md`
- `privacy.md`
- `docs/troubleshooting.md`
- `CHANGELOG.md`

## Engineering Rules

- Keep CLI handlers thin.
- Put orchestration in application services.
- Put provider-independent behavior in domain modules.
- Put OS and third-party integration in infrastructure modules.
- Never store secrets outside the OS credential vault.
- Never log credentials or raw app passwords.
- Add tests for public behavior and security-sensitive rules.

## Local Checks

```bash
python -m pip install -e ".[dev]"
pytest
ruff check .
mypy src/otpilot
```

## Provider Contributions

New providers must register through the provider registry. IMAP-capable providers should reuse `providers/imap/` unless they require a genuinely different protocol.

