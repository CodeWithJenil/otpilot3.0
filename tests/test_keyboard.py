"""Tests for the synchronous keyboard reader.

These tests exercise the pure :func:`parse_key` mapping without a terminal,
including the macOS Return-key regression (``\\r`` must map to Enter).
"""

from otpilot.infrastructure.terminal.keyboard import Key, KeyEvent, parse_key


def _sequence(*chars: str):
    """Return a ``read_next`` callable yielding the given characters, then None."""
    iterator = iter(chars)
    return lambda: next(iterator, None)


def test_carriage_return_maps_to_enter() -> None:
    """Regression: macOS Return sends ``\\r`` (ASCII 13) and must confirm."""
    event = parse_key("\r")
    assert event is not None
    assert event.key == Key.ENTER


def test_newline_maps_to_enter() -> None:
    """Cooked terminals translate Return to ``\\n``; both must confirm."""
    event = parse_key("\n")
    assert event is not None
    assert event.key == Key.ENTER


def test_bare_escape_maps_to_escape() -> None:
    """A bare Escape press (no continuation bytes) maps to Escape."""
    event = parse_key("\x1b", _sequence())
    assert event is not None
    assert event.key == Key.ESCAPE


def test_escape_without_reader_maps_to_escape() -> None:
    """Escape with no continuation reader available maps to Escape."""
    event = parse_key("\x1b")
    assert event is not None
    assert event.key == Key.ESCAPE


def test_up_arrow_maps_correctly() -> None:
    event = parse_key("\x1b", _sequence("[", "A"))
    assert event is not None
    assert event.key == Key.UP


def test_down_arrow_maps_correctly() -> None:
    event = parse_key("\x1b", _sequence("[", "B"))
    assert event is not None
    assert event.key == Key.DOWN


def test_right_arrow_maps_correctly() -> None:
    event = parse_key("\x1b", _sequence("[", "C"))
    assert event is not None
    assert event.key == Key.RIGHT


def test_left_arrow_maps_correctly() -> None:
    event = parse_key("\x1b", _sequence("[", "D"))
    assert event is not None
    assert event.key == Key.LEFT


def test_delete_key_maps_to_backspace() -> None:
    event = parse_key("\x1b", _sequence("[", "3", "~"))
    assert event is not None
    assert event.key == Key.BACKSPACE


def test_incomplete_escape_sequence_maps_to_escape() -> None:
    event = parse_key("\x1b", _sequence("["))
    assert event is not None
    assert event.key == Key.ESCAPE


def test_unknown_escape_sequence_maps_to_escape() -> None:
    event = parse_key("\x1b", _sequence("[", "Z"))
    assert event is not None
    assert event.key == Key.ESCAPE


def test_delete_backspace_byte_maps_correctly() -> None:
    assert parse_key("\x7f") is not None and parse_key("\x7f").key == Key.BACKSPACE
    assert parse_key("\x08") is not None and parse_key("\x08").key == Key.BACKSPACE


def test_printable_characters_are_preserved() -> None:
    for char in ("a", "Z", "5", "!", "@", "~"):
        event = parse_key(char)
        assert event is not None
        assert event.key == Key.CHAR
        assert event.char == char


def test_tab_and_space_map_correctly() -> None:
    assert parse_key("\t") is not None and parse_key("\t").key == Key.TAB
    assert parse_key(" ") is not None and parse_key(" ").key == Key.SPACE


def test_ctrl_c_maps_correctly() -> None:
    event = parse_key("\x03")
    assert event is not None
    assert event.key == Key.CTRL_C
    assert event.ctrl is True


def test_ctrl_d_maps_correctly() -> None:
    event = parse_key("\x04")
    assert event is not None
    assert event.key == Key.CTRL_D
    assert event.ctrl is True


def test_empty_input_maps_to_ctrl_d() -> None:
    """End of stream is reported as Ctrl+D so callers exit gracefully."""
    event = parse_key("")
    assert event is not None
    assert event.key == Key.CTRL_D


def test_key_event_str_formatting() -> None:
    assert str(KeyEvent(key=Key.ENTER)) == "ENTER"
    assert str(KeyEvent(key=Key.CTRL_C, ctrl=True)) == "Ctrl+CTRL_C"
    assert str(KeyEvent(key=Key.CHAR, char="x")) == "X"


def test_windows_arrow_prefix_maps_correctly() -> None:
    from otpilot.infrastructure.terminal.keyboard import _parse_key_windows

    prefix = "\xe0"  # b"\xe0" decoded as latin-1, as msvcrt.getwch would yield
    assert _parse_key_windows(prefix, _sequence("H")).key == Key.UP
    assert _parse_key_windows(prefix, _sequence("P")).key == Key.DOWN
    assert _parse_key_windows(prefix, _sequence("M")).key == Key.RIGHT
    assert _parse_key_windows(prefix, _sequence("K")).key == Key.LEFT
    assert _parse_key_windows(prefix, _sequence("S")).key == Key.BACKSPACE


def test_windows_carriage_return_and_escape_map_correctly() -> None:
    from otpilot.infrastructure.terminal.keyboard import _parse_key_windows

    assert _parse_key_windows("\r", _sequence()).key == Key.ENTER
    assert _parse_key_windows("\x1b", _sequence()).key == Key.ESCAPE


def test_utf8_expected_length_helper() -> None:
    from otpilot.infrastructure.terminal.keyboard import _utf8_expected_length

    assert _utf8_expected_length(ord("a")) == 1
    assert _utf8_expected_length(0xC3) == 2
    assert _utf8_expected_length(0xE2) == 3
    assert _utf8_expected_length(0xF0) == 4
