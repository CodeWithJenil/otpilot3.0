"""System clipboard adapter backed by pyperclip."""

import pyperclip  # type: ignore[import-untyped]

from otpilot.domain.errors import ClipboardError


def clipboard_backend_available() -> str:
    """Return a backend identifier without writing to the clipboard."""
    try:
        copy_fn, _paste_fn = pyperclip.determine_clipboard()
    except Exception as exc:
        raise ClipboardError("Clipboard support is unavailable.") from exc
    name = getattr(copy_fn, "__module__", None) or getattr(copy_fn, "__name__", None)
    return str(name or "pyperclip")


class PyperclipClipboard:
    def copy(self, value: str) -> None:
        try:
            pyperclip.copy(value)
        except Exception as exc:
            raise ClipboardError("Unable to copy the OTP to the clipboard.") from exc
