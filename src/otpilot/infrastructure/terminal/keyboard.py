"""Synchronous terminal keyboard input.

This module provides a small, blocking keyboard reader for interactive
terminal commands.  The previous implementation used background threads and
callback dispatch which made control flow hard to follow and unreliable
(especially bare ``Escape`` and macOS ``Return``).  The replacement is a set
of plain synchronous functions:

``read_key()``   - block until a key is pressed, return a :class:`KeyEvent`.
``raw_mode()``   - context manager that puts stdin into cbreak mode.
``parse_key()``  - pure character/escape-sequence to :class:`KeyEvent` mapping.
``flush_stdin()``- discard pending input (used after modal hotkey capture).

There is intentionally no background thread: keyboard input is read
synchronously on the calling thread.  The only place a listener thread is
used is :mod:`otpilot.infrastructure.terminal.hotkey_capture`, which relies on
``pynput`` for global (physical) key capture.
"""

from __future__ import annotations

import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum

# Timeout (seconds) used to distinguish a bare Escape press from the start of
# an escape sequence such as ``\\x1b[A``.  Escape sequence bytes arrive within
# microseconds of each other, so a short timeout is imperceptible.
_ESCAPE_SEQUENCE_TIMEOUT = 0.05

# Timeout (seconds) used to collect UTF-8 continuation bytes of a multi-byte
# character so that ``é`` and friends are read as a single character.
_UTF8_CONTINUATION_TIMEOUT = 0.05


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


def parse_key(
    ch: str, read_next: Callable[[], str | None] | None = None
) -> KeyEvent | None:
    """Map a character (and any escape sequence) to a :class:`KeyEvent`.

    ``read_next`` is called to obtain continuation bytes of an escape
    sequence; it returns ``None`` when no further byte arrives (bare
    ``Escape`` press or end of stream).  The function is pure and safe to use
    in tests without a terminal.

    Returns ``None`` only for unrecognized extended-key prefixes on Windows.
    """
    if ch == "":
        # End of input stream – treat like Ctrl+D so callers exit gracefully.
        return KeyEvent(key=Key.CTRL_D, ctrl=True)
    if ch == "\x03":
        return KeyEvent(key=Key.CTRL_C, ctrl=True)
    if ch == "\x04":
        return KeyEvent(key=Key.CTRL_D, ctrl=True)
    if ch == "\x1b":
        next_ch = read_next() if read_next else None
        if next_ch == "[":
            third = read_next()
            if third == "A":
                return KeyEvent(key=Key.UP)
            if third == "B":
                return KeyEvent(key=Key.DOWN)
            if third == "C":
                return KeyEvent(key=Key.RIGHT)
            if third == "D":
                return KeyEvent(key=Key.LEFT)
            if third == "3" and read_next() == "~":
                return KeyEvent(key=Key.BACKSPACE)
        return KeyEvent(key=Key.ESCAPE)
    if ch in ("\r", "\n"):
        # macOS Return sends ``\r``; cooked terminals translate it to ``\n``.
        # Both are normalized to the confirm action.
        return KeyEvent(key=Key.ENTER)
    if ch == "\t":
        return KeyEvent(key=Key.TAB)
    if ch == " ":
        return KeyEvent(key=Key.SPACE)
    if ch in ("\x7f", "\x08"):
        return KeyEvent(key=Key.BACKSPACE)
    # Regular (possibly multi-byte) character.
    return KeyEvent(key=Key.CHAR, char=ch)


def _parse_key_windows(ch: str, read_next: Callable[[], str]) -> KeyEvent | None:
    """Map a Windows console character to a :class:`KeyEvent."""
    if ch in ("\x00", "\xe0"):
        # Extended key prefix (arrows, Delete, function keys).
        code = read_next()
        mapping = {
            "H": Key.UP,
            "P": Key.DOWN,
            "M": Key.RIGHT,
            "K": Key.LEFT,
            "S": Key.BACKSPACE,  # Delete key
        }
        if code in mapping:
            return KeyEvent(key=mapping[code])
        return None
    return parse_key(ch)


def _utf8_expected_length(first_byte: int) -> int:
    """Return the total byte length of the UTF-8 character started by ``first_byte``."""
    if first_byte < 0x80:
        return 1
    if first_byte >= 0xF0:
        return 4
    if first_byte >= 0xE0:
        return 3
    if first_byte >= 0xC0:
        return 2
    return 1


def _read_char_unix(fd: int) -> str:
    """Read one character (possibly multi-byte UTF-8) from ``fd``, blocking."""
    import os
    import select

    chunk = bytearray(os.read(fd, 1))
    if not chunk:
        return ""
    expected = _utf8_expected_length(chunk[0])
    while len(chunk) < expected:
        ready, _, _ = select.select([fd], [], [], _UTF8_CONTINUATION_TIMEOUT)
        if not ready:
            break
        chunk.extend(os.read(fd, 1))
    return chunk.decode("utf-8", errors="replace")


def _read_next_unix(fd: int) -> Callable[[], str | None]:
    """Return a continuation reader used to finish escape sequences.

    Uses :func:`select.select` with a short timeout so that a bare ``Escape``
    press is reported immediately instead of blocking until the next key.
    Reads bypass Python's buffered streams (``os.read``) so that escape
    sequence bytes arriving together are still returned one at a time and
    ``select`` stays accurate.
    """

    def read_next() -> str | None:
        import os
        import select

        ready, _, _ = select.select([fd], [], [], _ESCAPE_SEQUENCE_TIMEOUT)
        if not ready:
            return None
        return os.read(fd, 1).decode("utf-8", errors="replace")

    return read_next


@contextmanager
def raw_mode() -> Iterator[None]:
    """Put stdin into cbreak mode for the duration of the context.

    In cbreak mode keys are delivered immediately without echo, while ISIG
    stays enabled so ``Ctrl+C`` still raises :class:`KeyboardInterrupt`.
    The previous terminal settings are always restored on exit.

    The context is a no-op when stdin is not a TTY or on Windows, where
    ``msvcrt`` console functions already return keys without echo.
    """
    if sys.platform == "win32" or not sys.stdin.isatty():
        yield
        return

    import termios
    import tty

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        yield
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def read_key() -> KeyEvent:
    """Block until a key is pressed and return a normalized :class:`KeyEvent`.

    On Unix-like systems the terminal should already be in cbreak mode (see
    :func:`raw_mode`); without it, keys are only delivered after ``Enter``.
    On Windows ``msvcrt`` is used directly.
    """
    if sys.platform == "win32":
        import msvcrt

        while True:
            ch = msvcrt.getwch()
            event = _parse_key_windows(ch, msvcrt.getwch)
            if event is not None:
                return event

    fd = sys.stdin.fileno()
    while True:
        ch = _read_char_unix(fd)
        event = parse_key(ch, _read_next_unix(fd))
        if event is not None:
            return event


def flush_stdin() -> None:
    """Discard any pending keyboard input.

    Used after modal interactions (hotkey capture) that bypass the ordinary
    synchronous reader, so stale bytes are not processed as key events.
    """
    if sys.platform == "win32":
        import msvcrt

        while msvcrt.kbhit():
            msvcrt.getwch()
        return

    import os
    import select
    import termios

    if not sys.stdin.isatty():
        return
    fd = sys.stdin.fileno()
    termios.tcflush(fd, termios.TCIFLUSH)
    # Drain anything that arrived after the flush request.
    while select.select([fd], [], [], 0)[0]:
        if not os.read(fd, 1):
            break
