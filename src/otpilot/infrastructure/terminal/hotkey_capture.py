"""Cross-platform hotkey capture using pynput."""

from __future__ import annotations

import sys
import threading
from contextlib import suppress

from pynput import keyboard  # type: ignore[import-untyped]

from otpilot.domain.errors import OTPilotError

# macOS virtual key codes for printable keys.  Modifier combinations on
# macOS often carry no character, only a virtual key code; these codes are
# HID usages, not ASCII (e.g. "O" is 0x1F), so they must be mapped
# explicitly.  On Windows virtual key codes are ASCII-compatible.
_MACOS_VK_CHARS: dict[int, str] = {
    0x00: "a", 0x01: "s", 0x02: "d", 0x03: "f", 0x04: "h", 0x05: "g",
    0x06: "z", 0x07: "x", 0x08: "c", 0x09: "v", 0x0B: "b", 0x0C: "q",
    0x0D: "w", 0x0E: "e", 0x0F: "r", 0x10: "y", 0x11: "t",
    0x12: "1", 0x13: "2", 0x14: "3", 0x15: "4", 0x16: "6", 0x17: "5",
    0x18: "=", 0x19: "9", 0x1A: "7", 0x1B: "-", 0x1C: "8", 0x1D: "0",
    0x1E: "]", 0x1F: "o", 0x20: "u", 0x21: "[", 0x22: "i", 0x23: "p",
    0x25: "l", 0x26: "j", 0x27: "'", 0x28: "k", 0x29: ";", 0x2A: "\\",
    0x2B: ",", 0x2C: "/", 0x2D: "n", 0x2E: "m", 0x2F: ".",
}


def _macos_accessibility_denied() -> bool:
    """Return True when macOS blocks input monitoring for this process.

    pynput's global listener starts but never receives events until the
    hosting application is added to **both** Accessibility **and** Input Monitoring
    allowlists. The standard ``AXIsProcessTrusted`` check detects this so
    the failure can be reported instead of silently timing out.
    """
    if sys.platform != "darwin":
        return False
    try:
        import ctypes

        framework = (
            "/System/Library/Frameworks/ApplicationServices.framework"
            "/ApplicationServices"
        )
        lib = ctypes.cdll.LoadLibrary(framework)
        lib.AXIsProcessTrusted.restype = ctypes.c_bool
        return not lib.AXIsProcessTrusted()
    except OSError:
        # The check itself is unavailable; do not block capture on it.
        return False


class HotkeyCapture:
    """Capture a hotkey combination from physical key presses.

    Uses pynput for global hotkey capture - only used for the
    hotkey configuration dialog, not for general navigation.

    Pressing ``Esc`` cancels the capture.  The capture always returns within
    ``timeout`` seconds, so it never blocks the application permanently.
    """

    def __init__(self) -> None:
        self._pressed_keys: set[str] = set()
        self._result: str | None = None
        self._cancelled = False
        self._done = threading.Event()
        self._listener: keyboard.Listener | None = None
        self._lock = threading.Lock()

    def capture(self, timeout: float = 30.0) -> str | None:
        """Capture a hotkey combination from the user.

        Returns the normalized hotkey string (e.g., "ctrl+shift+o"), or None
        if the capture was cancelled, timed out, or only modifiers were
        pressed.
        """
        self._pressed_keys.clear()
        self._result = None
        self._cancelled = False
        self._done.clear()

        if _macos_accessibility_denied():
            raise OTPilotError(
                "macOS is blocking keyboard input monitoring for this process. "
                "Add your terminal app to **Accessibility AND Input Monitoring** in "
                "System Settings > Privacy & Security, then try again."
            )

        def on_press(key: keyboard.Key | keyboard.KeyCode) -> bool:
            with self._lock:
                key_str = self._key_to_string(key)
                if key_str == "esc":
                    # Escape cancels the capture.
                    self._cancelled = True
                    self._done.set()
                    return False
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

        try:
            # Wait for result or timeout
            self._done.wait(timeout=timeout)
        finally:
            if self._listener:
                with suppress(Exception):
                    self._listener.stop()
                with suppress(Exception):
                    self._listener.join(timeout=1.0)
                self._listener = None

        if self._cancelled:
            return None
        return self._result or None

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
                char = key.char.lower()
                if "\x01" <= char <= "\x1a":
                    # Ctrl+letter arrives as a control character (e.g. Ctrl+O
                    # is "\\x0f"); map it back to the plain letter.
                    return chr(ord(char) + 0x60)
                return char
            if key.vk is not None:
                vk = key.vk
                if vk < 256:
                    if sys.platform == "darwin":
                        return _MACOS_VK_CHARS.get(vk)
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
        return "+".join([*modifiers, main_key])