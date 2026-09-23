# OTPilot

OTPilot is a local-first CLI application for fetching one-time passwords from email accounts.

The first supported provider target is Gmail via IMAP over SSL with Google App Passwords. The architecture is intentionally not Gmail-specific: Gmail is a provider configuration layered on a generic IMAP transport so Outlook, Yahoo, Proton Bridge, and custom IMAP servers can be added without changing the CLI or application services.

OTPilot is available on PyPI:
```bash
pip install otpilot
```

## Platform Support

OTPilot supports cross-platform execution on:
- **Windows**
- **macOS**
- **Linux X11** (*Wayland is unsupported*)

## Product Principles

- Local only: no server, hosted API, relay, sync service, or cloud dependency.
- No telemetry: OTPilot does not collect usage, diagnostics, crash reports, or analytics.
- No OAuth: email access uses IMAP over SSL and provider-specific app passwords.
- Secure credentials: passwords are stored in the operating system credential vault via `keyring` (macOS Keychain, Windows Credential Manager, Linux Secret Service), never in config files.
- Documentation first: public behavior is incomplete unless docs are updated with code.

## Current Status

Version 3.0.0 is released on PyPI. It features credential-backed Gmail IMAP fetching, candidate-based OTP extraction, optional clipboard copying via `otpilot fetch --copy` (which copies the OTP to the clipboard without printing it to terminal output), synchronous polling watch mode, and cross-platform global hotkey support.

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

See [docs/cli-reference.md](docs/cli-reference.md) for command behavior and documentation details. Note that `otpilot config` and `otpilot doctor` are scaffolded commands.

## Global Hotkey

`otpilot hotkey` registers a system-wide hotkey using a cross-platform `pynput` adapter so it works while another application has focus:
- **Windows & Linux (X11)**: `Ctrl+Shift+O` by default.
- **macOS**: `Cmd+Shift+O` or `Ctrl+Shift+O` by default.

Configure another supported combination in OTPilot's non-secret TOML configuration file, for example:

```toml
hotkey = "cmd+shift+o"
```

*Note:* On macOS, Accessibility permissions are required for hotkey capturing. On Linux, only X11 display servers are supported (Wayland is unsupported).

Press `Ctrl+C` to unregister the hotkey and exit. Each invocation copies the OTP to the clipboard; OTPilot never prints it in hotkey mode and does **not** paste it automatically.

## Privacy Guarantee (`fetch --copy`)

When using `otpilot fetch --copy` or running in hotkey mode, OTPilot copies the extracted OTP directly to your system clipboard without printing the value to terminal output.

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

- [installation.md](installation.md): installation and development setup.
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
