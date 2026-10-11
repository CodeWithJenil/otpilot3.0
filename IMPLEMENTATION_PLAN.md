# OTPilot v3.1.2 Implementation Plan

## 1. Cross-Platform Daemon Support

### Architecture
- **Shared interface**: `DaemonManager` protocol in `application/ports.py`
- **Platform adapters** in `infrastructure/daemon/`:
  - `windows.py`: Background process with PID file management
  - `macos.py`: Per-user `launchd` LaunchAgent (`~/Library/LaunchAgents/com.jenil.otpilot.plist`)
  - `linux.py`: `systemd --user` service with fallback to background process
- **CLI command**: `cli/commands/daemon.py` with `start`, `stop`, `status`, `restart`, `enable-autostart`, `disable-autostart`
- **Service integration**: Daemon runs `WatchService` for background OTP polling
- **Doctor integration**: Add daemon health checks

### Platform Details

#### Windows
- Use `subprocess.Popen` with `CREATE_NO_WINDOW` flag
- PID file at `%LOCALAPPDATA%\otpilot\daemon.pid`
- Auto-start via Windows Registry `Run` key (optional, user-enabled)
- Graceful shutdown via `CTRL_BREAK_EVENT` or `taskkill`

#### macOS
- LaunchAgent plist at `~/Library/LaunchAgents/com.jenil.otpilot.plist`
- Use `launchctl bootstrap gui/$(id -u)` for per-user loading
- Executable: `sys.executable -m otpilot.cli.app daemon run-internal`
- Working directory: user's home or config directory
- Handle spaces in paths, virtual environment Python paths

#### Linux
- Primary: `systemd --user` service at `~/.config/systemd/user/otpilot.service`
- Fallback: Background process with PID file at `~/.local/state/otpilot/daemon.pid`
- Check for `systemd --user` availability via `systemctl --user status`
- Auto-start via `systemctl --user enable`

### Reliability
- Single-instance enforcement via PID file + process verification
- Stale PID detection and cleanup
- Graceful shutdown with timeout and force-kill fallback
- No duplicate LaunchAgents/systemd services after upgrades

## 2. Feedback Page & Database Integration

### Fixes Needed
- **UserPreferences model**: Add `feedback_prompts_enabled`, `feedback_prompt_min_commands`, `feedback_commands_since_prompt` fields
- **SettingsService**: Add parsing for feedback preference keys
- **SettingsService.SUPPORTED_KEYS**: Include feedback keys

### Website Integration
- Register `/feedback` route in `web/src/App.tsx`
- Add "Feedback" link to Footer component
- Verify existing `Feedback.tsx` page and `/api/feedback` endpoint work correctly
- Neon schema already exists in `web/feedback_schema.sql`

### Database
- Table: `feedback_submissions` (already defined)
- API: `/api/feedback.ts` (already implemented)
- Migration: Provided in `web/feedback_schema.sql`

## 3. Randomized Community Messages

### Implementation
- **Location**: Extend `TelemetryTyper.__call__` in `cli/app.py` (after telemetry suggestion)
- **Probability**: 15% default, configurable via `preferences.community_message_probability` (0.0-1.0)
- **Disable option**: `preferences.community_messages_enabled` (default: true)
- **Message pool** (randomized selection):
  1. "Enjoying OTPilot? Share your review: https://jenil-otpilot.vercel.app/feedback"
  2. "Found a bug or issue? Report it here: https://github.com/CodeWithJenil/otpilot3.0/issues"
  3. "Have an idea or question? Join the discussion: https://github.com/CodeWithJenil/otpilot3.0/discussions"

### Eligibility Rules
- **Show when**: Interactive TTY (`sys.stdout.isatty()`), command succeeded (exit code 0), human-readable output
- **Suppress when**: Non-TTY, JSON/machine output, failed commands, `telemetry` subcommands, `version`, `doctor --offline`, `config --non-interactive`
- **At most one message per command**
- **OSC 8 hyperlinks** for supported terminals, plain URL fallback

### Testing
- Mock `random.random()` for deterministic tests
- Test probability boundaries, message selection, suppression rules
- Test preservation of exit codes and stdout/stderr

## 4. Documentation & Release

### Updates Required
- `pyproject.toml`: version = "3.1.2"
- `CHANGELOG.md`: Add 3.1.2 entry
- `README.md`: Daemon commands, community messages note
- `docs/cli-reference.md`: Daemon command reference
- `docs/configuration.md`: New preferences (community messages, feedback)
- `docs/troubleshooting.md`: Daemon troubleshooting per platform
- Website: Footer link to Feedback, version references

### Tests
- Daemon lifecycle tests (mocked platform adapters)
- Community message probability and eligibility tests
- Feedback preference persistence tests
- Integration tests for CLI commands

## 5. File Changes Summary

### New Files
- `src/otpilot/application/ports.py` - Add `DaemonManager` protocol
- `src/otpilot/infrastructure/daemon/__init__.py`
- `src/otpilot/infrastructure/daemon/windows.py`
- `src/otpilot/infrastructure/daemon/macos.py`
- `src/otpilot/infrastructure/daemon/linux.py`
- `src/otpilot/infrastructure/daemon/factory.py` - Platform adapter factory
- `src/otpilot/cli/commands/daemon.py`
- `tests/test_daemon.py`
- `tests/test_community_messages.py`

### Modified Files
- `src/otpilot/__init__.py` - Version 3.1.2
- `pyproject.toml` - Version 3.1.2
- `src/otpilot/preferences/models.py` - Add feedback + community message fields
- `src/otpilot/application/settings.py` - Parse feedback + community message keys
- `src/otpilot/application/feedback.py` - Fix to use actual preference fields
- `src/otpilot/cli/app.py` - Add daemon command, community message logic
- `src/otpilot/application/doctor.py` - Add daemon diagnostics
- `src/otpilot/application/services.py` - Add `DaemonService` if needed
- `web/src/App.tsx` - Add `/feedback` route
- `web/src/components/Footer.tsx` - Add Feedback link
- `CHANGELOG.md` - 3.1.2 entry
- `README.md` - Updates
- `docs/cli-reference.md` - Daemon commands
- `docs/configuration.md` - New preferences
- `docs/troubleshooting.md` - Daemon troubleshooting

## 6. Dependencies
- No new Python dependencies required (uses stdlib: `subprocess`, `plistlib`, `pathlib`, `sys`, `os`)
- No new Node.js dependencies for website

## 7. Testing Strategy
- Unit tests with mocks for platform-specific daemon operations
- Integration tests for CLI command flow
- Deterministic community message tests using seeded `random.Random`
- Doctor diagnostics tests for daemon checks