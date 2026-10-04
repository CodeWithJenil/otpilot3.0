# OTPilot

[![PyPI version](https://img.shields.io/pypi/v/otpilot)](https://pypi.org/project/otpilot/)
[![Python versions](https://img.shields.io/pypi/pyversions/otpilot)](https://pypi.org/project/otpilot/)
[![Downloads](https://static.pepy.tech/personalized-badge/otpilot?period=month&units=INTERNATIONAL_SYSTEM&left_color=GREEN&right_color=BLACK&left_text=downloads%20this%20month)](https://pepy.tech/projects/otpilot)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**Retrieve email OTPs from your terminal and copy them to your clipboard—without manually searching your inbox.**

OTPilot is a local-first command-line tool for retrieving one-time passwords from Gmail over IMAP. Use it when you want a simpler workflow for email-based verification codes.

- **Clipboard support:** use `otpilot fetch --copy` to copy the detected OTP without printing its value to terminal output.
- **Local-first design:** email retrieval happens on your machine; OTPilot does not require a hosted relay or sync service.
- **Opt-in telemetry:** usage telemetry is disabled by default and is sent only if you explicitly enable it.
- **Credential storage:** credentials are stored through your operating system's credential vault rather than in the TOML configuration file.
- **Cross-platform CLI:** Windows, macOS, and Linux with X11 are supported. Linux Wayland is not currently supported.

## Get started

### 1. Install

Requires Python 3.12 or newer.

```bash
python -m pip install --upgrade otpilot
```

### 2. Configure Gmail access

OTPilot currently supports Gmail through IMAP over SSL and a Google App Password. Enable IMAP for your Gmail account and create an App Password if your Google account is eligible. Never share your App Password or commit it to a repository.

### 3. Sign in and fetch

```bash
otpilot login you@gmail.com
otpilot fetch --copy
```

Follow the prompts shown by the CLI. The `fetch --copy` command copies the detected OTP to your clipboard when a suitable code is found.

## Common commands

| Command | Purpose |
| --- | --- |
| `otpilot login you@gmail.com` | Configure an email account |
| `otpilot fetch` | Fetch and identify OTP candidates |
| `otpilot fetch --copy` | Copy the selected OTP to the clipboard |
| `otpilot watch` | Poll for new OTP messages |
| `otpilot hotkey` | Run the global-hotkey workflow |
| `otpilot config` | View or edit preferences |
| `otpilot doctor` | Diagnose common setup issues |
| `otpilot telemetry status` | Check telemetry status |
| `otpilot telemetry enable` | Explicitly enable optional telemetry |
| `otpilot telemetry disable` | Disable telemetry |
| `otpilot logout you@gmail.com` | Remove saved account credentials |

Run `otpilot --help` or consult the [CLI reference](docs/cli-reference.md) for details.

## Platform notes

- **Windows:** supported.
- **macOS:** supported; Accessibility permission may be required for global hotkey capture.
- **Linux:** X11 is supported; Wayland is not currently supported.

Hotkey combinations can be configured in OTPilot's non-secret TOML configuration file. See the [configuration guide](docs/configuration.md).

## Privacy and security

OTPilot is designed to keep email retrieval local and credentials out of plain-text configuration files.

- Credentials use the operating system credential vault through `keyring` (macOS Keychain, Windows Credential Manager, or a supported Linux Secret Service backend).
- OTP values copied with `fetch --copy` are not printed to terminal output by that command.
- Telemetry is **off by default**. You can inspect its status and enable or disable it with the commands above.
- Review the [privacy policy](privacy.md) and [security guidance](security.md) before use.

As with any tool that accesses email, review the permissions you grant and protect your account credentials.

## How it works

OTPilot is organized into layers that separate the CLI, application services, domain logic, providers, and infrastructure. Its current email provider is Gmail over IMAP. Other IMAP providers are architectural possibilities, not currently advertised as supported providers.

See [architecture.md](architecture.md) for the design and [developer-guide.md](developer-guide.md) for the development workflow.

## Documentation

- [Installation and development setup](installation.md)
- [CLI reference](docs/cli-reference.md)
- [Configuration](docs/configuration.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Architecture](architecture.md)
- [Security](security.md)
- [Privacy](privacy.md)
- [Contributing](contributing.md)
- [Roadmap](roadmap.md)
- [Changelog](CHANGELOG.md)

## Contributing

Issues, bug reports, and thoughtful contributions are welcome. Please read [contributing.md](contributing.md) before opening a pull request. When reporting an issue, include your OS, Python version, OTPilot version, and the command involved—never include OTPs, passwords, App Passwords, or private email content.

## License

OTPilot is released under the [MIT License](LICENSE).
