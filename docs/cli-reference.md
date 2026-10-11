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

Unified monitoring for new OTP emails. The monitoring mode is determined by the
``hotkey_enabled`` configuration setting (default: ``false``).

### Monitoring Mode A: Hotkey enabled (``hotkey_enabled = true``)

When ``hotkey_enabled`` is ``true``, watch mode waits for the configured global
hotkey instead of performing periodic mailbox polling.

- Each valid hotkey activation triggers an immediate mailbox check.
- Overlapping mailbox checks are prevented.
- Provides consistent behaviour across ``watch`` and the daemon.
- The configured hotkey (default: ``ctrl+shift+o``) must be registered via
  ``otpilot config``.

### Monitoring Mode B: Hotkey disabled (``hotkey_enabled = false``, default)

When ``hotkey_enabled`` is ``false`` (the default), watch mode checks the
mailbox every ``poll_interval_seconds`` (default: ``3.0`` seconds).

- The polling interval configured via ``otpilot config`` is respected.
- Concurrent polling operations are avoided.
- Timeouts, connection loss, authentication failures, and reconnection are
  handled safely.
- Valid newly detected OTPs are copied using the existing clipboard implementation.

**The same configuration semantics apply to both ``otpilot watch`` and
``otpilot daemon``.**

The default polling interval is 3 seconds, settable via:

```bash
otpilot config set poll_interval_seconds 5.0
```

Options:

- `--copy` (deprecated in watch mode, use with ``otpilot fetch``): copy the
  discovered OTP to the system clipboard without displaying/printing the value
  to terminal output.

Behavior (hotkey disabled):

```text
WatchService
  -> FetchOtpService
  -> ClipboardService
```

Behavior (hotkey enabled):

```text
HotkeyService
  -> FetchOtpService
  -> ClipboardService
```

Watch mode does not implement notifications, auto-paste, or separate daemon
management.

## `otpilot login`

Interactive login: prompt for email address and Gmail App Password, validate the
IMAP connection, and store credentials securely.

The command must not be called with an email argument:

```bash
otpilot login
```

**Flow:**

1. Prompt for email address (validated format required).
2. Prompt for App Password (masked input).
3. Test IMAP connection with provided credentials.
4. On success: store credentials in the OS keyring.
5. On failure: display error and allow retry.

**Requirements:**

- Email and password are never printed, logged, or exposed in diagnostic output.
- Credentials are stored using the OS credential vault via ``keyring``.
- Never saved in plaintext configuration files.
- Invalid credentials, IMAP connection failures, and interrupted input are
  handled cleanly.
- Use ``otpilot logout <account>`` to remove stored credentials.

## `otpilot logout <account>`

Remove stored credentials for an email account from the credential backend.

## `otpilot config`

Inspect or update non-secret configuration and user preferences.

### Interactive Mode (Default)

When run in a real terminal (TTY), ``otpilot config`` launches a synchronous,
keyboard-navigable settings editor. See the interactive editor documentation for
keybindings and setting types.

### Non-Interactive Mode

Use ``--non-interactive`` (or ``-n``) to force read-only output, suitable for
scripting and automation:

```bash
otpilot config --non-interactive
```

This prints the effective configuration and exits. The command also falls back
to this mode automatically when stdin is not a TTY.

### Configuration Keys

- ``provider.provider_id`` — Active provider (default: ``gmail``).
- ``provider.account`` — Active account email (default: unset).
- ``credential_backend.backend`` — Credential backend (default: ``keyring``).
- ``poll_interval_seconds`` — Watch polling interval in seconds (default: ``3.0``,
  range: ``>0`` to ``3600``).
- ``hotkey`` — Global hotkey combination (default: ``ctrl+shift+o`` or
  ``cmd+shift+o`` on macOS). See the interactive editor for validation rules.
- ``hotkey_enabled`` — Enable hotkey-based monitoring (default: ``false``).
  When ``true``, ``otpilot watch`` and ``otpilot daemon`` use hotkey events
  instead of periodic polling.

### Supported Preference Keys

- ``preferences.theme`` — UI theme: ``system``, ``light``, or ``dark`` (default:
  ``system``).
