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

Run `otpilot config` in a terminal to launch an interactive keyboard-navigable
interface:

- **Navigation**: ↑/↓ to move between settings, Enter to edit, Esc to cancel,
  q or Esc (at top level) to exit.
- **Boolean/Enum settings**: Selection dialog with arrow keys.
- **Text/Numeric settings**: Input field with current value prefilled.
- **Hotkey capture**: Press Enter on the hotkey row, then physically press the
  desired key combination. The detected combination is displayed and normalized.
  Enter confirms, Esc cancels.
- **Restore Defaults**: Navigate to the action at the bottom, confirm in dialog.

Use `otpilot config --non-interactive` (or `-n`) for scriptable read-only output.

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
| macOS         | ✅ Full                                      | Requires Accessibility permissions for global hotkey registration (not for capture) |
| Linux X11     | ✅ Full                                      | Works in GNOME Terminal, Konsole, etc.                                              |
| Linux Wayland | ⚠️ Capture works, global hotkeys unsupported | `pynput` cannot register global hotkeys on Wayland; use XWayland or X11 session     |
| SSH/Remote    | ⚠️ Capture may not work                      | Requires proper TTY allocation (`ssh -t`)                                           |

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
