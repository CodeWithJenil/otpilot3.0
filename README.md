# OTPilot

OTPilot is a local-first CLI application for fetching one-time passwords from email accounts.

The first supported provider target is Gmail via IMAP over SSL with Google App Passwords. The architecture is intentionally not Gmail-specific: Gmail is a provider configuration layered on a generic IMAP transport so Outlook, Yahoo, Proton Bridge, and custom IMAP servers can be added without changing the CLI or application services.

## Product Principles

- Local only: no server, hosted API, relay, sync service, or cloud dependency.
- No telemetry: OTPilot does not collect usage, diagnostics, crash reports, or analytics.
- No OAuth: email access uses IMAP over SSL and provider-specific app passwords.
- Secure credentials: passwords are stored in the operating system credential vault, never config files.
- Documentation first: public behavior is incomplete unless docs are updated with code.

## Current Status

The first working vertical slices are implemented: credential-backed Gmail IMAP fetching, OTP extraction, optional clipboard copying, synchronous polling watch mode, and a Windows global hotkey. Notifications, auto-paste, and update functionality remain deferred.

## CLI

```bash
otpilot fetch
otpilot fetch --copy
otpilot watch
otpilot hotkey
otpilot login user@gmail.com
otpilot logout user@gmail.com
otpilot config
otpilot doctor
otpilot version
```

See [docs/cli-reference.md](docs/cli-reference.md) for command behavior and documentation requirements.

## Windows Global Hotkey

On Windows, `otpilot hotkey` registers the system-wide `Ctrl+Shift+O` shortcut by default, so it
works while another application has focus. Configure another supported combination in OTPilot's
existing non-secret TOML configuration, for example:

```toml
hotkey = "alt+f9"
```

The Windows-only `pynput` dependency is installed automatically with OTPilot. Press `Ctrl+C` to
unregister the hotkey and exit. Each invocation copies the OTP to the clipboard; OTPilot never
prints it in hotkey mode and does **not** paste it automatically.

## Architecture

OTPilot is layered:

```text
CLI
Application Services
Domain
Providers
Infrastructure
```

The provider architecture is:

```text
OTP Source
  -> IMAP Provider
      -> Gmail
      -> Outlook
      -> Yahoo
      -> Custom IMAP
```

See [architecture.md](architecture.md) for the complete architecture, dependency graph, and design decisions.

## Documentation

- [installation.md](installation.md): local installation and development setup.
- [architecture.md](architecture.md): boundaries, dependency graph, and decisions.
- [developer-guide.md](developer-guide.md): engineering workflow and testing.
- [contributing.md](contributing.md): contribution requirements.
- [security.md](security.md): credential and logging rules.
- [privacy.md](privacy.md): privacy guarantees.
- [roadmap.md](roadmap.md): phased delivery plan.
- [docs/configuration.md](docs/configuration.md): config and preferences reference.
- [docs/troubleshooting.md](docs/troubleshooting.md): support guide.
- [CHANGELOG.md](CHANGELOG.md): release history.

## Development

```bash
python -m pip install -e ".[dev]"
pytest
ruff check .
mypy src/otpilot
```

## License

MIT.
