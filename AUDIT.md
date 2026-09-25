# Phase 1 Audit — OTPilot Interactive `config` Command

## 1. Existing Configuration Keys and Types

| Key | Type | Source | Settable | Validation |
|-----|------|--------|----------|------------|
| `provider.provider_id` | str (enum: "gmail") | Config | Yes | Must be "gmail" |
| `provider.account` | str \| None | Config | Yes | Stripped; empty → None |
| `credential_backend.backend` | str (enum: "keyring") | Config | Yes | Must be "keyring" |
| `config_dir` | Path \| None | Config | **No** (derived) | Derived from platform config path |
| `poll_interval_seconds` | float | Config | Yes | 0 < value ≤ 3600 |
| `hotkey` | str | Config | Yes | Modifier(s) + non-modifier key (e.g., `ctrl+shift+o`) |
| `preferences.theme` | str (enum: "system", "light", "dark") | Preferences | Yes | Must be one of three |
| `preferences.notifications_enabled` | bool | Preferences | Yes | true/1/yes/on or false/0/no/off |
| `preferences.auto_paste_enabled` | bool | Preferences | Yes | true/1/yes/on or false/0/no/off |

**SETTABLE_KEYS**: All except `config_dir` (8 keys total).

---

## 2. Existing Validation Rules

Defined in `SettingsService._parse_value()` and `AppConfig` model validators:

- **Hotkey**: `_validate_hotkey()` — requires ≥1 modifier (`ctrl`, `alt`, `shift`, `win`, `cmd`) + one non-modifier key (letter, digit, F1–F24, space, enter, tab, esc). Modifiers must be unique and precede the final key.
- **Poll interval**: `float` with Pydantic `gt=0, le=3600`.
- **Provider ID**: Only `"gmail"` supported.
- **Credential backend**: Only `"keyring"` supported.
- **Theme**: `"system"`, `"light"`, or `"dark"`.
- **Booleans**: Case-insensitive `true`/`1`/`yes`/`on` or `false`/`0`/`no`/`off`.
- **Account**: Stripped; empty string → `None`.

Validation errors are formatted via `_format_validation_error()` and raised as `ConfigurationError` or `PreferenceError`.

---

## 3. Existing Persistence Behavior

- **Repositories**: `TomlConfigurationRepository` (config.toml), `TomlPreferencesRepository` (preferences.toml).
- **Atomic writes**: Via `dump_toml_atomic()` — temp file + `os.replace()`.
- **Paths**: `platformdirs.user_config_path("otpilot")` (respects XDG on Linux, `~/Library/Application Support` on macOS).
- **SettingsService.snapshot()**: Returns `SettingsSnapshot` with all entries, source tracking (`configured`/`default`/`unset`/`derived`), and redaction for secret-like keys.
- **SettingsService.set()**: Validates → updates model → saves via repository → returns `SettingEntry`.
- **SettingsService.reset()**: Calls `clear()` on both repositories (deletes files). **Credentials are stored separately (keyring) and never touched.**

---

## 4. Existing Public CLI Behavior

| Command | Behavior |
|---------|----------|
| `otpilot config` | Interactive editor (falls back to non-interactive if stdin not a TTY) |
| `otpilot config --non-interactive` / `-n` | Read-only display of current configuration |
| `otpilot config --help` | Shows help |

**Interactive Editor Flow:**
1. Load snapshot via `SettingsService.snapshot()`
2. Build menu via `SettingsMenu.build_items()`
3. Enter `raw_mode()` (cbreak, no echo, ISIG enabled)
4. Render menu → read key → dispatch:
   - `↑`/`↓`: Navigate (skips section headers)
   - `Enter`: Open editor for selected setting
   - `Esc`/`Ctrl+C`/`Ctrl+D`/`q`: Exit
5. Setting editors:
   - **Text/Numeric**: `InputDialog` — type value, `Enter` confirms, `Esc` cancels
   - **Enum/Boolean**: `SelectionDialog` — `↑`/`↓` navigate, `Enter` selects, `Esc` cancels
   - **Hotkey**: `HotkeyCapture` (pynput listener thread, 30s timeout, `Esc` cancels)
   - **Reset**: `ConfirmDialog` — `←`/`→` navigate, `Enter` confirms, `Esc` cancels
6. On save: `SettingsService.set()` → validation → persist → `_refresh()` rebuilds menu
7. On error: Dialog shows error, buffer cleared for retry
8. Exit: Prints "Goodbye!"

---

## 5. Components That Can Be Safely Reused

| Component | Location | Purpose |
|-----------|----------|---------|
| `SettingsService` | `application/settings.py` | Core business logic: load, validate, save, reset |
| `AppConfig`, `UserPreferences` | `config/models.py`, `preferences/models.py` | Pydantic models with validation |
| `TomlConfigurationRepository`, `TomlPreferencesRepository` | `infrastructure/config_storage/toml.py`, `infrastructure/preferences/toml.py` | TOML persistence with atomic writes |
| `Key`, `KeyEvent`, `parse_key`, `raw_mode`, `read_key`, `flush_stdin` | `infrastructure/terminal/keyboard.py` | Synchronous, blocking keyboard input (cross-platform) |
| `HotkeyCapture` | `infrastructure/terminal/hotkey_capture.py` | Global hotkey capture via pynput |
| `SettingsMenu`, `MenuItem`, `InputDialog`, `SelectionDialog`, `ConfirmDialog` | `infrastructure/terminal/ui.py` | Terminal UI components (render + key handling) |
| `SETTABLE_KEYS`, `CONFIG_KEYS`, `PREFERENCE_KEYS` | `application/settings.py` | Key registries |

