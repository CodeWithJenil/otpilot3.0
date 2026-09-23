"""Cross-platform global-hotkey adapter backed by :mod:`pynput`.

Supports Windows, macOS, and Linux X11. Wayland is not supported because
``pynput`` requires X11 input hooks. The adapter detects Wayland at
registration time and raises a clear error.
"""

import os
import sys
from collections.abc import Callable
from contextlib import suppress
from typing import Any

from otpilot.domain.errors import BackgroundServiceError

_SUPPORTED_PLATFORMS = {"win32", "darwin", "linux"}


def _is_wayland() -> bool:
    return os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland" and not os.environ.get(
        "DISPLAY"
    )


class PynputHotkeyListener:
    """Register one system-wide hotkey without exposing pynput types.

    Supported platforms:
    - Windows (all versions supported by pynput)
    - macOS (requires Accessibility permissions in System Settings)
    - Linux X11 (requires an active X display)

    Not supported:
    - Linux Wayland without XWayland (pynput needs X11 input hooks)
    """

    def __init__(self) -> None:
        self._listener: Any | None = None

    def register(self, hotkey: str, callback: Callable[[], None]) -> None:
        if sys.platform not in _SUPPORTED_PLATFORMS:
            raise BackgroundServiceError(
                f"Global hotkeys are not supported on this platform ({sys.platform})."
            )
        if sys.platform == "linux" and _is_wayland():
            raise BackgroundServiceError(
                "Global hotkeys require X11. Wayland is not supported by the"
                " underlying pynput library. Set DISPLAY or use X11/XWayland."
            )
        if self._listener is not None:
            raise BackgroundServiceError("A global hotkey is already registered.")
        try:
            from pynput.keyboard import GlobalHotKeys  # type: ignore[import-untyped]
        except ModuleNotFoundError as exc:
            raise BackgroundServiceError("Global-hotkey support is unavailable.") from exc
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
        modifiers = {
            "ctrl": "<ctrl>",
            "shift": "<shift>",
            "alt": "<alt>",
            "win": "<cmd>",
            "cmd": "<cmd>",
        }
        parts = hotkey.split("+")
        return "+".join([*(modifiers[part] for part in parts[:-1]), parts[-1]])