- ``preferences.notifications_enabled`` — Enable desktop notifications (default:
  ``true``).
- ``preferences.auto_paste_enabled`` — Auto-paste OTP after copy (default:
  ``false``).
- ``preferences.telemetry_enabled`` — Enable anonymous usage telemetry (default:
  ``false``).
- ``preferences.telemetry_installation_id`` — Installation ID for telemetry
  (auto-generated).
- ``preferences.feedback_prompts_enabled`` — Enable feedback prompts after
  commands (default: ``true``).
- ``preferences.feedback_prompt_min_commands`` — Minimum commands before feedback
  prompt (default: ``5``).
- ``preferences.feedback_commands_since_prompt`` — Internal counter (default:
  ``0``).
- ``preferences.community_messages_enabled`` — Enable randomized community
  messages (default: ``true``).
- ``preferences.community_message_probability`` — Probability of showing a
  community message (default: ``0.15``, range: ``0.0`` to ``1.0``).

### Notes

- Configuration and preferences are stored as non-secret TOML files.
- Secrets (passwords, tokens) are never stored in configuration files; they use
  the OS credential vault via ``keyring``.
- The ``config_dir`` setting is derived from the platform config path and cannot
  be changed via the ``config`` command.
- Invalid values are rejected with clear error messages and non-zero exit codes.
- Configuration writes are atomic.

## `otpilot daemon`

Manage the OTPilot background daemon for persistent OTP polling.

### Subcommands

- ``otpilot daemon install [--autostart]`` — Install the daemon (create service
  files). Use ``--autostart`` to enable automatic startup on login.
- ``otpilot daemon uninstall`` — Uninstall the daemon (remove service files).
- ``otpilot daemon start`` — Start the daemon.
- ``otpilot daemon stop`` — Stop the daemon.
- ``otpilot daemon restart`` — Restart the daemon.
- ``otpilot daemon status`` — Show daemon status (installed, running, PID,
  autostart, state).
- ``otpilot daemon enable-autostart`` — Enable daemon autostart on login.
- ``otpilot daemon disable-autostart`` — Disable daemon autostart on login.
- ``otpilot daemon run-internal`` — Internal command to run the daemon watch
  loop (not for direct use).

### Daemon Monitoring Mode

The daemon respects the ``hotkey_enabled`` and ``poll_interval_seconds``
configuration settings, just like ``otpilot watch``.

- When ``hotkey_enabled = true``: the daemon uses hotkey-based monitoring.
- When ``hotkey_enabled = false`` (default): the daemon uses polling with the
  configured interval, or IMAP IDLE if an account is authenticated.

### Platform Implementation

- **Windows**: Background process with PID file
  (`%LOCALAPPDATA%\otpilot\daemon.pid`). Optional autostart via Windows Registry
  ``Run`` key.
- **macOS**: Per-user ``launchd`` LaunchAgent
  (`~/Library/LaunchAgents/com.jenil.otpilot.plist`). Uses ``launchctl bootstrap``.
- **Linux**: Prefers ``systemd --user``
  (`~/.config/systemd/user/otpilot.service`). Falls back to background process
  with PID file (`~/.local/state/otpilot/daemon.pid`) if systemd is unavailable.

### Daemon Behavior

The daemon reuses existing configuration and credentials from the OS keyring.
It does not print OTPs or credentials to logs. Handles graceful shutdown on
``stop`` and ``restart``. Prevents duplicate instances via PID file / service
management. Cleans up stale PID files on startup.

### Notes

- Daemon installation does not require administrator privileges (per-user only).
- On Linux without systemd, autostart is not automatically configured.
- The daemon respects the same ``poll_interval_seconds`` setting as ``otpilot watch``.
- Run ``otpilot doctor`` to diagnose daemon status and configuration.

## `otpilot version`

Print the installed package version.

## `otpilot telemetry`

Manage anonymous usage telemetry.

### Subcommands

- ``otpilot telemetry status`` — Show whether telemetry is enabled and display
  the installation ID (if enabled).
- ``otpilot telemetry enable`` — Enable telemetry. Generates a random
  installation ID if none exists.
