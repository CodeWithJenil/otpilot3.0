"""Tests for the redesigned ConfigController (state-machine-based editor).

These tests mirror the integration tests from test_config_ui.py but target
the new ConfigController with its explicit state machine.
"""

import io
from collections import deque

import pytest
from rich.console import Console

from otpilot.application.settings import SettingsService, SETTABLE_KEYS
from otpilot.cli.commands.config_controller import (
    RESET_ACTION_KEY,
    ConfigController,
    RichRenderer,
    create_controller,
)
from otpilot.infrastructure.config_storage.toml import TomlConfigurationRepository
from otpilot.infrastructure.preferences.toml import TomlPreferencesRepository
from otpilot.infrastructure.terminal.keyboard import Key, KeyEvent, parse_key
from otpilot.infrastructure.terminal.ui import SettingsMenu


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


def make_controller(service: SettingsService, *keys: str) -> ConfigController:
    console = make_console()
    controller = create_controller(
        console=console,
        service=service,
        key_reader=ScriptedKeys(*keys),
        hotkey_capturer=None,  # Will be mocked in tests
    )
    return controller


def down(n: int = 1) -> str:
    return "\x1b[B" * n


def up(n: int = 1) -> str:
    return "\x1b[A" * n


def right(n: int = 1) -> str:
    return "\x1b[C" * n


# ----------------------------------------------------------------------
# Menu tests (reusing SettingsMenu tests from test_config_ui.py)


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
            RESET_ACTION_KEY,
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
            RESET_ACTION_KEY,
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


# ----------------------------------------------------------------------
# Dialog tests (reusing from test_config_ui.py)


class TestInputDialog:
    def test_typing_appends_at_cursor(self) -> None:
        from otpilot.infrastructure.terminal.ui import InputDialog
        dialog = InputDialog(make_console())
        for c in "abc":
            dialog.handle_key(char(c))
        assert dialog.buffer == "abc"
        assert dialog.cursor_pos == 3

    def test_cursor_movement(self) -> None:
        from otpilot.infrastructure.terminal.ui import InputDialog
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
        from otpilot.infrastructure.terminal.ui import InputDialog
        dialog = InputDialog(make_console())
        for c in "abc":
            dialog.handle_key(char(c))
        dialog.handle_key(KeyEvent(key=Key.BACKSPACE))
        assert dialog.buffer == "ab"
        assert dialog.cursor_pos == 2

    def test_backspace_at_start_is_ignored(self) -> None:
        from otpilot.infrastructure.terminal.ui import InputDialog
        dialog = InputDialog(make_console())
        dialog.handle_key(KeyEvent(key=Key.BACKSPACE))
        assert dialog.buffer == ""

    def test_enter_confirms(self) -> None:
        from otpilot.infrastructure.terminal.ui import InputDialog
        dialog = InputDialog(make_console())
        dialog.handle_key(char("5"))
        assert dialog.handle_key(enter()) == "5"

    def test_escape_cancels(self) -> None:
        from otpilot.infrastructure.terminal.ui import InputDialog
        dialog = InputDialog(make_console())
        dialog.handle_key(char("5"))
        assert dialog.handle_key(escape()) == "CANCEL"

    def test_empty_input_confirms_empty_string(self) -> None:
        from otpilot.infrastructure.terminal.ui import InputDialog
        dialog = InputDialog(make_console())
        assert dialog.handle_key(enter()) == ""

    def test_ctrl_c_is_not_consumed_by_dialog(self) -> None:
        from otpilot.infrastructure.terminal.ui import InputDialog
        dialog = InputDialog(make_console())
        assert dialog.handle_key(KeyEvent(key=Key.CTRL_C)) is None
        assert dialog.buffer == ""

    def test_error_is_rendered(self) -> None:
        from otpilot.infrastructure.terminal.ui import InputDialog
        console = make_console()
        dialog = InputDialog(console)
        dialog.error = "must be a number"
        console.print(dialog.render("Edit", "prompt", "5"))
        assert "must be a number" in console.file.getvalue()


