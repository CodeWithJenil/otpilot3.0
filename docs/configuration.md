# Configuration Reference

OTPilot separates configuration from preferences.

## Configuration

Configuration affects correctness and integration.

Current model:

- `provider.provider_id`: active provider. Default: `gmail`.
- `provider.account`: active account email. Default: unset.
- `credential_backend.backend`: credential backend. Default: `windows-credential-manager`.
- `config_dir`: override for local config path. Default: platform-specific.
- `poll_interval_seconds`: watch polling interval. Default: `30.0`; allowed range is greater than 0 and up to 3600 seconds.
- `hotkey`: Windows global hotkey for `otpilot hotkey`. Default: `ctrl+shift+o`. It must be a
  non-empty, plus-separated key combination with at least one modifier and a non-modifier key;
  for example, `alt+f9`.

Secrets are forbidden.

## Preferences

Preferences affect user experience.

Current model:

- `theme`: `system` by default.
- `notifications_enabled`: `true` by default.
- `auto_paste_enabled`: `false` by default.

## Storage

Configuration is stored as non-secret TOML under the platform-specific OTPilot config directory. Credentials remain in the operating system credential vault.

## Documentation Requirement

Any new configuration or preference option must update this file, `README.md` if user-facing, `developer-guide.md`, `docs/troubleshooting.md`, and `CHANGELOG.md`.
