"""Daemon platform adapter factory."""

from __future__ import annotations

import sys

from otpilot.application.ports import DaemonManager
from otpilot.domain.errors import OTPilotError


def create_daemon_manager() -> DaemonManager:
    """Create the platform-appropriate daemon manager."""
    if sys.platform == "win32":
        from otpilot.infrastructure.daemon.windows import WindowsDaemonManager
        return WindowsDaemonManager()
    elif sys.platform == "darwin":
        from otpilot.infrastructure.daemon.macos import MacOSDaemonManager
        return MacOSDaemonManager()
    elif sys.platform.startswith("linux"):
        from otpilot.infrastructure.daemon.linux import LinuxDaemonManager
        return LinuxDaemonManager()
    else:
        raise OTPilotError(f"Unsupported platform for daemon: {sys.platform}")