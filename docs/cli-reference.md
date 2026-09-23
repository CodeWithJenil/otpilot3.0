# CLI Reference

## `otpilot fetch`

Fetch the most probable OTP from the active email account.

Options:

- `--copy`: copy the discovered OTP to the system clipboard without displaying/printing the value to terminal output.

Behavior:

```text
FetchOtpService
  -> cache lookup
  -> provider search
  -> message download
  -> OtpExtractor
  -> optional clipboard copy
```

## `otpilot watch`

Poll for new OTP emails and copy newly detected OTPs to the system clipboard.

The default polling interval is 30 seconds. Press `Ctrl+C` to stop cleanly.

Behavior:

```text
WatchService
  -> FetchOtpService
  -> ClipboardService
```

Watch mode does not implement notifications, auto-paste, or daemon management.

## `otpilot hotkey`

Listen for the configured global hotkey (`Ctrl+Shift+O` on Windows/Linux X11, `Cmd+Shift+O` or `Ctrl+Shift+O` on macOS), fetch the latest OTP, and copy it to the system clipboard. Press `Ctrl+C` to stop and unregister it cleanly. Each successful trigger reports `OTP copied to clipboard.` without printing the OTP value.

Hotkey listening is supported on Windows, macOS (requires Accessibility permissions), and Linux X11 (Wayland unsupported). It uses the cross-platform `pynput` dependency. Fetch and clipboard failures are reported and leave the listener active. Repeated presses while a fetch is already in progress are ignored. The command copies an OTP but never prints or automatically pastes it.

## `otpilot login <email>`

Store credentials for an email account using the secure credential backend (`keyring`).

The command must never write app passwords to config, logs, shell history helpers, or documentation examples.

## `otpilot logout <account>`

Remove stored credentials for an email account from the credential backend.

## `otpilot config`

Inspect or update non-secret configuration and preferences (*scaffolded command*).

Configuration and preferences must stay separated.

## `otpilot doctor`

Inspect local configuration, provider availability, credential backend support, and platform status (*scaffolded command*).

## `otpilot version`

Print the installed package version.

## Documentation Requirement

Any command addition or behavior change must update this file, `README.md`, `docs/troubleshooting.md`, and `CHANGELOG.md`.