- ``otpilot telemetry disable`` — Disable telemetry. Stops future transmission.
  Preserves the installation ID locally.

### Telemetry Principles

- **Opt-in only**: Telemetry is disabled by default. You must explicitly run
  ``otpilot telemetry enable``.
- **Anonymous**: A cryptographically random UUID is generated locally. It is not
  derived from hardware, hostname, username, or identity.
- **Minimal payload**: Only operational metadata is sent (installation ID, event
  name, version, Python version, OS, architecture, timestamp, optional command
  name from allowlist).
- **No sensitive data**: Never collects emails, OTPs, credentials, clipboard
  contents, file paths, usernames, IP addresses, exact location, hostnames, or
  command arguments.
- **Asynchronous & non-blocking**: Telemetry is dispatched in a background thread.
- **Failure-tolerant**: Network failures, timeouts, or server errors are silently
  ignored.
- **Easy to disable**: ``otpilot telemetry disable`` stops transmission immediately.

### What IS Collected (if enabled)

| Field | Example |
|-------|---------|
| ``installation_id`` | ``a1b2c3d4-e5f6-7890-abcd-ef1234567890`` |
| ``event`` | ``app_started``, ``command_executed`` |
| ``version`` | ``3.0.1`` |
| ``python_version`` | ``3.12`` |
| ``os`` | ``macos``, ``linux``, ``windows`` |
| ``architecture`` | ``x86_64``, ``arm64`` |
| ``timestamp`` | ``2026-09-27T10:15:00Z`` |
| ``command`` (optional) | ``fetch``, ``watch``, ``hotkey`` |

### What is NOT Collected

- Email addresses, email contents, OTP codes
- Credentials, passwords, access tokens
- Clipboard contents, file paths, usernames
- IP addresses (beyond inherent HTTP metadata), exact location, hostnames
- Command arguments or any sensitive data

### End-of-Command Suggestion

When telemetry is disabled, a brief suggestion appears at the end of normal
human-readable command output:

```text
Telemetry is currently disabled.
Enable anonymous telemetry to help improve OTPilot:
  otpilot telemetry enable
```

This suggestion:
- Appears after the command's normal output
- Does not interfere with command results or machine-readable output (e.g., JSON)
- Does not appear for ``telemetry`` subcommands themselves
- Is concise and non-intrusive

### Installation ID Lifecycle

- Generated only when telemetry is first enabled.
- Stored in local preferences (not config, not keyring).
- Persists across OTPilot runs.
- Preserved when telemetry is disabled; reused if re-enabled later.
- Not derived from MAC address, hostname, username, email, or hardware identifiers.

## `otpilot community messages`

After successful, interactive commands, OTPilot may occasionally display a
randomized community message (default 15% probability). This is a lightweight,
offline feature that never makes network requests.

### Message Pool

One of three messages is randomly selected:

1. **Review** — "Enjoying OTPilot? Share your review:
   https://jenil-otpilot.vercel.app/feedback"
2. **Issues** — "Found a bug or issue? Report it here:
   https://github.com/CodeWithJenil/otpilot3.0/issues"
3. **Discussions** — "Have an idea or question? Join the discussion:
   https://github.com/CodeWithJenil/otpilot3.0/discussions"

### Behavior

- Shown after command output, before the telemetry suggestion (if any)
- Only in interactive TTY sessions (`stdout.isatty()`)
- Only for successful commands (exit code 0)
- Suppressed for: ``telemetry``, ``version``, ``daemon``, ``config``,
  ``doctor``, ``login``, ``logout`` subcommands
- At most one message per command
- Supports OSC 8 hyperlinks in compatible terminals (plain URL shown as fallback)

### Configuration

- ``preferences.community_messages_enabled`` — Enable/disable (default: ``true``)
- ``preferences.community_message_probability`` — Probability 0.0–1.0 (default:
  ``0.15``)

```bash
# Disable community messages
otpilot config set preferences.community_messages_enabled false

# Change probability to 5%
otpilot config set preferences.community_message_probability 0.05
```

## Documentation Requirement

Any command addition or behavior change must update this file, ``README.md``,
``docs/troubleshooting.md``, and ``CHANGELOG.md