class TestSelectionDialog:
    OPTIONS = [("system", "System"), ("light", "Light"), ("dark", "Dark")]

    def test_preselects_current_value(self) -> None:
        from otpilot.infrastructure.terminal.ui import SelectionDialog
        dialog = SelectionDialog(make_console())
        dialog.set_options(self.OPTIONS, current="light")
        assert dialog.selected_index == 1

    def test_preselect_defaults_to_first(self) -> None:
        from otpilot.infrastructure.terminal.ui import SelectionDialog
        dialog = SelectionDialog(make_console())
        dialog.set_options(self.OPTIONS, current=None)
        assert dialog.selected_index == 0

    def test_navigation(self) -> None:
        from otpilot.infrastructure.terminal.ui import SelectionDialog
        dialog = SelectionDialog(make_console())
        dialog.set_options(self.OPTIONS, current="system")
        dialog.handle_key(KeyEvent(key=Key.DOWN))
        assert dialog.handle_key(enter()) == "light"
        dialog.handle_key(KeyEvent(key=Key.UP))
        assert dialog.handle_key(enter()) == "system"

    def test_navigation_bounds(self) -> None:
        from otpilot.infrastructure.terminal.ui import SelectionDialog
        dialog = SelectionDialog(make_console())
        dialog.set_options(self.OPTIONS)
        for _ in range(10):
            dialog.handle_key(KeyEvent(key=Key.DOWN))
        assert dialog.selected_index == len(self.OPTIONS) - 1
        for _ in range(10):
            dialog.handle_key(KeyEvent(key=Key.UP))
        assert dialog.selected_index == 0

    def test_escape_cancels(self) -> None:
        from otpilot.infrastructure.terminal.ui import SelectionDialog
        dialog = SelectionDialog(make_console())
        dialog.set_options(self.OPTIONS)
        assert dialog.handle_key(escape()) == "CANCEL"

    def test_empty_options_returns_none(self) -> None:
        from otpilot.infrastructure.terminal.ui import SelectionDialog
        dialog = SelectionDialog(make_console())
        dialog.set_options([])
        assert dialog.handle_key(enter()) is None


class TestConfirmDialog:
    def test_yes_confirms(self) -> None:
        from otpilot.infrastructure.terminal.ui import ConfirmDialog
        dialog = ConfirmDialog(make_console())
        assert dialog.handle_key(enter()) is True

    def test_no_confirms(self) -> None:
        from otpilot.infrastructure.terminal.ui import ConfirmDialog
        dialog = ConfirmDialog(make_console())
        dialog.handle_key(KeyEvent(key=Key.RIGHT))
        assert dialog.handle_key(enter()) is False

    def test_escape_cancels(self) -> None:
        from otpilot.infrastructure.terminal.ui import ConfirmDialog
        dialog = ConfirmDialog(make_console())
        assert dialog.handle_key(escape()) is None


# ----------------------------------------------------------------------
# Controller integration tests
#
# Menu order (initial selection on provider_id):
# 0: provider.provider_id, 1: provider.account, 2: credential_backend.backend,
# 3: poll_interval_seconds, 4: hotkey, 5: preferences.theme,
# 6: preferences.notifications_enabled, 7: preferences.auto_paste_enabled,
# 8: RESET_ACTION_KEY, 9: EXIT_ACTION_KEY


class MockHotkeyCapturer:
    """Mock hotkey capturer for testing."""

    def __init__(self, return_value: str | None = "ctrl+shift+p") -> None:
        self.return_value = return_value
        self.called = False

    def capture(self, timeout: float = 30.0) -> str | None:
        self.called = True
        return self.return_value


