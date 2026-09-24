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

Inspect or update non-secret configuration and user preferences.

### Interactive Mode (Default)

When run in a real terminal (TTY), `otpilot config` launches an interactive
keyboard-navigable TUI:

- **↑ / ↓** — Navigate between settings
- **Enter** — Select and edit a setting
- **Esc** — Cancel editing or return to menu
- **q** or **Esc** (at top level) — Exit the configuration UI
- **← / →** — Navigate in confirmation dialogs

Settings are grouped into sections (Provider, Credential Backend, Watch,
Hotkeys, Preferences). Each setting shows its current value.

#### Editing Different Setting Types

- **Boolean settings** (e.g., `notifications_enabled`): Toggle via selection
  dialog with `true`/`false` options.
- **Enum settings** (e.g., `theme`, `provider_id`): Select from available
  options using arrow keys.
- **Text/Numeric settings** (e.g., `account`, `poll_interval_seconds`): Input
  with current value shown; validation applied on confirm.
- **Hotkey setting**: Press **Enter** on the hotkey row to open the capture
  dialog. The prompt reads "Press the desired key combination..." — physically
  press the keys you want (e.g., `Ctrl+Shift+O`). The detected combination is
  displayed. Press **Enter** to confirm, **Esc** to cancel. The combination is
  normalized consistently across platforms (e.g., `ctrl+shift+o`).

#### Restore Defaults

Navigate to the **Restore Defaults** action at the bottom and press **Enter**.
A confirmation dialog appears — select **Yes** to reset all configuration and
preferences to defaults (credentials are not removed).

### Non-Interactive Mode

Use `--non-interactive` (or `-n`) to force read-only output, suitable for
scripting and automation:

```bash
otpilot config --non-interactive
```

This prints the effective configuration (configured values, defaults, and
sources) and exits. The command also falls back to this mode automatically
when stdin is not a TTY.

### Subcommands

- `otpilot config` — Display the full effective configuration (configured values, defaults, and sources).
- `otpilot config get` — Display the full effective configuration.
- `otpilot config get <key>` — Display a specific setting with its value and source.
- `otpilot config set <key> <value>` — Update a supported non-secret setting.
- `otpilot config path` — Print the platform-specific configuration file path.
- `otpilot config reset [--yes]` — Restore configuration and preferences to defaults. Credentials are not removed. Use `--yes` to skip confirmation.

### Supported Configuration Keys

- `provider.provider_id` — Active provider (default: `gmail`).
- `provider.account` — Active account email (default: unset).
- `credential_backend.backend` — Credential backend (default: `keyring`).
- `poll_interval_seconds` — Watch polling interval in seconds (default: `30.0`, range: `>0` to `3600`).
- `hotkey` — Global hotkey combination (default: `ctrl+shift+o` or `cmd+shift+o` on macOS).

### Supported Preference Keys

- `preferences.theme` — UI theme: `system`, `light`, or `dark` (default: `system`).
- `preferences.notifications_enabled` — Enable desktop notifications (default: `true`).
- `preferences.auto_paste_enabled` — Auto-paste OTP after copy (default: `false`).

### Notes

- Configuration and preferences are stored as non-secret TOML files.
- Secrets (passwords, tokens) are never stored in configuration files; they use the OS credential vault via `keyring`.
- The `config_dir` setting is derived from the platform config path and cannot be changed via `config set`.
- Invalid values are rejected with clear error messages and non-zero exit codes.
- Configuration writes are atomic.

## `otpilot doctor`

Inspect local configuration, provider availability, credential backend support, and platform status.

### Options

- `--offline` — Skip the live Gmail IMAP login check.

### Diagnostic Categories

- **Environment** — Python version compatibility, operating system, OTPilot version.
- **Configuration** — Config directory writability, file permissions, config file validity, account configuration, preferences file validity.
- **Credentials** — Keyring backend availability, stored credentials presence.
- **Connectivity** — Gmail IMAP login test (skipped if `--offline`, credentials missing, or config invalid).
- **Clipboard** — Clipboard backend availability.
- **Hotkeys** — Hotkey environment support (X11/Wayland on Linux, Accessibility on macOS).
- **Dependencies** — Importability of required runtime dependencies.

### Status Values

- `PASS` — Check succeeded.
- `WARN` — Check passed with caveats; action may be needed.
- `FAIL` — Check failed; action required.
- `SKIP` — Check not performed (e.g., `--offline`, missing prerequisites).

### Exit Codes

- `0` — Diagnostics completed with no critical failures (`FAIL`).
- `1` — One or more checks reported `FAIL`.

### Notes

- No secrets (credentials, OTPs) are printed in diagnostics.
- The connectivity check authenticates via IMAP but does not download messages.
- Hotkey checks do not register a permanent listener.

## `otpilot version`

Print the installed package version.

## Documentation Requirement

Any command addition or behavior change must update this file, `README.md`, `docs/troubleshooting.md`, and `CHANGELOG.md`.
