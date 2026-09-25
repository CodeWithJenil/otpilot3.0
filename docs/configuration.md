# Configuration Reference

OTPilot separates configuration from preferences.

## Configuration

Configuration affects correctness and integration.

Current model:

- `provider.provider_id`: active provider. Default: `gmail`.
- `provider.account`: active account email. Default: unset.
- `credential_backend.backend`: credential backend. Default: `keyring`.
- `config_dir`: override for local config path. Default: platform-specific.
- `poll_interval_seconds`: watch polling interval. Default: `30.0`; allowed range is greater than 0 and up to 3600 seconds.
- `hotkey`: global hotkey for `otpilot hotkey`. Default: `ctrl+shift+o` (or `cmd+shift+o` on macOS). It must be a non-empty, plus-separated key combination with at least one modifier (`ctrl`, `shift`, `alt`, `cmd`) and a non-modifier key; for example, `cmd+shift+o` or `alt+f9`.

Secrets are forbidden in configuration files.

## Preferences

Preferences affect user experience.

Current model:

- `theme`: `system` by default. Options: `system`, `light`, `dark`.
- `notifications_enabled`: `true` by default. Boolean.
- `auto_paste_enabled`: `false` by default. Boolean.

## Interactive Configuration UI

Run `otpilot config` in a terminal to launch a synchronous, keyboard-navigable
editor:

- **Navigation**: ↑/↓ to move the selection (section headers are skipped),
  Enter to select, Esc to cancel or exit at top level. `q`, `Ctrl+C`, and
  `Ctrl+D` also exit at top level.
- **Boolean/Enum settings**: Selection dialog with the current value
  preselected; ↑/↓ to navigate, Enter to confirm, Esc to cancel.
- **Text/Numeric settings**: Current value shown above a fresh input line;
  invalid values show an inline error and clear the input for another try.
- **Hotkey capture**: Press Enter on the hotkey row, then physically press
  the desired key combination. Esc cancels, and the capture ends on its own
  after 30 seconds. Captured combinations are validated before saving. On
  macOS the hosting terminal must have Accessibility / Input Monitoring
  permission; an actionable error is shown when macOS blocks input
  monitoring.
- **Reset to Defaults**: Navigate to the action near the bottom, confirm in
  dialog. Stored credentials are not removed.

Use `otpilot config --non-interactive` (or `-n`) for scriptable read-only
output. The command also falls back to this mode automatically when stdin is
not a TTY.

## Storage

Configuration is stored as non-secret TOML under the platform-specific OTPilot
config directory. Credentials remain in the operating system credential vault
via `keyring`.

### Platform Config Paths

| Platform | Config Directory                                   |
| -------- | -------------------------------------------------- |
| Linux    | `~/.config/otpilot/` (respects `$XDG_CONFIG_HOME`) |
| macOS    | `~/Library/Application Support/otpilot/`           |
| Windows  | `%APPDATA%\otpilot\`                               |

Files:

- `config.toml` — Configuration
- `preferences.toml` — Preferences

Writes are atomic (temp file + rename) for crash safety.

## Platform Limitations

### Hotkey Capture (Interactive Config)

| Platform      | Support                                      | Notes                                                                               |
| ------------- | -------------------------------------------- | ----------------------------------------------------------------------------------- |
| Windows       | ✅ Full                                      | Works in CMD, PowerShell, Windows Terminal                                          |
| macOS         | ✅ Full                                      | Requires Accessibility **and** Input Monitoring permissions for the terminal app   |
| Linux X11     | ✅ Full                                      | Works in GNOME Terminal, Konsole, etc.                                              |
| Linux Wayland | ⚠️ Capture works, global hotkeys unsupported | `pynput` cannot register global hotkeys on Wayland; use XWayland or X11 session     |
| SSH/Remote    | ⚠️ Capture may not work                      | Requires proper TTY allocation (`ssh -t`)                                           |

> **macOS Users:** To capture a hotkey in `otpilot config`, your terminal application (Terminal.app, iTerm2, etc.) must have **both** Accessibility **and** Input Monitoring permissions.  
> Go to **System Settings → Privacy & Security → Accessibility** and enable your terminal.  
> Then go to **System Settings → Privacy & Security → Input Monitoring** and enable your terminal.  
> Restart your terminal after granting permissions.

### Global Hotkey Registration (`otpilot hotkey`)

| Platform      | Support                   | Notes                                                         |
| ------------- | ------------------------- | ------------------------------------------------------------- |
| Windows       | ✅ Full                   |                                                               |
| macOS         | ⚠️ Requires Accessibility | Grant in System Settings → Privacy & Security → Accessibility |
| Linux X11     | ✅ Full                   |                                                               |
| Linux Wayland | ❌ Unsupported            | `pynput` limitation; no known workaround                      |
| SSH/Remote    | ❌ Unsupported            | No display server access                                      |

### Terminal Compatibility

The interactive UI requires a terminal that supports:

- ANSI escape sequences (colors, cursor movement)
- Raw mode input (for key capture)
- Minimum width: 60 columns

Known compatible terminals: Windows Terminal, Terminal.app, iTerm2, GNOME Terminal, Konsole, Alacritty, Kitty, foot.

## Documentation Requirement

Any new configuration or preference option must update this file, `README.md` if user-facing, `developer-guide.md`, `docs/troubleshooting.md`, and `CHANGELOG.md`.
