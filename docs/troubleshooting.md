# Troubleshooting

## Watch mode stops immediately

Watch mode requires an active account and stored credentials. Run `otpilot login <email>` first.

Use `Ctrl+C` to stop a running watch session cleanly.

## Gmail login does not work

Confirm that the credential backend (`keyring`) is available and that the account uses a Gmail App Password.
On Linux, ensure a Secret Service provider (such as GNOME Keyring, KWallet, or KeePassXC with Secret Service enabled) is running and unlocked.

## IMAP fetch does not work

Temporary provider failures are retried by watch mode. Missing configuration or credentials are fatal and stop the command.

Each IMAP authentication and search operation uses a separate connection with a 30-second timeout.
OTPilot attempts logout after every opened connection, including when authentication, search, or
message retrieval fails. Timeout, connection, authentication, mailbox, and protocol failures are
reported without including credentials or email content.

## Clipboard copy does not work

`otpilot fetch --copy` and `otpilot watch` require an operating-system clipboard backend supported by `pyperclip`.

## Hotkey does not start or respond

`otpilot hotkey` uses `pynput` for cross-platform hotkey capturing:

- **macOS**: Hotkey listeners require Accessibility permissions. Grant permission to your terminal application under `System Settings > Privacy & Security > Accessibility`.
- **Linux**: Global hotkeys are supported under X11 display servers only. Wayland is currently unsupported for hotkey interception due to compositor security restrictions.
- **Windows / General**: Ensure no other program owns the shortcut (default: `ctrl+shift+o` on Windows/Linux, `cmd+shift+o` or `ctrl+shift+o` on macOS) and run `otpilot login <email>` before starting the listener. A fetch failure is reported without stopping the listener; press `Ctrl+C` to stop it cleanly.

## Linux Secret Service / Keyring Issues

On Linux, `keyring` requires a supported Secret Service daemon (such as GNOME Keyring, KWallet, or KeePassXC) to store credentials securely. If credential operations fail, verify that a Secret Service daemon is active and unlocked in your desktop session.

## Wayland Limitation Note

On Linux desktop environments using Wayland, global hotkey capture via `pynput` is unsupported due to Wayland security restrictions blocking global key logging. Switch to an X11 session or use `otpilot fetch` / `otpilot watch` commands.

## Documentation looks stale

Open an issue or pull request. Public behavior changes are incomplete unless the relevant documentation is updated.

## Running Diagnostics with `otpilot doctor`

Use `otpilot doctor` to diagnose installation, configuration, and runtime issues. The command performs checks across multiple categories and reports a summary with `PASS`, `WARN`, `FAIL`, and `SKIP` statuses.

### Common Diagnostic Scenarios

- **No email account configured**: Run `otpilot login <email>` to store credentials and set the active account.
- **Gmail credentials not stored**: The doctor will warn if credentials are missing. Run `otpilot login <email>` with a Gmail App Password.
- **Keyring backend unavailable**: On Linux, ensure a Secret Service daemon (GNOME Keyring, KWallet, KeePassXC) is running and unlocked.
- **Configuration file permissions too open**: The doctor will warn if the config file is group- or world-readable. Fix with `chmod 600 <config-path>`.
- **macOS Accessibility permission not granted**: Grant Accessibility access to your terminal under `System Settings > Privacy & Security > Accessibility`.
- **Linux Wayland session**: Global hotkeys require X11. Switch to an X11 session or use `otpilot fetch` / `otpilot watch`.
- **Missing or broken dependencies**: Reinstall OTPilot with `pip install --force-reinstall otpilot`.

### Offline Mode

Use `otpilot doctor --offline` to skip the live Gmail IMAP connectivity check. This is useful when network access is restricted or when credentials are not yet configured.

### Exit Codes

- `0`: No critical failures (`FAIL` status).
- `1`: One or more critical failures detected.

The doctor never prints secrets (credentials, OTPs) in its output.