class TestControllerMenuFlow:
    def test_macos_return_key_selects_and_confirms(self, tmp_path) -> None:
        """Regression: macOS Return (\\r) must select and confirm, not exit."""
        service = make_service(tmp_path)
        controller = make_controller(
            service,
            down(3), "\r", "10", "\r", "\x1b",
        )
        controller.hotkey_capturer = MockHotkeyCapturer()

        controller.run()

        assert service.snapshot().entry("poll_interval_seconds").value == 10.0
        assert (tmp_path / "config.toml").exists()
        assert "Goodbye" in controller.renderer.console.file.getvalue()

    def test_newline_key_selects_and_confirms(self, tmp_path) -> None:
        service = make_service(tmp_path)
        controller = make_controller(
            service,
            down(3), "\n", "10", "\n", "\x1b",
        )
        controller.hotkey_capturer = MockHotkeyCapturer()

        controller.run()

        assert service.snapshot().entry("poll_interval_seconds").value == 10.0

    def test_edit_returns_to_menu_and_shows_updated_value(self, tmp_path) -> None:
        service = make_service(tmp_path)
        controller = make_controller(
            service,
            down(3), "\r", "10", "\r", "\x1b",
        )
        controller.hotkey_capturer = MockHotkeyCapturer()

        controller.run()

        output = controller.renderer.console.file.getvalue()
        assert "Poll Interval 10.0" in output
        assert "Edit Poll Interval" in output

    def test_invalid_value_shows_error_and_retries(self, tmp_path) -> None:
        service = make_service(tmp_path)
        controller = make_controller(
            service,
            down(3), "\r", "a", "\r", "10", "\r", "\x1b",
        )
        controller.hotkey_capturer = MockHotkeyCapturer()

        controller.run()

        output = controller.renderer.console.file.getvalue()
        assert "must be a number" in output
        assert service.snapshot().entry("poll_interval_seconds").value == 10.0

    def test_cancelled_edit_is_not_saved(self, tmp_path) -> None:
        service = make_service(tmp_path)
        controller = make_controller(
            service,
            down(3), "\r", "9", "\x1b", "\x1b",
        )
        controller.hotkey_capturer = MockHotkeyCapturer()

        controller.run()

        assert service.snapshot().entry("poll_interval_seconds").value == 30.0
        assert not (tmp_path / "config.toml").exists()

    def test_confirming_same_value_keeps_it(self, tmp_path) -> None:
        service = make_service(tmp_path)
        controller = make_controller(
            service,
            down(3), "\r", "30.0", "\r", "\x1b",
        )
        controller.hotkey_capturer = MockHotkeyCapturer()

        controller.run()

        assert service.snapshot().entry("poll_interval_seconds").value == 30.0

    def test_empty_numeric_input_shows_error_and_stays(self, tmp_path) -> None:
        service = make_service(tmp_path)
        controller = make_controller(
            service,
            down(3), "\r", "\r", "\x1b", "\x1b",
        )
        controller.hotkey_capturer = MockHotkeyCapturer()

        controller.run()

        output = controller.renderer.console.file.getvalue()
        assert "must be a number" in output
        assert service.snapshot().entry("poll_interval_seconds").value == 30.0

    def test_empty_account_input_clears_account(self, tmp_path) -> None:
        service = make_service(tmp_path)
        service.set("provider.account", "old@example.com")
        controller = make_controller(
            service,
            down(1), "\r", "\r", "\x1b",
        )
        controller.hotkey_capturer = MockHotkeyCapturer()

        controller.run()

        assert service.snapshot().entry("provider.account").value is None

    def test_theme_selection(self, tmp_path) -> None:
        service = make_service(tmp_path)
        controller = make_controller(
            service,
            down(5), "\r", "\x1b[B", "\r", "\x1b",
        )
        controller.hotkey_capturer = MockHotkeyCapturer()

        controller.run()

        assert service.snapshot().entry("preferences.theme").value == "light"

    def test_boolean_selection(self, tmp_path) -> None:
        service = make_service(tmp_path)
        controller = make_controller(
            service,
            down(6), "\r", "\x1b[B", "\r", "\x1b",
        )
        controller.hotkey_capturer = MockHotkeyCapturer()

        controller.run()

        assert service.snapshot().entry("preferences.notifications_enabled").value is False

    def test_provider_selection(self, tmp_path) -> None:
        service = make_service(tmp_path)
        controller = make_controller(
            service,
            "\r", "\r", "\x1b",
        )
        controller.hotkey_capturer = MockHotkeyCapturer()

        controller.run()

        assert service.snapshot().entry("provider.provider_id").value == "gmail"

    def test_provider_account_text_input(self, tmp_path) -> None:
        service = make_service(tmp_path)
        controller = make_controller(
            service,
            down(1), "\r", "test@example.com", "\r", "\x1b",
        )
        controller.hotkey_capturer = MockHotkeyCapturer()

        controller.run()

        assert service.snapshot().entry("provider.account").value == "test@example.com"


