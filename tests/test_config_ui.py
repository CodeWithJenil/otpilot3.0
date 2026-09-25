"""Tests for the interactive configuration UI components.

These tests cover the reusable UI components: SettingsMenu, InputDialog,
SelectionDialog, ConfirmDialog, and HotkeyCapture.  Editor integration tests
are in test_config_controller.py.
"""

import io
from collections import deque

import pytest
from rich.console import Console

from otpilot.application.settings import SettingsService, SETTABLE_KEYS
from otpilot.infrastructure.config_storage.toml import TomlConfigurationRepository
from otpilot.infrastructure.preferences.toml import TomlPreferencesRepository
from otpilot.infrastructure.terminal.keyboard import Key, KeyEvent, parse_key
from otpilot.infrastructure.terminal.hotkey_capture import HotkeyCapture
from otpilot.infrastructure.terminal.ui import (
    ConfirmDialog,
    InputDialog,
    MenuItem,
    SelectionDialog,
    SettingsMenu,
)

# ----------------------------------------------------------------------
# Helpers


def make_service(tmp_path) -> SettingsService:
    return SettingsService(
        config=TomlConfigurationRepository(tmp_path / "config.toml"),
        preferences=TomlPreferencesRepository(tmp_path / "preferences.toml"),
    )


def make_console() -> Console:
    return Console(
        file=io.StringIO(), width=100, force_terminal=False, highlight=False
    )


def char(c: str) -> KeyEvent:
    return KeyEvent(key=Key.CHAR, char=c)


def enter() -> KeyEvent:
    return KeyEvent(key=Key.ENTER)


def escape() -> KeyEvent:
    return KeyEvent(key=Key.ESCAPE)


def editor_menu_keys() -> set[str]:
    return set(SETTABLE_KEYS)


class ScriptedKeys:
    """A key reader that replays scripted raw input through the real parser."""

    def __init__(self, *keys: str) -> None:
        self._queue: deque[str] = deque()
        for key in keys:
            self._queue.extend(key)

    def __call__(self) -> KeyEvent:
        if not self._queue:
            return KeyEvent(key=Key.ESCAPE)
        first = self._queue.popleft()
        queue = self._queue

        def read_next() -> str | None:
            if not queue:
                return None
            return queue.popleft()

        event = parse_key(first, read_next)
        return event if event is not None else KeyEvent(key=Key.ESCAPE)


def down(n: int = 1) -> str:
    return "\x1b[B" * n


def up(n: int = 1) -> str:
    return "\x1b[A" * n


def right(n: int = 1) -> str:
    return "\x1b[C" * n


# ----------------------------------------------------------------------
# Menu tests


