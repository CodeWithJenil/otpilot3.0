"""Read-only platform probes for `otpilot doctor`."""

from __future__ import annotations

import importlib
import os
import stat
import sys
from importlib import metadata
from pathlib import Path

import keyring

from otpilot.domain.diagnostics import CheckStatus, DiagnosticCheck
from otpilot.domain.errors import ClipboardError
from otpilot.infrastructure.clipboard.pyperclip_adapter import clipboard_backend_available
from otpilot.infrastructure.platform.environment import (
    SUPPORTED_HOTKEY_PLATFORMS,
    environment_info,
    is_wayland_without_x11,
    macos_accessibility_trusted,
)

REQUIRED_DEPENDENCIES: tuple[tuple[str, str], ...] = (
    ("imapclient", "imapclient"),
    ("keyring", "keyring"),
    ("platformdirs", "platformdirs"),
    ("pydantic", "pydantic"),
    ("pynput", "pynput"),
    ("pyperclip", "pyperclip"),
    ("rich", "rich"),
    ("tomli_w", "tomli-w"),
    ("typer", "typer"),
)

_DISPLAY_NAMES = {
    "Darwin": "macOS",
    "Windows": "Windows",
    "Linux": "Linux",
}


class DefaultPlatformDiagnostics:
    def environment_checks(self) -> list[DiagnosticCheck]:
        info = environment_info()
        os_label = _DISPLAY_NAMES.get(info.system, info.system)
        python_status = CheckStatus.PASS if info.python_compatible else CheckStatus.FAIL
        python_message = f"Python version: {info.python_version}"
        python_remediation = None
        if not info.python_compatible:
            python_message += " (OTPilot requires Python 3.12 or newer)"
            python_remediation = "Install Python 3.12+ and reinstall OTPilot."
        return [
            DiagnosticCheck(
                "Environment",
                "Python",
                python_status,
                python_message,
                python_remediation,
            ),
            DiagnosticCheck(
                "Environment",
                "Operating system",
                CheckStatus.PASS,
                f"Operating system: {os_label} {info.release} ({info.machine})",
            ),
            DiagnosticCheck(
                "Environment",
                "OTPilot",
                CheckStatus.PASS,
                f"OTPilot version: {info.otpilot_version}",
            ),
        ]

    def configuration_support_checks(self, config_path: Path) -> list[DiagnosticCheck]:
        checks = [_config_directory_check(config_path.parent)]
        permission = config_permission_check(config_path)
        if permission is not None:
            checks.append(permission)
        return checks

    def keyring_check(self) -> DiagnosticCheck:
        try:
            backend = keyring.get_keyring()
        except Exception:
            return DiagnosticCheck(
                "Credentials",
                "Keyring",
                CheckStatus.FAIL,
                "Keyring backend could not be initialized.",
                "Install or unlock the operating system credential vault and retry.",
            )
        backend_name = f"{type(backend).__module__}.{type(backend).__name__}"
        if backend_name.rsplit(".", 1)[-1] == "Keyring" and "fail" in backend_name.lower():
            return DiagnosticCheck(
                "Credentials",
                "Keyring",
                CheckStatus.FAIL,
                f"Keyring fallback backend is active ({backend_name}).",
                "On Linux, start a Secret Service provider such as GNOME Keyring or KWallet.",
            )
        return DiagnosticCheck(
            "Credentials",
            "Keyring",
            CheckStatus.PASS,
            f"Keyring backend available: {backend_name}",
        )

    def clipboard_check(self) -> DiagnosticCheck:
        try:
            backend = clipboard_backend_available()
        except ClipboardError:
            return DiagnosticCheck(
                "Clipboard",
                "Backend",
                CheckStatus.WARN,
                "Clipboard backend is unavailable.",
                "Install a platform clipboard tool (for example xclip/xsel on Linux) "
                "if you need copy support.",
            )
        except Exception:
            return DiagnosticCheck(
                "Clipboard",
                "Backend",
                CheckStatus.WARN,
                "Clipboard backend could not be probed.",
            )
        return DiagnosticCheck(
            "Clipboard",
            "Backend",
            CheckStatus.PASS,
            f"Clipboard backend available ({backend}).",
        )

    def hotkey_check(self) -> DiagnosticCheck:
        if sys.platform not in SUPPORTED_HOTKEY_PLATFORMS:
            return DiagnosticCheck(
                "Hotkeys",
                "Environment",
                CheckStatus.WARN,
                f"Global hotkeys are not supported on this platform ({sys.platform}).",
                "Use `otpilot fetch` or `otpilot watch` instead of `otpilot hotkey`.",
            )
        if sys.platform == "linux" and is_wayland_without_x11():
            return DiagnosticCheck(
                "Hotkeys",
                "Environment",
                CheckStatus.WARN,
                "Wayland session detected without X11. Global hotkeys require X11 or XWayland.",
                "Switch to an X11 session, set DISPLAY, or use `otpilot fetch` / `otpilot watch`.",
            )
        if sys.platform == "linux" and not os.environ.get("DISPLAY"):
            return DiagnosticCheck(
                "Hotkeys",
                "Environment",
                CheckStatus.WARN,
                "No DISPLAY is set, so a global hotkey listener cannot attach to X11.",
                "Run OTPilot in a graphical X11 session.",
            )
        if sys.platform == "darwin":
            trusted = macos_accessibility_trusted()
            if trusted is False:
                return DiagnosticCheck(
                    "Hotkeys",
                    "Environment",
                    CheckStatus.WARN,
                    "macOS Accessibility permission is not granted for this process.",
                    "Grant Accessibility access under System Settings > "
                "Privacy & Security > Accessibility.",
                )
            if trusted is None:
                return DiagnosticCheck(
                    "Hotkeys",
                    "Environment",
                    CheckStatus.WARN,
                    "macOS Accessibility permission could not be verified.",
                    "If hotkeys do not work, grant Accessibility access to your terminal app.",
                )
        return DiagnosticCheck(
            "Hotkeys",
            "Environment",
            CheckStatus.PASS,
            "Hotkey environment looks usable. Listener was not registered.",
        )

    def dependency_checks(self) -> list[DiagnosticCheck]:
        checks: list[DiagnosticCheck] = []
        for module_name, distribution in REQUIRED_DEPENDENCIES:
            checks.append(_dependency_check(module_name, distribution))
        return checks