class TestControllerExit:
    def test_escape_exits_without_modifying(self, tmp_path) -> None:
        service = make_service(tmp_path)
        controller = make_controller(service, "\x1b")
        controller.hotkey_capturer = MockHotkeyCapturer()

        controller.run()

        assert not (tmp_path / "config.toml").exists()
        assert not (tmp_path / "preferences.toml").exists()
        assert "Goodbye" in controller.renderer.console.file.getvalue()

    def test_ctrl_c_exits_cleanly(self, tmp_path) -> None:
        service = make_service(tmp_path)
        controller = make_controller(service, "\x03")
        controller.hotkey_capturer = MockHotkeyCapturer()

        controller.run()

        assert "Goodbye" in controller.renderer.console.file.getvalue()

    def test_ctrl_d_exits_cleanly(self, tmp_path) -> None:
        service = make_service(tmp_path)
        controller = make_controller(service, "\x04")
        controller.hotkey_capturer = MockHotkeyCapturer()

        controller.run()

        assert "Goodbye" in controller.renderer.console.file.getvalue()

    def test_q_exits(self, tmp_path) -> None:
        service = make_service(tmp_path)
        controller = make_controller(service, "q")
        controller.hotkey_capturer = MockHotkeyCapturer()

        controller.run()

        assert "Goodbye" in controller.renderer.console.file.getvalue()

    def test_exit_item_exits(self, tmp_path) -> None:
        service = make_service(tmp_path)
        controller = make_controller(service, down(9), "\r")
        controller.hotkey_capturer = MockHotkeyCapturer()

        controller.run()

        assert "Goodbye" in controller.renderer.console.file.getvalue()

    def test_keyboard_interrupt_is_caught(self, tmp_path) -> None:
        service = make_service(tmp_path)

        def raising_reader() -> KeyEvent:
            raise KeyboardInterrupt

        console = make_console()
        controller = create_controller(
            console=console,
            service=service,
            key_reader=raising_reader,
            hotkey_capturer=MockHotkeyCapturer(),
        )
        controller.run()


class TestControllerReset:
    def test_reset_confirmed(self, tmp_path) -> None:
        service = make_service(tmp_path)
        service.set("poll_interval_seconds", "10")
        controller = make_controller(service, down(8), "\r", "\r", "\x1b")
        controller.hotkey_capturer = MockHotkeyCapturer()

        controller.run()

        assert not (tmp_path / "config.toml").exists()
        assert not (tmp_path / "preferences.toml").exists()
        assert service.snapshot().entry("poll_interval_seconds").value == 30.0

    def test_reset_cancelled_with_escape(self, tmp_path) -> None:
        service = make_service(tmp_path)
        service.set("poll_interval_seconds", "10")
        controller = make_controller(service, down(8), "\r", "\x1b", "\x1b")
        controller.hotkey_capturer = MockHotkeyCapturer()

        controller.run()

        assert (tmp_path / "config.toml").exists()
        assert service.snapshot().entry("poll_interval_seconds").value == 10.0

    def test_reset_cancelled_with_no(self, tmp_path) -> None:
        service = make_service(tmp_path)
        service.set("poll_interval_seconds", "10")
        controller = make_controller(service, down(8), "\r", right(), "\r", "\x1b")
        controller.hotkey_capturer = MockHotkeyCapturer()

        controller.run()

        assert (tmp_path / "config.toml").exists()
        assert service.snapshot().entry("poll_interval_seconds").value == 10.0

    def test_reset_preserves_credentials(self, tmp_path) -> None:
        """Reset must only clear config/preferences; credentials are separate."""
        config = TomlConfigurationRepository(tmp_path / "config.toml")
        preferences = TomlPreferencesRepository(tmp_path / "preferences.toml")
        calls: list[str] = []
        config.clear = lambda: calls.append("config.clear")
        preferences.clear = lambda: calls.append("preferences.clear")
        service = SettingsService(config=config, preferences=preferences)

        service.reset()

        assert calls == ["config.clear", "preferences.clear"]