---

## 6. Components That Should Be Replaced / Refactored

| Component | Issue | Recommendation |
|-----------|-------|----------------|
| `InteractiveConfigEditor` | Monolithic (361 lines), mixes control flow, rendering, and persistence logic. Hard to test individual states in isolation. | Replace with a **state-machine-based controller** with explicit states (`MENU`, `EDIT_TEXT`, `EDIT_NUMBER`, `SELECT_OPTION`, `CAPTURE_HOTKEY`, `CONFIRM_RESET`, `EXIT`). Separate **controller** from **view** (UI components). |
| `_prompt_text`, `_prompt_selection`, `_prompt_hotkey`, `_confirm_reset` | Each duplicates rendering loop + key handling + save logic. | Unify into a generic **interaction handler** per state. |
| `_render_menu`, `_render_edit_header` | Direct `console.print()` calls scattered. | Centralize rendering; make controller testable without real console. |
| `read_key_fn` injection | Only the key reader is injectable; menu/dialogs use real `Console`. | Make **entire UI injectable** (provide a `Renderer` protocol) for full unit testability. |
| Error handling in `_save` | Sets `dialog.error` but clears buffer, forcing re-entry. | Preserve user input on validation error; show error inline. |
| Section header navigation | `move_up`/`move_down` skip headers via `while` loops. | Model menu as flat list of **selectable items only**; render headers separately. |

---

## 7. Identified Bugs / Reliability Concerns

1. **Enter key in InputDialog**: Reported bug where pressing Enter doesn't confirm. Current code handles both `\r` (macOS) and `\n` (Linux) via `parse_key`, but the synchronous reader may have edge cases with escape sequence timeouts or terminal encoding.
2. **Escape sequence timeout** (`_ESCAPE_SEQUENCE_TIMEOUT = 0.05s`): May be too short for high-latency SSH connections, causing bare `Esc` to be misidentified as start of arrow sequence.
3. **UTF-8 continuation timeout** (`_UTF8_CONTINUATION_TIMEOUT = 0.05s`): Same concern for multi-byte characters.
4. **Hotkey capture thread**: Bypasses synchronous reader; `flush_stdin()` called after, but race conditions possible.
5. **InputDialog cursor rendering**: Uses `▌` with background color; may not render correctly on all terminals.
6. **No explicit state machine**: Control flow implicit in call stack; harder to reason about and test.

---

## 8. Test Coverage Summary

| Test File | Coverage |
|-----------|----------|
| `test_cli_config.py` | CLI entry point, non-interactive mode, error handling, TTY fallback |
| `test_config_ui.py` | **58 tests** — Menu navigation, dialogs, editor integration (scripted keys), exit flows, reset, hotkey capture |
| `test_config_pty.py` | **2 tests** — Real PTY integration: arrow keys, macOS Return (`\r`) |
| `test_keyboard.py` | Key parsing, raw mode, Windows/Unix readers |

**All 179 tests pass.**

---

## 9. Dependency Boundaries (What NOT to Touch)

| Layer | Modules | Status |
|-------|---------|--------|
| CLI Registration | `cli/app.py`, `cli/commands/config.py` | Keep; only update `config.py` to use new controller |
| Settings Business Logic | `application/settings.py`, `config/models.py`, `preferences/models.py` | **Frozen** — reuse entirely |
| Persistence | `infrastructure/config_storage/toml.py`, `infrastructure/preferences/toml.py` | **Frozen** |
| Keyboard Infrastructure | `infrastructure/terminal/keyboard.py`, `hotkey_capture.py` | **Frozen** — reuse; only replace if proven unreliable |
| UI Components | `infrastructure/terminal/ui.py` | **Refactor** — extract rendering protocols, keep key handling |
| Credentials / IMAP / OTP / Providers | `infrastructure/credentials/`, `providers/`, `domain/` | **Out of scope** |

---

## 10. Phase 2 Design Goals

1. **Explicit State Machine**: `ConfigController` with states `MENU`, `EDIT_TEXT`, `EDIT_NUMBER`, `SELECT_OPTION`, `CAPTURE_HOTKEY`, `CONFIRM_RESET`, `EXIT`.
2. **Deterministic Transitions**: Each state handles input → returns next state + optional action.
3. **Testable Controller**: Inject `KeyReader`, `Renderer`, `SettingsService`, `HotkeyCapturer`. No direct `Console` or `raw_mode` in controller.
4. **Preserve User Input on Error**: Don't clear buffer on validation failure.
5. **Unified Interaction Loop**: Single `run()` loop dispatching to current state handler.
6. **Clean Separation**: Controller knows *what* to do; Renderer knows *how* to draw.
7. **Non-Interactive Mode**: Unchanged (already clean).