def _config_directory_check(directory: Path) -> DiagnosticCheck:
    if directory.exists():
        if os.access(directory, os.W_OK | os.X_OK):
            return DiagnosticCheck(
                "Configuration",
                "Directory",
                CheckStatus.PASS,
                f"Configuration directory is writable: {directory}",
            )
        return DiagnosticCheck(
            "Configuration",
            "Directory",
            CheckStatus.FAIL,
            f"Configuration directory is not writable: {directory}",
            "Fix directory permissions or set a user-writable config location.",
        )
    parent = directory.parent
    if parent.exists() and os.access(parent, os.W_OK | os.X_OK):
        return DiagnosticCheck(
            "Configuration",
            "Directory",
            CheckStatus.PASS,
            f"Configuration directory can be created: {directory}",
        )
    return DiagnosticCheck(
        "Configuration",
        "Directory",
        CheckStatus.FAIL,
        f"Configuration directory cannot be created: {directory}",
        "Ensure the user config location is writable.",
    )


def config_permission_check(path: Path) -> DiagnosticCheck | None:
    if os.name != "posix" or not path.exists():
        return None
    try:
        mode = path.stat().st_mode
    except OSError:
        return DiagnosticCheck(
            "Configuration",
            "Permissions",
            CheckStatus.WARN,
            "Configuration file permissions could not be read.",
        )
    if mode & (stat.S_IRWXG | stat.S_IRWXO):
        return DiagnosticCheck(
            "Configuration",
            "Permissions",
            CheckStatus.WARN,
            f"Configuration file is group- or world-accessible ({stat.filemode(mode)}).",
            f"Restrict permissions with: chmod 600 {path}",
        )
    return DiagnosticCheck(
        "Configuration",
        "Permissions",
        CheckStatus.PASS,
        "Configuration file permissions are restricted.",
    )


def _dependency_check(module_name: str, distribution: str) -> DiagnosticCheck:
    try:
        importlib.import_module(module_name)
    except Exception:
        return DiagnosticCheck(
            "Dependencies",
            distribution,
            CheckStatus.FAIL,
            f"Required dependency '{distribution}' could not be imported.",
            "Reinstall OTPilot with `pip install otpilot`.",
        )
    version = _distribution_version(distribution)
    suffix = f" {version}" if version else ""
    return DiagnosticCheck(
        "Dependencies",
        distribution,
        CheckStatus.PASS,
        f"{distribution} is importable{suffix}.",
    )


def _distribution_version(distribution: str) -> str | None:
    try:
        return metadata.version(distribution)
    except metadata.PackageNotFoundError:
        return None
