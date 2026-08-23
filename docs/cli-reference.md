# CLI Reference

## `otpilot fetch`

Fetch the most probable OTP from the active email account.

Options:

- `--copy`: copy the discovered OTP to the system clipboard.

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

Watch mode does not implement hotkeys, notifications, auto-paste, or daemon management.

## `otpilot login <email>`

Store credentials for an email account using the secure credential backend.

The command must never write app passwords to config, logs, shell history helpers, or documentation examples.

## `otpilot logout <account>`

Remove stored credentials for an email account from the credential backend.

## `otpilot config`

Inspect or update non-secret configuration and preferences.

Configuration and preferences must stay separated.

## `otpilot doctor`

Inspect local configuration, provider availability, credential backend support, and platform status.

## `otpilot version`

Print the installed package version.

## Documentation Requirement

Any command addition or behavior change must update this file, `README.md`, `docs/troubleshooting.md`, and `CHANGELOG.md`.
