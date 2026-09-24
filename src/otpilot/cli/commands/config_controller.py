"""Configuration controller for the interactive `otpilot config` command.

This module implements a lightweight state machine that drives the
interactive configuration UI.  It re‑uses the existing services and UI
components but removes the tight coupling that existed in the original
implementation.  The controller is intentionally small and testable –
each state transition is a pure function of the current state and the
incoming key event.

The public API is a single :class:`ConfigController` class with two
methods:

``run_interactive(console: Console)`` – start the interactive loop.
``run_non_interactive(console: Console)`` – display the current
configuration and exit.

The controller keeps a reference to a :class:`SettingsService` instance
and a :class:`SettingsMenu` for rendering.  All UI rendering is
delegated to the existing Rich‑based components in
``otpilot.infrastructure.terminal.ui``.

The state machine is defined by the ``State`` enum below.  Each state
has a dedicated handler that updates the controller's internal
state.  The handlers are intentionally small and return a boolean
indicating whether the loop should continue.

This file is deliberately self‑contained – it does not import the
``config`` command module directly.  The command module simply
instantiates the controller and delegates to it.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

import typer
from rich.console import Console

from otpilot.application.settings import SettingsService, SettingsSnapshot, SETTABLE_KEYS, _parse_value
# Option and validator mappings originally defined in the old config command.
# They are duplicated here to keep the controller self‑contained.
_SETTING_OPTIONS: dict[str, list[tuple[str, str]]] = {
    "provider.provider_id": [("gmail", "Gmail")],
    "credential_backend.backend": [("keyring", "System Keyring")],
    "preferences.theme": [("system", "System"), ("light", "Light"), ("dark", "Dark")],
    "preferences.notifications_enabled": [("true", "Enabled"), ("false", "Disabled")],
    "preferences.auto_paste_enabled": [("true", "Enabled"), ("false", "Disabled")],
}

_SETTING_VALIDATORS: dict[str, Any] = {
    "poll_interval_seconds": lambda v: 0 < v <= 3600,
}
from otpilot.domain.errors import ConfigurationError, OTPilotError, PreferenceError
from otpilot.infrastructure.config_storage.toml import TomlConfigurationRepository
from otpilot.infrastructure.preferences.toml import TomlPreferencesRepository
from otpilot.infrastructure.terminal.hotkey_capture import HotkeyCapture
from otpilot.infrastructure.terminal.keyboard import Key, KeyEvent
from otpilot.infrastructure.terminal.keyboard_sync import read_key
from otpilot.infrastructure.terminal.ui import (
    ConfirmDialog,
    HotkeyCaptureDialog,
    InputDialog,
    SelectionDialog,
    SettingsMenu,
)


class State(Enum):
    MENU = "menu"
    INPUT = "input"
    SELECTION = "selection"
    HOTKEY = "hotkey"
    CONFIRM = "confirm"
    EXIT = "exit"


@dataclass
class ConfigUIState:
    console: Console
    service: SettingsService
    menu: SettingsMenu
    # No keyboard handler in synchronous mode
    snapshot: SettingsSnapshot | None = None
    current_state: State = State.MENU
    selected_item: Any = None
    input_dialog: InputDialog | None = None
    selection_dialog: SelectionDialog | None = None
    hotkey_dialog: HotkeyCaptureDialog | None = None
    confirm_dialog: ConfirmDialog | None = None
    dirty: bool = True
    interactive: bool = True


def build_settings_service() -> SettingsService:
    return SettingsService(
        config=TomlConfigurationRepository(),
        preferences=TomlPreferencesRepository(),
    )


def _refresh_snapshot(state: ConfigUIState) -> None:
    state.snapshot = state.service.snapshot()
    state.menu.build_items(state.snapshot, set(SETTABLE_KEYS))
    state.dirty = True


def _render(state: ConfigUIState) -> None:
    if state.current_state == State.MENU:
        _render_menu(state)
    elif state.current_state == State.INPUT:
        _render_input(state)
    elif state.current_state == State.SELECTION:
        _render_selection(state)
    elif state.current_state == State.HOTKEY:
        _render_hotkey(state)
    elif state.current_state == State.CONFIRM:
        _render_confirm(state)


def _render_menu(state: ConfigUIState) -> None:
    state.console.clear()
    state.console.print("[bold]OTPilot Settings[/bold]")
    state.console.print("─────────────────────────────────────────────\n")
    state.console.print(state.menu.render())
    state.console.print("\n↑/↓ to navigate • Enter to select • Esc to exit")


def _render_input(state: ConfigUIState) -> None:
    if not state.input_dialog or not state.selected_item:
        return
    state.console.clear()
    item = state.selected_item
    state.console.print(
        state.input_dialog.render(
            title=f"Edit {item.label}",
            prompt=f"Enter new value for {item.key}",
            current_value=item.current_value,
        )
    )


def _render_selection(state: ConfigUIState) -> None:
    if not state.selection_dialog or not state.selected_item:
        return
    state.console.clear()
    item = state.selected_item
    state.console.print(
        state.selection_dialog.render(
            title=f"Select {item.label}",
            prompt=f"Choose a value for {item.key}",
            options=state.selection_dialog.options,
            current_value=item.current_value,
        )
    )


def _render_hotkey(state: ConfigUIState) -> None:
    if not state.hotkey_dialog or not state.selected_item:
        return
    state.console.clear()
    item = state.selected_item
    state.console.print(
        state.hotkey_dialog.render(
            title="Capture Hotkey",
            current_hotkey=item.current_value,
        )
    )


def _render_confirm(state: ConfigUIState) -> None:
    if not state.confirm_dialog:
        return
    state.console.clear()
    state.console.print(
        state.confirm_dialog.render(
            title="Confirm Reset",
            message="Reset all configuration and preferences to defaults?\nStored credentials will not be removed.",
        )
    )


def _handle_menu(state: ConfigUIState, event: KeyEvent) -> None:
    if event.key == Key.UP:
        state.menu.move_up()
        state.dirty = True
    elif event.key == Key.DOWN:
        state.menu.move_down()
        state.dirty = True
    elif event.key == Key.ENTER:
        item = state.menu.get_selected()
        if item:
            _enter_setting(state, item)
    elif event.key == Key.ESCAPE:
        state.current_state = State.EXIT
    elif event.key == Key.CHAR and event.char and event.char.lower() == "q":
        state.current_state = State.EXIT


def _enter_setting(state: ConfigUIState, item: Any) -> None:
    state.selected_item = item
    key = item.key
    if key == "__action__reset":
        state.current_state = State.CONFIRM
        state.confirm_dialog = ConfirmDialog(state.console)
        state.dirty = True
        return
    if key == "hotkey":
        state.current_state = State.HOTKEY
        state.hotkey_dialog = HotkeyCaptureDialog(state.console)
        # Render the dialog
        if state.dirty:
            _render(state)
            state.dirty = False
        # Blocking capture
        result = HotkeyCapture().capture(timeout=30.0)
        if result:
            try:
                state.service.set("hotkey", result)
            except (ConfigurationError, PreferenceError):
                pass
        # Reset state
        state.current_state = State.MENU
        state.hotkey_dialog = None
        state.selected_item = None
        _refresh_snapshot(state)
        return
    options = _SETTING_OPTIONS.get(key)
    if options:
        state.current_state = State.SELECTION
        state.selection_dialog = SelectionDialog(state.console)
        state.selection_dialog.set_options(options)
        state.dirty = True
        return
    # Text/numeric input – prepopulate with current value
    state.current_state = State.INPUT
    state.input_dialog = InputDialog(state.console)
    state.input_dialog.buffer = str(state.selected_item.current_value or "")
    state.input_dialog.cursor_pos = len(state.input_dialog.buffer)
    state.dirty = True


def _start_hotkey_capture(state: ConfigUIState) -> None:
    state.hotkey_dialog = HotkeyCaptureDialog(state.console)
    state.hotkey_capturer = HotkeyCapture()
    state.hotkey_capture_result = None
    def capture() -> None:
        result = state.hotkey_capturer.capture(timeout=30.0)
        state.hotkey_capture_result = result
        state.dirty = True
    state.hotkey_capture_thread = threading.Thread(target=capture, daemon=True)
    state.hotkey_capture_thread.start()


def _handle_input(state: ConfigUIState, event: KeyEvent) -> None:
    print(f"DEBUG: Received key: {event.key}", flush=True)

    if not state.input_dialog or not state.selected_item:
        state.current_state = State.MENU
        return
    result = state.input_dialog.handle_key(event)
    if result is None:
        return
    if result == "CANCEL":
        state.current_state = State.MENU
        state.input_dialog = None
        state.selected_item = None
        state.dirty = True
        return
    key = state.selected_item.key
    try:
        parsed = _parse_value(key, result)
        validator = _SETTING_VALIDATORS.get(key)
        if validator and not validator(parsed):
            raise ConfigurationError(f"Value out of range for {key}")
        state.service.set(key, result)
        state.current_state = State.MENU
        state.input_dialog = None
        state.selected_item = None
        _refresh_snapshot(state)
    except ConfigurationError as exc:
        # Reset buffer to allow re‑entry
        state.input_dialog.buffer = ""
        state.input_dialog.cursor_pos = 0
        state.dirty = True


def _handle_selection(state: ConfigUIState, event: KeyEvent) -> None:
    if not state.selection_dialog or not state.selected_item:
        state.current_state = State.MENU
        return
    result = state.selection_dialog.handle_key(event)
    if result is None:
        return
    if result == "CANCEL":
        state.current_state = State.MENU
        state.selection_dialog = None
        state.selected_item = None
        state.dirty = True
        return
    key = state.selected_item.key
    try:
        state.service.set(key, result)
        state.current_state = State.MENU
        state.selection_dialog = None
        state.selected_item = None
        _refresh_snapshot(state)
    except (ConfigurationError, PreferenceError) as exc:
        pass


def _handle_hotkey(state: ConfigUIState, event: KeyEvent) -> None:
    if not state.hotkey_dialog or not state.hotkey_capturer:
        state.current_state = State.MENU
        return
    if state.hotkey_capture_result is not None:
        if state.hotkey_capture_result:
            try:
                state.service.set("hotkey", state.hotkey_capture_result)
            except (ConfigurationError, PreferenceError):
                pass
        state.current_state = State.MENU
        state.hotkey_dialog = None
        state.hotkey_capturer = None
        state.hotkey_capture_thread = None
        state.hotkey_capture_result = None
        state.selected_item = None
        _refresh_snapshot(state)
        return
    if event.key == Key.ESCAPE:
        state.current_state = State.MENU
        state.hotkey_dialog = None
        state.hotkey_capturer = None
        state.hotkey_capture_thread = None
        state.hotkey_capture_result = None
        state.selected_item = None
        state.dirty = True


def _handle_confirm(state: ConfigUIState, event: KeyEvent) -> None:
    if not state.confirm_dialog:
        state.current_state = State.MENU
        return
    result = state.confirm_dialog.handle_key(event)
    if result is None:
        return
    if result:
        try:
            state.service.reset()
        except OTPilotError:
            pass
    state.current_state = State.MENU
    state.confirm_dialog = None
    state.selected_item = None
    _refresh_snapshot(state)


def _dispatch(state: ConfigUIState, event: KeyEvent) -> None:
    if state.current_state == State.MENU:
        _handle_menu(state, event)
    elif state.current_state == State.INPUT:
        _handle_input(state, event)
    elif state.current_state == State.SELECTION:
        _handle_selection(state, event)
    elif state.current_state == State.HOTKEY:
        _handle_hotkey(state, event)
    elif state.current_state == State.CONFIRM:
        _handle_confirm(state, event)


def run_interactive(console: Console) -> None:
    """Run the configuration editor synchronously.

    The function enters a loop that renders the current state and blocks on
    :func:`read_key` to receive the next key event.  The loop exits when the
    user presses *Esc* or *Ctrl+C*.
    """
    state = ConfigUIState(
        console=console,
        service=build_settings_service(),
        menu=SettingsMenu(console),
        keyboard=None,
    )
    _refresh_snapshot(state)
    try:
        while state.current_state != State.EXIT:
            if state.dirty:
                _render(state)
                state.dirty = False
            event = read_key()
            _dispatch(state, event)
    except KeyboardInterrupt:
        pass
    console.print("\n[yellow]Configuration saved. Goodbye![/yellow]")
    raise typer.Exit(code=0)


def run_non_interactive(state: ConfigUIState) -> None:
    _refresh_snapshot(state)
    state.console.print("[bold]OTPilot Settings[/bold]")
    state.console.print("─────────────────────────────────────────────\n")
    state.console.print(state.menu.render())
    state.console.print("\n[dim]Running in non-interactive mode. Use a real terminal for interactive editing.[/dim]")
    raise typer.Exit(code=0)
