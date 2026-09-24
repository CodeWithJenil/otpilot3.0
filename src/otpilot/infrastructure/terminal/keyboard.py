"""Terminal keyboard input handling using stdin."""

from __future__ import annotations

import sys
import threading
import termios
import tty
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any


class Key(Enum):
    """Normalized key identifiers."""

    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
    ENTER = "enter"
    ESCAPE = "escape"
    BACKSPACE = "backspace"
    TAB = "tab"
    SPACE = "space"
    CTRL_C = "ctrl_c"
    CTRL_D = "ctrl_d"

    # Regular keys
    CHAR = "char"


@dataclass(frozen=True, slots=True)
class KeyEvent:
    """A normalized keyboard event."""

    key: Key
    char: str | None = None
    ctrl: bool = False
    alt: bool = False
    shift: bool = False
    meta: bool = False

    def __str__(self) -> str:
        parts = []
        if self.ctrl:
            parts.append("Ctrl")
        if self.alt:
            parts.append("Alt")
        if self.shift:
            parts.append("Shift")
        if self.meta:
            parts.append("Meta")
        if self.key == Key.CHAR and self.char:
            parts.append(self.char.upper() if len(self.char) == 1 else self.char)
        elif self.key != Key.CHAR:
            parts.append(self.key.value.upper())
        return "+".join(parts) if parts else "Unknown"


class TerminalKeyboardHandler:
    """Terminal-native keyboard handler using stdin.

    Works on Unix-like systems (macOS, Linux) without requiring
    accessibility permissions.
    """

    def __init__(self) -> None:
        self._callbacks: list[Callable[[KeyEvent], None]] = []
        self._running = False
        self._thread: threading.Thread | None = None
        self._old_settings: Any = None

    def start(self) -> bool:
        """Start listening for keyboard events from stdin.

        Returns True if started successfully, False if stdin is not a TTY.
        """
        if self._running:
            return True

        if not sys.stdin.isatty():
            return False

        self._running = True
        self._old_settings = termios.tcgetattr(sys.stdin.fileno())
        tty.setcbreak(sys.stdin.fileno())

        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()
        return True

    def stop(self) -> None:
        """Stop listening for keyboard events."""
        if not self._running:
            return

        self._running = False

        if self._old_settings is not None:
            try:
                termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, self._old_settings)
            except Exception:
                pass

        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None

    def on_key(self, callback: Callable[[KeyEvent], None]) -> None:
        """Register a callback for key events."""
        self._callbacks.append(callback)

    def clear_callbacks(self) -> None:
        """Clear all registered callbacks."""
        self._callbacks.clear()

    def _read_loop(self) -> None:
        """Read loop for stdin."""
        while self._running:
            try:
                ch = sys.stdin.read(1)
                if not ch:
                    break
                event = self._parse_key(ch)
                if event:
                    for callback in self._callbacks:
                        try:
                            callback(event)
                        except Exception:
                            import traceback
                            traceback.print_exc()
            except Exception:
                break

    def _parse_key(self, ch: str) -> KeyEvent | None:
        """Parse a character or escape sequence into a KeyEvent."""
        # Ctrl+C, Ctrl+D
        if ch == "\x03":
            return KeyEvent(key=Key.CTRL_C, ctrl=True)
        if ch == "\x04":
            return KeyEvent(key=Key.CTRL_D, ctrl=True)
        if ch == "\x1b":  # ESC or escape sequence
            # Read more characters for escape sequences
            next_ch = sys.stdin.read(1)
            if not next_ch:
                return KeyEvent(key=Key.ESCAPE)
            if next_ch == "[":
                third = sys.stdin.read(1)
                if third == "A":
                    return KeyEvent(key=Key.UP)
                if third == "B":
                    return KeyEvent(key=Key.DOWN)
                if third == "C":
                    return KeyEvent(key=Key.RIGHT)
                if third == "D":
                    return KeyEvent(key=Key.LEFT)
                if third == "3":
                    fourth = sys.stdin.read(1)
                    if fourth == "~":
                        return KeyEvent(key=Key.BACKSPACE)
            return KeyEvent(key=Key.ESCAPE)
        if ch == "\r" or ch == "\n":
            return KeyEvent(key=Key.ENTER)
        if ch == "\t":
            return KeyEvent(key=Key.TAB)
        if ch == " ":
            return KeyEvent(key=Key.SPACE)
        if ch == "\x7f" or ch == "\x08":
            return KeyEvent(key=Key.BACKSPACE)
        # Regular character
        return KeyEvent(key=Key.CHAR, char=ch)

    def __enter__(self) -> TerminalKeyboardHandler:
        self.start()
        return self

    def __exit__(self, *args: Any) -> None:
        self.stop()


# For Windows compatibility
class WindowsKeyboardHandler:
    """Windows-specific keyboard handler using msvcrt."""

    def __init__(self) -> None:
        self._callbacks: list[Callable[[KeyEvent], None]] = []
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self) -> bool:
        if self._running:
            return True
        self._running = True
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()
        return True

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None

    def on_key(self, callback: Callable[[KeyEvent], None]) -> None:
        self._callbacks.append(callback)

    def clear_callbacks(self) -> None:
        self._callbacks.clear()

    def _read_loop(self) -> None:
        import msvcrt

        while self._running:
            try:
                if msvcrt.kbhit():
                    ch = msvcrt.getch()
                    event = self._parse_key(ch)
                    if event:
                        for callback in self._callbacks:
                            try:
                                callback(event)
                            except Exception:
                                pass
            except Exception:
                break

    def _parse_key(self, ch: bytes) -> KeyEvent | None:
        if ch in (b"\x03",):  # Ctrl+C
            return KeyEvent(key=Key.CTRL_C, ctrl=True)
        if ch in (b"\x04",):  # Ctrl+D
            return KeyEvent(key=Key.CTRL_D, ctrl=True)
        if ch == b"\xe0":  # Arrow keys prefix
            ch2 = msvcrt.getch()
            if ch2 == b"H":
                return KeyEvent(key=Key.UP)
            if ch2 == b"P":
                return KeyEvent(key=Key.DOWN)
            if ch2 == b"M":
                return KeyEvent(key=Key.RIGHT)
            if ch2 == b"K":
                return KeyEvent(key=Key.LEFT)
            return None
        if ch in (b"\r", b"\n"):
            return KeyEvent(key=Key.ENTER)
        if ch == b"\x1b":
            return KeyEvent(key=Key.ESCAPE)
        if ch == b"\t":
            return KeyEvent(key=Key.TAB)
        if ch == b" ":
            return KeyEvent(key=Key.SPACE)
        if ch in (b"\x08", b"\x7f"):
            return KeyEvent(key=Key.BACKSPACE)
        # Regular character
        try:
            char = ch.decode("utf-8")
            return KeyEvent(key=Key.CHAR, char=char)
        except Exception:
            return None

    def __enter__(self) -> WindowsKeyboardHandler:
        self.start()
        return self

    def __exit__(self, *args: Any) -> None:
        self.stop()


def create_keyboard_handler() -> TerminalKeyboardHandler | WindowsKeyboardHandler:
    """Create the appropriate keyboard handler for the current platform."""
    if sys.platform == "win32":
        return WindowsKeyboardHandler()
    return TerminalKeyboardHandler()