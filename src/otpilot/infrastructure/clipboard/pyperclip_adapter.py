"""System clipboard adapter backed by pyperclip."""

import pyperclip  # type: ignore[import-untyped]

from otpilot.domain.errors import ClipboardError


class PyperclipClipboard:
    def copy(self, value: str) -> None:
        try:
            pyperclip.copy(value)
        except Exception as exc:
            raise ClipboardError("Unable to copy the OTP to the clipboard.") from exc