class TestSettingsMenu:
    def test_builds_items_from_snapshot(self, tmp_path) -> None:
        menu = SettingsMenu(make_console())
        menu.build_items(make_service(tmp_path).snapshot(), set(editor_menu_keys()))

        keys = [item.key for item in menu.items]
        assert keys == [
            "__section__provider",
            "provider.provider_id",
            "provider.account",
            "__section__credential_backend",
            "credential_backend.backend",
            "__section__watch",
            "poll_interval_seconds",
            "__section__hotkeys",
            "hotkey",
            "__section__preferences",
            "preferences.theme",
            "preferences.notifications_enabled",
            "preferences.auto_paste_enabled",
            "__action__reset",
            "__action__exit",
        ]

    def test_initial_selection_is_first_setting_not_header(self, tmp_path) -> None:
        menu = SettingsMenu(make_console())
        menu.build_items(make_service(tmp_path).snapshot(), set(editor_menu_keys()))

        assert menu.get_selected() is not None
        assert menu.get_selected().key == "provider.provider_id"

    def test_move_down_skips_section_headers(self, tmp_path) -> None:
        menu = SettingsMenu(make_console())
        menu.build_items(make_service(tmp_path).snapshot(), set(editor_menu_keys()))

        sequence = [item.key for item in menu.items]
        selectable = [k for k in sequence if not k.startswith("__section__")]
        visited = [menu.get_selected().key]
        for _ in range(len(selectable) - 1):
            menu.move_down()
            selected = menu.get_selected()
            assert selected is not None, "selection must never rest on a header"
            visited.append(selected.key)
        assert visited == selectable

    def test_move_up_skips_section_headers(self, tmp_path) -> None:
        menu = SettingsMenu(make_console())
        menu.build_items(make_service(tmp_path).snapshot(), set(editor_menu_keys()))

        for _ in range(20):
            menu.move_down()
        visited = []
        while True:
            selected = menu.get_selected()
            assert selected is not None
            visited.append(selected.key)
            before = menu.selected_index
            menu.move_up()
            if menu.selected_index == before:
                break
        expected = [
            "provider.provider_id",
            "provider.account",
            "credential_backend.backend",
            "poll_interval_seconds",
            "hotkey",
            "preferences.theme",
            "preferences.notifications_enabled",
            "preferences.auto_paste_enabled",
            "__action__reset",
            "__action__exit",
        ]
        assert list(reversed(visited)) == expected

    def test_navigation_bounds(self, tmp_path) -> None:
        menu = SettingsMenu(make_console())
        menu.build_items(make_service(tmp_path).snapshot(), set(editor_menu_keys()))

        first = menu.selected_index
        menu.move_up()
        assert menu.selected_index == first
        for _ in range(50):
            menu.move_down()
        last = menu.selected_index
        menu.move_down()
        assert menu.selected_index == last

    def test_empty_menu_is_handled(self) -> None:
        menu = SettingsMenu(make_console())
        menu.items = []
        menu.move_up()
        menu.move_down()
        assert menu.get_selected() is None

    def test_single_item_menu_is_handled(self) -> None:
        menu = SettingsMenu(make_console())
        menu.items = [
            MenuItem(
                key="poll_interval_seconds",
                label="Poll Interval",
                description="",
                current_value="30.0",
                item_type="setting",
            )
        ]
        menu.move_down()
        assert menu.get_selected() is not None
        menu.move_up()
        assert menu.get_selected() is not None

    def test_render_displays_current_values(self, tmp_path) -> None:
        console = make_console()
        menu = SettingsMenu(console)
        menu.build_items(make_service(tmp_path).snapshot(), set(editor_menu_keys()))
        console.print(menu.render())
        output = console.file.getvalue()
        assert "Poll Interval" in output
        assert "30.0" in output
        assert "system" in output


# ----------------------------------------------------------------------
# Dialog tests


class TestInputDialog:
    def test_typing_appends_at_cursor(self) -> None:
        dialog = InputDialog(make_console())
        for c in "abc":
            dialog.handle_key(char(c))
        assert dialog.buffer == "abc"
        assert dialog.cursor_pos == 3

    def test_cursor_movement(self) -> None:
        dialog = InputDialog(make_console())
        for c in "abc":
            dialog.handle_key(char(c))
        dialog.handle_key(KeyEvent(key=Key.LEFT))
        dialog.handle_key(char("X"))
        assert dialog.buffer == "abXc"
        dialog.handle_key(KeyEvent(key=Key.RIGHT))
        dialog.handle_key(char("Y"))
        assert dialog.buffer == "abXcY"

    def test_backspace_deletes_character(self) -> None:
        dialog = InputDialog(make_console())
        for c in "abc":
            dialog.handle_key(char(c))
        dialog.handle_key(KeyEvent(key=Key.BACKSPACE))
        assert dialog.buffer == "ab"
        assert dialog.cursor_pos == 2

    def test_backspace_at_start_is_ignored(self) -> None:
        dialog = InputDialog(make_console())
        dialog.handle_key(KeyEvent(key=Key.BACKSPACE))
        assert dialog.buffer == ""

    def test_enter_confirms(self) -> None:
        dialog = InputDialog(make_console())
        dialog.handle_key(char("5"))
        assert dialog.handle_key(enter()) == "5"

    def test_escape_cancels(self) -> None:
        dialog = InputDialog(make_console())
        dialog.handle_key(char("5"))
        assert dialog.handle_key(escape()) == "CANCEL"

    def test_empty_input_confirms_empty_string(self) -> None:
        dialog = InputDialog(make_console())
        assert dialog.handle_key(enter()) == ""

    def test_ctrl_c_is_not_consumed_by_dialog(self) -> None:
        dialog = InputDialog(make_console())
        assert dialog.handle_key(KeyEvent(key=Key.CTRL_C)) is None
        assert dialog.buffer == ""

    def test_error_is_rendered(self) -> None:
        console = make_console()
        dialog = InputDialog(console)
        dialog.error = "must be a number"
        console.print(dialog.render("Edit", "prompt", "5"))
        assert "must be a number" in console.file.getvalue()


