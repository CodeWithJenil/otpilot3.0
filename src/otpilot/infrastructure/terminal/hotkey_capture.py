"""Cross-platform hotkey capture using pynput."""

from __future__ import annotations

import threading
from contextlib import suppress
from typing import Any

from pynput import keyboard  # type: ignore[import-untyped]


class HotkeyCapture:
    """Capture a hotkey combination from physical key presses.

    Uses pynput for global hotkey capture - only used for the
    hotkey configuration dialog, not for general navigation.
    """

    def __init__(self) -> None:
        self._pressed_keys: set[str] = set()
        self._result: str | None = None
        self._done = threading.Event()
        self._listener: keyboard.Listener | None = None
        self._lock = threading.Lock()

    def capture(self, timeout: float = 30.0) -> str | None:
        """Capture a hotkey combination from the user.

        Returns the normalized hotkey string (e.g., "ctrl+shift+o") or None if cancelled.
        """
        self._pressed_keys.clear()
        self._result = None
        self._done.clear()

        def on_press(key: keyboard.Key | keyboard.KeyCode) -> bool:
            with self._lock:
                key_str = self._key_to_string(key)
                if key_str:
                    self._pressed_keys.add(key_str)
                return True

        def on_release(key: keyboard.Key | keyboard.KeyCode) -> bool:
            with self._lock:
                key_str = self._key_to_string(key)
                if key_str and key_str in self._pressed_keys:
                    # Key combination complete - normalize and return
                    self._result = self._normalize_combination(self._pressed_keys)
                    self._pressed_keys.clear()
                    self._done.set()
                    return False  # Stop listener
            return True

        self._listener = keyboard.Listener(on_press=on_press, on_release=on_release, suppress=False)
        self._listener.start()

        # Wait for result or timeout
        self._done.wait(timeout=timeout)

        if self._listener:
            with suppress(Exception):
                self._listener.stop()
            with suppress(Exception):
                self._listener.join(timeout=1.0)
            self._listener = None

        return self._result

    def _key_to_string(self, key: keyboard.Key | keyboard.KeyCode) -> str | None:
        """Convert a pynput key to a normalized string."""
        if isinstance(key, keyboard.Key):
            key_map = {
                keyboard.Key.ctrl_l: "ctrl",
                keyboard.Key.ctrl_r: "ctrl",
                keyboard.Key.alt_l: "alt",
                keyboard.Key.alt_r: "alt",
                keyboard.Key.shift_l: "shift",
                keyboard.Key.shift_r: "shift",
                keyboard.Key.cmd_l: "cmd",
                keyboard.Key.cmd_r: "cmd",
                keyboard.Key.ctrl: "ctrl",
                keyboard.Key.alt: "alt",
                keyboard.Key.shift: "shift",
                keyboard.Key.cmd: "cmd",
                keyboard.Key.enter: "enter",
                keyboard.Key.esc: "esc",
                keyboard.Key.tab: "tab",
                keyboard.Key.space: "space",
                keyboard.Key.backspace: "backspace",
                keyboard.Key.delete: "delete",
                keyboard.Key.home: "home",
                keyboard.Key.end: "end",
                keyboard.Key.page_up: "page_up",
                keyboard.Key.page_down: "page_down",
            }
            for i in range(1, 25):
                key_map[getattr(keyboard.Key, f"f{i}", None)] = f"f{i}"
            return key_map.get(key)

        if isinstance(key, keyboard.KeyCode):
            if key.char:
                return key.char.lower()
            if key.vk:
                vk = key.vk
                if vk is not None and vk < 256:
                    return chr(vk).lower()
        return None

    def _normalize_combination(self, keys: set[str]) -> str:
        """Normalize a set of pressed keys into a canonical hotkey string."""
        modifier_order = ["ctrl", "alt", "shift", "cmd", "win"]
        modifiers = sorted([k for k in keys if k in modifier_order], key=lambda x: modifier_order.index(x))
        non_modifiers = [k for k in keys if k not in modifier_order]

        # Filter out standalone modifiers
        if not non_modifiers:
            return ""

        # Take the first non-modifier as the main key
        main_key = non_modifiers[0]

        # Build combination
        parts = modifiers + [main_key]
        return "+".join(parts)