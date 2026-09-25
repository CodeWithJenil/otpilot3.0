"""Platform detection helpers used by hotkeys and diagnostics."""

from __future__ import annotations

import os
import platform
import sys
from dataclasses import dataclass

from otpilot import __version__

SUPPORTED_HOTKEY_PLATFORMS = {"win32", "darwin", "linux"}


@dataclass(frozen=True, slots=True)
class EnvironmentInfo:
    python_version: str
    python_compatible: bool
    system: str
    release: str
    machine: str
    otpilot_version: str
    platform_name: str


def python_supported(minimum: tuple[int, int] = (3, 12)) -> bool:
    return sys.version_info[:2] >= minimum


def is_wayland_without_x11() -> bool:
    return sys.platform.startswith("linux") and os.environ.get(
        "XDG_SESSION_TYPE", ""
    ).lower() == "wayland" and not os.environ.get("DISPLAY")


def macos_accessibility_trusted() -> bool | None:
    if sys.platform != "darwin":
        return None
    try:
        import ctypes
        import ctypes.util

        library_name = ctypes.util.find_library("ApplicationServices")
        if library_name is None:
            return None
        library = ctypes.cdll.LoadLibrary(library_name)
        library.AXIsProcessTrusted.restype = ctypes.c_bool
        return bool(library.AXIsProcessTrusted())
    except Exception:
        return None


def environment_info() -> EnvironmentInfo:
    system = platform.system() or sys.platform
    return EnvironmentInfo(
        python_version=platform.python_version(),
        python_compatible=python_supported(),
        system=system,
        release=platform.release(),
        machine=platform.machine(),
        otpilot_version=__version__,
        platform_name=sys.platform,
    )