class TestControllerHotkey:
    def test_capture_success_saves(self, tmp_path) -> None:
        service = make_service(tmp_path)
        mock_capturer = MockHotkeyCapturer("ctrl+shift+p")
        controller = make_controller(service, down(4), "\r", "\x1b")
        controller.hotkey_capturer = mock_capturer

        controller.run()

        assert service.snapshot().entry("hotkey").value == "ctrl+shift+p"
        assert mock_capturer.called

    def test_capture_cancelled_does_not_save(self, tmp_path) -> None:
        service = make_service(tmp_path)
        mock_capturer = MockHotkeyCapturer(None)
        controller = make_controller(service, down(4), "\r", "\x1b")
        controller.hotkey_capturer = mock_capturer

        controller.run()

        assert service.snapshot().entry("hotkey").value == "ctrl+shift+o"
        assert mock_capturer.called

    def test_capture_invalid_combination_rejected(self, tmp_path) -> None:
        service = make_service(tmp_path)
        mock_capturer = MockHotkeyCapturer("esc")  # Invalid - only modifier
        controller = make_controller(service, down(4), "\r", "\r", "\x1b")
        controller.hotkey_capturer = mock_capturer

        controller.run()

        output = controller.renderer.console.file.getvalue()
        assert "modifiers" in output
        assert service.snapshot().entry("hotkey").value == "ctrl+shift+o"

    def test_capture_failure_shows_error_and_continues(self, tmp_path) -> None:
        service = make_service(tmp_path)

        class FailingCapturer:
            def capture(self, timeout: float = 30.0) -> str | None:
                raise RuntimeError("boom")

        controller = make_controller(service, down(4), "\r", "\r", "\x1b")
        controller.hotkey_capturer = FailingCapturer()

        controller.run()

        assert "Hotkey capture failed: boom" in controller.renderer.console.file.getvalue()


class TestControllerStateMachine:
    """Test explicit state transitions."""

    def test_initial_state_is_menu(self, tmp_path) -> None:
        service = make_service(tmp_path)
        controller = create_controller(
            console=make_console(),
            service=service,
            key_reader=lambda: KeyEvent(key=Key.ESCAPE),
            hotkey_capturer=MockHotkeyCapturer(),
        )
        assert controller.state == State.MENU

    def test_state_transitions_menu_to_edit_text(self, tmp_path) -> None:
        service = make_service(tmp_path)
        keys = ScriptedKeys(down(1), "\r", "test", "\r", "\x1b")
        controller = create_controller(
            console=make_console(),
            service=service,
            key_reader=keys,
            hotkey_capturer=MockHotkeyCapturer(),
        )
        # Initially in MENU
        assert controller.state == State.MENU
        # After Enter on provider.account (down 1), should go to EDIT_TEXT
        # We can't easily test intermediate states without running, but we can verify final result
        controller.run()
        assert service.snapshot().entry("provider.account").value == "test"

    def test_buffer_cleared_on_validation_error(self, tmp_path) -> None:
        """Buffer should be cleared on validation error for clean retry."""
        service = make_service(tmp_path)
        controller = make_controller(
            service,
            down(3), "\r", "a", "\r",  # Invalid - error shown, buffer cleared
            "10", "\r",  # Type "10" fresh, confirm
            "\x1b",
        )
        controller.hotkey_capturer = MockHotkeyCapturer()

        controller.run()

        assert service.snapshot().entry("poll_interval_seconds").value == 10.0


# Import State for the test above
from otpilot.cli.commands.config_controller import State