"""Redesigned interactive configuration controller with explicit state machine.

This module replaces the monolithic InteractiveConfigEditor with a clean
state-machine architecture:

    ConfigController
    ├── State: MENU, EDIT_TEXT, EDIT_NUMBER, SELECT_OPTION, CAPTURE_HOTKEY,
    │          CONFIRM_RESET, EXIT
    ├── KeyReader (injectable) — synchronous key events
    ├── Renderer (injectable) — terminal drawing
    ├── SettingsService — persistence & validation (reused)
    └── HotkeyCapturer (injectable) — global hotkey capture (reused)

All business logic, validation, and persistence remain in SettingsService.
UI components (SettingsMenu, InputDialog, etc.) are reused via Renderer.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol

from rich.console import Console

from otpilot.application.settings import SETTABLE_KEYS, SettingsService, SettingsSnapshot
from otpilot.domain.errors import OTPilotError
from otpilot.infrastructure.terminal.hotkey_capture import HotkeyCapture
from otpilot.infrastructure.terminal.keyboard import Key, KeyEvent, flush_stdin, raw_mode, read_key
from otpilot.infrastructure.terminal.ui import (
    ConfirmDialog,
    InputDialog,
    MenuItem,
    SelectionDialog,
    SettingsMenu,
)

# ----------------------------------------------------------------------
# Protocols for dependency injection (testability)


class KeyReader(Protocol):
    """Synchronous keyboard event reader."""

    def __call__(self) -> KeyEvent: ...


class Renderer(Protocol):
    """Terminal rendering interface."""

    def clear(self) -> None: ...
    def print(self, *objects: Any, **kwargs: Any) -> None: ...
    def get_width(self) -> int: ...


class HotkeyCapturer(Protocol):
    """Global hotkey capture interface."""

    def capture(self, timeout: float = 30.0) -> str | None: ...


class SettingsProvider(Protocol):
    """Settings persistence interface (subset of SettingsService)."""

    def snapshot(self) -> SettingsSnapshot: ...
    def set(self, key: str, value: str) -> Any: ...
    def reset(self) -> None: ...


# ----------------------------------------------------------------------
# State machine


class State(Enum):
    """Explicit interaction states."""

    MENU = "menu"
    EDIT_TEXT = "edit_text"
    EDIT_NUMBER = "edit_number"
    SELECT_OPTION = "select_option"
    CAPTURE_HOTKEY = "capture_hotkey"
    CONFIRM_RESET = "confirm_reset"
    EXIT = "exit"


@dataclass(frozen=True, slots=True)
class Transition:
    """Result of a state handler: next state + optional side-effect data."""

    next_state: State
    action: str | None = None  # e.g., "save", "cancel", "refresh"
    payload: Any = None  # e.g., key/value for save, error message


# ----------------------------------------------------------------------
# Configuration metadata


@dataclass(frozen=True, slots=True)
class SettingMeta:
    """Metadata for a settable configuration key."""

    key: str
    label: str
    description: str
    input_type: str  # "text", "number", "selection", "hotkey", "boolean"
    options: list[tuple[str, str]] | None = None  # for selection/boolean
    current_value: str = ""
    section: str | None = None


# Section ordering and metadata
SECTION_ORDER = [
    "provider",
    "credential_backend",
    "watch",
    "hotkeys",
    "preferences",
]

SECTION_TITLES = {
    "provider": "Provider",
    "credential_backend": "Credential Backend",
    "watch": "Watch",
    "hotkeys": "Hotkeys",
    "preferences": "Preferences",
}

SECTION_DESCRIPTIONS = {
    "provider": "Email provider configuration",
    "credential_backend": "Credential storage backend",
    "watch": "Watch mode settings",
    "hotkeys": "Global hotkey configuration",
    "preferences": "User interface preferences",
}

SETTING_METADATA: dict[str, SettingMeta] = {
    "provider.provider_id": SettingMeta(
        key="provider.provider_id",
        label="Provider ID",
        description="Active email provider (currently only 'gmail')",
        input_type="selection",
        options=[("gmail", "Gmail")],
        section="provider",
    ),
    "provider.account": SettingMeta(
        key="provider.account",
        label="Account",
        description="Email account for OTP fetching",
        input_type="text",
        section="provider",
    ),
    "credential_backend.backend": SettingMeta(
        key="credential_backend.backend",
        label="Backend",
        description="Credential storage backend (currently only 'keyring')",
        input_type="selection",
        options=[("keyring", "System Keyring")],
        section="credential_backend",
    ),
    "poll_interval_seconds": SettingMeta(
        key="poll_interval_seconds",
        label="Poll Interval",
        description="Polling interval in seconds (1-3600)",
        input_type="number",
        section="watch",
    ),
    "hotkey": SettingMeta(
        key="hotkey",
        label="Hotkey",
        description="Global hotkey combination (press to capture)",
        input_type="hotkey",
        section="hotkeys",
    ),
    "preferences.theme": SettingMeta(
        key="preferences.theme",
        label="Theme",
        description="UI theme: system, light, or dark",
        input_type="selection",
        options=[("system", "System"), ("light", "Light"), ("dark", "Dark")],
        section="preferences",
    ),
    "preferences.notifications_enabled": SettingMeta(
        key="preferences.notifications_enabled",
        label="Notifications",
        description="Enable desktop notifications",
        input_type="boolean",
        options=[("true", "Enabled"), ("false", "Disabled")],
        section="preferences",
    ),
    "preferences.auto_paste_enabled": SettingMeta(
        key="preferences.auto_paste_enabled",
        label="Auto Paste",
        description="Auto-paste OTP after copying",
        input_type="boolean",
        options=[("true", "Enabled"), ("false", "Disabled")],
        section="preferences",
    ),
}

# Action items (not settings)
RESET_ACTION_KEY = "__action__reset"
EXIT_ACTION_KEY = "__action__exit"

ACTION_ITEMS = [
    MenuItem(
        key=RESET_ACTION_KEY,
        label="Reset to Defaults",
        description="Reset all settings and preferences to their default values",
        current_value="",
        item_type="action",
    ),
    MenuItem(
        key=EXIT_ACTION_KEY,
        label="Exit",
        description="Leave the configuration editor without saving",
        current_value="",
        item_type="action",
    ),
]

MENU_HINT = "↑/↓ Navigate • Enter Select • Esc Exit"


# ----------------------------------------------------------------------
# Renderer implementation (wraps Rich Console)


class RichRenderer:
    """Renderer using Rich Console. Used in production."""

    def __init__(self, console: Console) -> None:
        self.console = console

    def clear(self) -> None:
        self.console.clear()

    def print(self, *objects: Any, **kwargs: Any) -> None:
        self.console.print(*objects, **kwargs)

    def get_width(self) -> int:
        return self.console.width


# ----------------------------------------------------------------------
# ConfigController — the state machine


class ConfigController:
    """State-machine-driven interactive configuration editor.

    The controller owns:
    - Current state (State enum)
    - Settings snapshot (refreshed after each save)
    - Menu selection index
    - Active dialog (InputDialog, SelectionDialog, ConfirmDialog)
    - Error message for current interaction

    All I/O dependencies are injected for testability.
    """

    def __init__(
        self,
        service: SettingsProvider,
        renderer: Renderer,
        key_reader: KeyReader,
        hotkey_capturer: HotkeyCapturer,
    ) -> None:
        self.service = service
        self.renderer = renderer
        self.read_key = key_reader
        self.hotkey_capturer = hotkey_capturer

        # State
        self.state = State.MENU
        self.snapshot: SettingsSnapshot | None = None
        self.menu = SettingsMenu(renderer.console if hasattr(renderer, "console") else Console())
        self.menu_index = 0

        # Dialogs (created lazily)
        self._input_dialog: InputDialog | None = None
        self._selection_dialog: SelectionDialog | None = None
        self._confirm_dialog: ConfirmDialog | None = None

        # Current editing context
        self._editing_key: str | None = None
        self._editing_meta: SettingMeta | None = None
        self._error: str | None = None

    # ------------------------------------------------------------------
    # Public entry point

    def run(self) -> None:
        """Run the interactive editor until EXIT state."""
        try:
            with raw_mode():
                self._load_snapshot()
                self._build_menu()
                self._main_loop()
        except KeyboardInterrupt:
            pass  # Graceful Ctrl+C
        finally:
            self.renderer.print("\n[dim]Goodbye![/dim]")

    # ------------------------------------------------------------------
    # Main loop

    def _main_loop(self) -> None:
        while self.state != State.EXIT:
            self._render_current_state()
            event = self.read_key()
            transition = self._handle_event(event)
            self._apply_transition(transition)

    def _handle_event(self, event: KeyEvent) -> Transition:
        """Dispatch event to current state handler."""
        if self.state == State.MENU:
            return self._handle_menu_event(event)
        elif self.state == State.EDIT_TEXT:
            return self._handle_edit_text_event(event)
        elif self.state == State.EDIT_NUMBER:
            return self._handle_edit_number_event(event)
        elif self.state == State.SELECT_OPTION:
            return self._handle_select_option_event(event)
        elif self.state == State.CAPTURE_HOTKEY:
            return self._handle_capture_hotkey_event(event)
        elif self.state == State.CONFIRM_RESET:
            return self._handle_confirm_reset_event(event)
        return Transition(State.EXIT)

    def _apply_transition(self, transition: Transition) -> None:
        """Apply state transition and side effects."""
        previous_state = self.state
        self.state = transition.next_state

        # Run entry actions for the new state
        if self.state == State.CAPTURE_HOTKEY and previous_state != State.CAPTURE_HOTKEY:
            self._do_capture_hotkey()
            # After capture completes, transition back to menu with refresh
            self._load_snapshot()
            self._build_menu()
            self.state = State.MENU
            return

        if transition.action == "save":
            success = self._do_save(transition.payload)
            if success:
                # On success: go back to menu and refresh
                self._reset_edit_context()
                self._load_snapshot()
                self._build_menu()
                self.state = State.MENU
            # On failure: stay in current edit state (already set), error shown
        elif transition.action == "cancel_edit":
            self._reset_edit_context()
            self.state = State.MENU
        elif transition.action == "refresh":
            self._load_snapshot()
            self._build_menu()
        elif transition.action == "reset_confirmed":
            self._do_reset()
            self._load_snapshot()
            self._build_menu()
        elif transition.action == "exit_editor":
            self.state = State.EXIT

    # ------------------------------------------------------------------
    # Snapshot & menu

    def _load_snapshot(self) -> None:
        try:
            self.snapshot = self.service.snapshot()
        except OTPilotError as exc:
            self.renderer.print(f"\n[red]Error loading settings:[/red] {exc}")
            self.renderer.print("[dim]Press any key to exit…[/dim]")
            self.read_key()
            self.state = State.EXIT

    def _build_menu(self) -> None:
        """Build menu items from snapshot, preserving selection where possible."""
        if not self.snapshot:
            return

        # Build flat list of selectable items (no section headers in selection)
        selectable_items: list[MenuItem] = []

        for section in SECTION_ORDER:
            # Add section header to menu for rendering
            pass  # SettingsMenu handles sections internally

        self.menu.build_items(self.snapshot, set(SETTABLE_KEYS))

        # Preserve selection index if possible
        if self.menu_index >= len(self.menu.items):
            self.menu_index = self._first_selectable_index()
        else:
            # Ensure we're on a selectable item
            while self.menu_index < len(self.menu.items) and self.menu.items[self.menu_index].item_type == "section":
                self.menu_index += 1
            if self.menu_index >= len(self.menu.items):
                self.menu_index = self._first_selectable_index()

        self.menu.selected_index = self.menu_index

    def _first_selectable_index(self) -> int:
        for i, item in enumerate(self.menu.items):
            if item.item_type != "section":
                return i
        return 0

    def _get_selected_item(self) -> MenuItem | None:
        item = self.menu.get_selected()
        if item and item.item_type != "section":
            return item
        return None

    # ------------------------------------------------------------------
    # Rendering

    def _render_current_state(self) -> None:
        if self.state == State.MENU:
            self._render_menu()
        elif self.state in (State.EDIT_TEXT, State.EDIT_NUMBER):
            self._render_edit_dialog()
        elif self.state == State.SELECT_OPTION:
            self._render_selection_dialog()
        elif self.state == State.CAPTURE_HOTKEY:
            self._render_hotkey_capture()
        elif self.state == State.CONFIRM_RESET:
            self._render_confirm_reset()

    def _render_menu(self) -> None:
        self.renderer.clear()
        self.renderer.print("[bold]OTPilot Settings[/bold]")
        self.renderer.print("─────────────────────────────────────────────\n")
        self.renderer.print(self.menu.render())
        self.renderer.print(f"\n{MENU_HINT}")

    def _render_edit_dialog(self) -> None:
        if not self._input_dialog or not self._editing_meta:
            return
        self.renderer.clear()
        self.renderer.print(f"[bold]Edit {self._editing_meta.label}[/bold]")
        self.renderer.print("─────────────────────────────────────────────\n")
        current_val = self._editing_meta.current_value or "(empty)"
        self.renderer.print(
            self._input_dialog.render(
                title=f"Edit {self._editing_meta.label}",
                prompt=f"Enter new value for {self._editing_key}",
                current_value=current_val,
            )
        )

    def _render_selection_dialog(self) -> None:
        if not self._selection_dialog or not self._editing_meta:
            return
        self.renderer.clear()
        self.renderer.print(f"[bold]Edit {self._editing_meta.label}[/bold]")
        self.renderer.print("─────────────────────────────────────────────\n")
        self.renderer.print(
            self._selection_dialog.render(
                title=f"Select {self._editing_meta.label}",
                prompt=f"Choose a value for {self._editing_key}",
                options=self._selection_dialog.options,
                current_value=self._editing_meta.current_value,
            )
        )

    def _render_hotkey_capture(self) -> None:
        if not self._editing_meta:
            return
        self.renderer.clear()
        from rich.panel import Panel
        from rich.style import Style
        from rich.text import Text

        content = Text()
        content.append(f"Current hotkey: {self._editing_meta.current_value}\n\n", Style(dim=True))
        content.append("Press the desired key combination...\n\n", Style(bold=True))
        content.append("Press keys to capture • Esc to cancel", Style(dim=True))
        self.renderer.print(Panel(content, title="Capture Hotkey", border_style="blue", padding=(1, 2)))

    def _render_confirm_reset(self) -> None:
        if not self._confirm_dialog:
            return
        self.renderer.clear()
        self.renderer.print(
            self._confirm_dialog.render(
                title="Confirm Reset",
                message=(
                    "Reset all configuration and preferences to defaults?\n"
                    "Stored credentials will not be removed."
                ),
            )
        )

    # ------------------------------------------------------------------
    # State handlers

    def _handle_menu_event(self, event: KeyEvent) -> Transition:
        if event.key == Key.UP:
            self.menu.move_up()
            self.menu_index = self.menu.selected_index
            return Transition(State.MENU)
        elif event.key == Key.DOWN:
            self.menu.move_down()
            self.menu_index = self.menu.selected_index
            return Transition(State.MENU)
        elif event.key == Key.ENTER:
            item = self._get_selected_item()
            if not item:
                return Transition(State.MENU)
            if item.key == EXIT_ACTION_KEY:
                return Transition(State.EXIT, action="exit_editor")
            if item.key == RESET_ACTION_KEY:
                self._confirm_dialog = ConfirmDialog(self.renderer.console if hasattr(self.renderer, "console") else Console())
                return Transition(State.CONFIRM_RESET)
            return self._enter_edit_state(item)
        elif event.key in (Key.ESCAPE, Key.CTRL_C, Key.CTRL_D):
            return Transition(State.EXIT, action="exit_editor")
        elif event.key == Key.CHAR and event.char and event.char.lower() == "q":
            return Transition(State.EXIT, action="exit_editor")
        return Transition(State.MENU)

    def _enter_edit_state(self, item: MenuItem) -> Transition:
        """Transition to appropriate edit state based on setting type."""
        self._editing_key = item.key
        meta = SETTING_METADATA.get(item.key)
        if not meta:
            return Transition(State.MENU)

        # Update meta with current value from snapshot
        current_entry = self.snapshot.entry(item.key) if self.snapshot else None
        current_display = current_entry.display_value() if current_entry else ""
        self._editing_meta = SettingMeta(
            key=meta.key,
            label=meta.label,
            description=meta.description,
            input_type=meta.input_type,
            options=meta.options,
            current_value=current_display,
            section=meta.section,
        )

        if meta.input_type == "hotkey":
            return Transition(State.CAPTURE_HOTKEY)
        elif meta.input_type in ("selection", "boolean"):
            self._selection_dialog = SelectionDialog(self.renderer.console if hasattr(self.renderer, "console") else Console())
            current = None if current_display in ("", "<unset>") else current_display.lower()
            self._selection_dialog.set_options(meta.options or [], current=current)
            return Transition(State.SELECT_OPTION)
        elif meta.input_type == "number":
            self._input_dialog = InputDialog(self.renderer.console if hasattr(self.renderer, "console") else Console())
            return Transition(State.EDIT_NUMBER)
        else:  # text
            self._input_dialog = InputDialog(self.renderer.console if hasattr(self.renderer, "console") else Console())
            return Transition(State.EDIT_TEXT)

    def _handle_edit_text_event(self, event: KeyEvent) -> Transition:
        if not self._input_dialog:
            return Transition(State.MENU)

        if event.key in (Key.CTRL_C, Key.CTRL_D):
            return Transition(State.MENU, action="cancel_edit")

        result = self._input_dialog.handle_key(event)
        if result == "CANCEL":
            return Transition(State.MENU, action="cancel_edit")
        if result is None:
            return Transition(State.EDIT_TEXT)  # Continue editing
        if result is not None:
            # User pressed Enter - validate and save
            return Transition(State.EDIT_TEXT, action="save", payload=(self._editing_key, result))
        return Transition(State.EDIT_TEXT)

    def _handle_edit_number_event(self, event: KeyEvent) -> Transition:
        # Same as text but could add numeric-only filtering if desired
        return self._handle_edit_text_event(event)

    def _handle_select_option_event(self, event: KeyEvent) -> Transition:
        if not self._selection_dialog:
            return Transition(State.MENU)

        if event.key in (Key.CTRL_C, Key.CTRL_D):
            return Transition(State.MENU, action="cancel_edit")

        result = self._selection_dialog.handle_key(event)
        if result == "CANCEL":
            return Transition(State.MENU, action="cancel_edit")
        if result is None:
            return Transition(State.SELECT_OPTION)  # Navigation
        if result is not None:
            return Transition(State.SELECT_OPTION, action="save", payload=(self._editing_key, result))
        return Transition(State.SELECT_OPTION)

    def _handle_capture_hotkey_event(self, event: KeyEvent) -> Transition:
        # This should not be called anymore since capture runs on state entry.
        # If somehow we're here, just return to menu.
        return Transition(State.MENU, action="refresh")

    def _do_capture_hotkey(self) -> None:
        """Run hotkey capture (blocking) and save if successful."""
        if not self._editing_key:
            return
        try:
            captured = self.hotkey_capturer.capture(timeout=30.0)
        except KeyboardInterrupt:
            raise
        except OTPilotError as exc:
            self._show_error(str(exc))
            return
        except Exception as exc:
            self._show_error(f"Hotkey capture failed: {exc}")
            return
        finally:
            flush_stdin()

        if not captured:
            self.renderer.print("[yellow]No hotkey captured. Returning to menu.[/yellow]")
            self.renderer.print("[dim]Press any key to continue…[/dim]")
            self.read_key()
            return

        try:
            self.service.set(self._editing_key, captured)
        except OTPilotError as exc:
            self._show_error(str(exc))

    def _handle_confirm_reset_event(self, event: KeyEvent) -> Transition:
        if not self._confirm_dialog:
            return Transition(State.MENU)

        if event.key in (Key.CTRL_C, Key.CTRL_D):
            return Transition(State.MENU, action="cancel_edit")

        result = self._confirm_dialog.handle_key(event)
        if result is None:
            if event.key == Key.ESCAPE:
                return Transition(State.MENU, action="cancel_edit")
            return Transition(State.CONFIRM_RESET)  # Navigation
        if result is True:
            return Transition(State.MENU, action="reset_confirmed")
        return Transition(State.MENU, action="cancel_edit")

    # ------------------------------------------------------------------
    # Persistence actions

    def _do_save(self, payload: tuple[str, str]) -> bool:
        """Save a value. Returns True on success, False on validation error."""
        key, value = payload
        try:
            self.service.set(key, value)
        except OTPilotError as exc:
            # Set error on active dialog for inline display (non-blocking)
            if self._input_dialog:
                self._input_dialog.error = str(exc)
                self._input_dialog.buffer = ""
                self._input_dialog.cursor_pos = 0
            if self._selection_dialog:
                self._selection_dialog.error = str(exc)
            return False
        return True

    def _do_reset(self) -> None:
        try:
            self.service.reset()
        except OTPilotError as exc:
            self._show_error(str(exc))

    def _reset_edit_context(self) -> None:
        self._editing_key = None
        self._editing_meta = None
        self._input_dialog = None
        self._selection_dialog = None
        self._error = None

    def _show_error(self, message: str) -> None:
        self.renderer.print(f"\n[red]Error:[/red] {message}")
        self.renderer.print("[dim]Press any key to continue…[/dim]")
        self.read_key()


# ----------------------------------------------------------------------
# Non-interactive mode (unchanged)


def run_non_interactive(console: Console) -> None:
    """Display the current configuration without interactive editing."""
    from otpilot.infrastructure.config_storage.toml import TomlConfigurationRepository
    from otpilot.infrastructure.preferences.toml import TomlPreferencesRepository

    service = SettingsService(
        config=TomlConfigurationRepository(),
        preferences=TomlPreferencesRepository(),
    )
    snapshot = service.snapshot()
    menu = SettingsMenu(console)
    menu.build_items(snapshot, set(SETTABLE_KEYS))
    console.print("[bold]OTPilot Settings[/bold]")
    console.print("─────────────────────────────────────────────\n")
    console.print(menu.render())
    console.print(
        "\n[dim]Running in non-interactive mode. Use a real terminal for interactive editing.[/dim]"
    )


# ----------------------------------------------------------------------
# Factory for production use


def build_settings_service() -> SettingsService:
    """Build the settings service from the platform repositories."""
    from otpilot.infrastructure.config_storage.toml import TomlConfigurationRepository
    from otpilot.infrastructure.preferences.toml import TomlPreferencesRepository

    return SettingsService(
        config=TomlConfigurationRepository(),
        preferences=TomlPreferencesRepository(),
    )


def create_controller(
    console: Console | None = None,
    service: SettingsService | None = None,
    key_reader: KeyReader | None = None,
    hotkey_capturer: HotkeyCapturer | None = None,
) -> ConfigController:
    """Create a ConfigController with production defaults."""
    console = console or Console()
    service = service or build_settings_service()
    key_reader = key_reader or read_key
    hotkey_capturer = hotkey_capturer or HotkeyCapture()
    renderer = RichRenderer(console)
    return ConfigController(service, renderer, key_reader, hotkey_capturer)