class TestSelectionDialog:
    OPTIONS = [("system", "System"), ("light", "Light"), ("dark", "Dark")]

    def test_preselects_current_value(self) -> None:
        dialog = SelectionDialog(make_console())
        dialog.set_options(self.OPTIONS, current="light")
        assert dialog.selected_index == 1

    def test_preselect_defaults_to_first(self) -> None:
        dialog = SelectionDialog(make_console())
        dialog.set_options(self.OPTIONS, current=None)
        assert dialog.selected_index == 0

    def test_navigation(self) -> None:
        dialog = SelectionDialog(make_console())
        dialog.set_options(self.OPTIONS, current="system")
        dialog.handle_key(KeyEvent(key=Key.DOWN))
        assert dialog.handle_key(enter()) == "light"
        dialog.handle_key(KeyEvent(key=Key.UP))
        assert dialog.handle_key(enter()) == "system"

    def test_navigation_bounds(self) -> None:
        dialog = SelectionDialog(make_console())
        dialog.set_options(self.OPTIONS)
        for _ in range(10):
            dialog.handle_key(KeyEvent(key=Key.DOWN))
        assert dialog.selected_index == len(self.OPTIONS) - 1
        for _ in range(10):
            dialog.handle_key(KeyEvent(key=Key.UP))
        assert dialog.selected_index == 0

    def test_escape_cancels(self) -> None:
        dialog = SelectionDialog(make_console())
        dialog.set_options(self.OPTIONS)
        assert dialog.handle_key(escape()) == "CANCEL"

    def test_empty_options_returns_none(self) -> None:
        dialog = SelectionDialog(make_console())
        dialog.set_options([])
        assert dialog.handle_key(enter()) is None


class TestConfirmDialog:
    def test_yes_confirms(self) -> None:
        dialog = ConfirmDialog(make_console())
        assert dialog.handle_key(enter()) is True

    def test_no_confirms(self) -> None:
        dialog = ConfirmDialog(make_console())
        dialog.handle_key(KeyEvent(key=Key.RIGHT))
        assert dialog.handle_key(enter()) is False

    def test_escape_cancels(self) -> None:
        dialog = ConfirmDialog(make_console())
        assert dialog.handle_key(escape()) is None


# ----------------------------------------------------------------------
# HotkeyCapture tests


class TestHotkeyCapture:
    def test_key_to_string_maps_plain_characters(self) -> None:
        from pynput import keyboard

        capturer = HotkeyCapture()
        assert capturer._key_to_string(keyboard.KeyCode.from_char("O")) == "o"
        assert capturer._key_to_string(keyboard.KeyCode.from_char("5")) == "5"

    def test_key_to_string_maps_ctrl_control_characters(self) -> None:
        """Ctrl+letter arrives as a control character (Ctrl+O is \\x0f)."""
        from pynput import keyboard

        capturer = HotkeyCapture()
        assert capturer._key_to_string(keyboard.KeyCode.from_char("\x0f")) == "o"
        assert capturer._key_to_string(keyboard.KeyCode.from_char("\x01")) == "a"

    def test_key_to_string_maps_macos_virtual_key_codes(self) -> None:
        """On macOS, modifier combinations carry a vk code, not a character."""
        from pynput import keyboard

        capturer = HotkeyCapture()
        # 0x1F is the macOS virtual key code for "O" (not ASCII 31).
        assert capturer._key_to_string(keyboard.KeyCode.from_vk(0x1F)) == "o"
        assert capturer._key_to_string(keyboard.KeyCode.from_vk(0x00)) == "a"

    def test_key_to_string_windows_vk_is_ascii_compatible(self, monkeypatch) -> None:
        from pynput import keyboard

        monkeypatch.setattr("otpilot.infrastructure.terminal.hotkey_capture.sys.platform", "win32")
        capturer = HotkeyCapture()
        assert capturer._key_to_string(keyboard.KeyCode.from_vk(0x4F)) == "o"

    def test_capture_raises_when_macos_blocks_input_monitoring(self, monkeypatch) -> None:
        from otpilot.domain.errors import OTPilotError
        from otpilot.infrastructure.terminal import hotkey_capture

        monkeypatch.setattr(hotkey_capture, "_macos_accessibility_denied", lambda: True)
        capturer = hotkey_capture.HotkeyCapture()

        with pytest.raises(OTPilotError, match="Accessibility"):
            capturer.capture(timeout=1.0)

    def test_capture_starts_when_accessibility_allowed(self, monkeypatch) -> None:
        from otpilot.infrastructure.terminal import hotkey_capture

        monkeypatch.setattr(hotkey_capture, "_macos_accessibility_denied", lambda: False)
        capturer = hotkey_capture.HotkeyCapture()

        assert capturer.capture(timeout=0.2) is None