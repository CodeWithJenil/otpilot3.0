"""Windows global-hotkey adapter backed by :mod:`pynput`."""

import sys
from collections.abc import Callable
from contextlib import suppress
from typing import Any

from otpilot.domain.errors import BackgroundServiceError


class PynputHotkeyListener:
    """Register one system-wide Windows hotkey without exposing pynput types."""

    def __init__(self) -> None:
        self._listener: Any | None = None

    def register(self, hotkey: str, callback: Callable[[], None]) -> None:
        if sys.platform != "win32":
            raise BackgroundServiceError("Global hotkeys are currently supported only on Windows.")
        if self._listener is not None:
            raise BackgroundServiceError("A global hotkey is already registered.")
        try:
            from pynput.keyboard import GlobalHotKeys  # type: ignore[import-untyped]
        except ModuleNotFoundError as exc:
            raise BackgroundServiceError("Windows global-hotkey support is unavailable.") from exc
        listener: Any | None = None
        try:
            listener = GlobalHotKeys({self._to_pynput_syntax(hotkey): callback})
            listener.start()
            self._listener = listener
        except Exception as exc:
            if listener is not None:
                with suppress(Exception):
                    listener.stop()
            raise BackgroundServiceError(
                "Unable to register the configured global hotkey."
            ) from exc

    def run(self) -> None:
        if self._listener is None:
            raise BackgroundServiceError("No global hotkey is registered.")
        try:
            self._listener.join()
        except KeyboardInterrupt:
            return
        except Exception as exc:
            raise BackgroundServiceError(
                "The global hotkey listener stopped unexpectedly."
            ) from exc

    def shutdown(self) -> None:
        listener, self._listener = self._listener, None
        if listener is None:
            return
        try:
            listener.stop()
            listener.join()
        except Exception as exc:
            raise BackgroundServiceError("Unable to unregister the global hotkey.") from exc

    @staticmethod
    def _to_pynput_syntax(hotkey: str) -> str:
        modifiers = {"ctrl": "<ctrl>", "shift": "<shift>", "alt": "<alt>", "win": "<cmd>"}
        parts = hotkey.split("+")
        return "+".join([*(modifiers[part] for part in parts[:-1]), parts[-1]])
