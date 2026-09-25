"""Platform detection adapters."""

from otpilot.infrastructure.platform.environment import (
    environment_info,
    is_wayland_without_x11,
    macos_accessibility_trusted,
)

__all__ = ["environment_info", "is_wayland_without_x11", "macos_accessibility_trusted"]
