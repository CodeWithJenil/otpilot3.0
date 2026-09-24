"""Synchronous keyboard reader for terminal input.

This module provides a single :func:`read_key` function that blocks until a key
is pressed and returns a :class:`KeyEvent` instance.  It is a lightweight
replacement for the asynchronous :class:`TerminalKeyboardHandler` used by the
original OTPilot configuration UI.

The implementation mirrors the parsing logic from
``otpilot.infrastructure.terminal.keyboard`` but operates in a blocking
fashion suitable for a simple synchronous configuration editor.
"""

from __future__ import annotations

import sys
import termios
import tty
from typing import Any

# Import the Key enum and KeyEvent dataclass from the existing keyboard module
from .keyboard import Key, KeyEvent


def _parse_key_unix(ch: str) -> KeyEvent | None:
    """Parse a character or escape sequence into a :class:`KeyEvent`.

    This logic is identical to the one used by the asynchronous handler.
    """
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


def _parse_key_windows(ch: bytes) -> KeyEvent | None:
    """Parse a Windows key byte into a :class:`KeyEvent`."""
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


def read_key() -> KeyEvent:
    """Block until a key is pressed and return a :class:`KeyEvent`.

    The function works on Unix-like systems and Windows.  It restores the
    terminal state after reading a key.
    """
    if sys.platform == "win32":
        import msvcrt
        ch = msvcrt.getch()
        return _parse_key_windows(ch)
    # Unix-like
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        ch = sys.stdin.read(1)
        return _parse_key_unix(ch)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

*** End Patch