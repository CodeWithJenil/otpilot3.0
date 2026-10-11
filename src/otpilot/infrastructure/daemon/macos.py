"""macOS daemon manager using launchd LaunchAgent."""

from __future__ import annotations

import os
import plistlib
import subprocess
import sys
import time
from pathlib import Path

from otpilot.application.ports import DaemonManager, DaemonStatus
from otpilot.domain.errors import OTPilotError
from otpilot.infrastructure.platform.environment import environment_info


class MacOSDaemonManager(DaemonManager):
    """Daemon manager for macOS using per-user launchd LaunchAgent."""

    LABEL = "com.jenil.otpilot"
    PLIST_NAME = f"{LABEL}.plist"

    def __init__(self) -> None:
        self._info = environment_info()
        self._launch_agents_dir = Path.home() / "Library" / "LaunchAgents"
        self._plist_path = self._launch_agents_dir / self.PLIST_NAME
        self._log_dir = Path.home() / "Library" / "Logs" / "otpilot"
        self._stdout_log = self._log_dir / "daemon.out.log"
        self._stderr_log = self._log_dir / "daemon.err.log"

    def _get_python_executable(self) -> str:
        """Get the Python executable path, handling virtual environments."""
        return sys.executable

    def _get_working_directory(self) -> str:
        """Get the working directory for the daemon."""
        return str(Path.home())

    def _build_plist(self) -> dict:
        """Build the LaunchAgent plist dictionary."""
        python_exe = self._get_python_executable()
        working_dir = self._get_working_directory()

        self._log_dir.mkdir(parents=True, exist_ok=True)

        return {
            "Label": self.LABEL,
            "ProgramArguments": [
                python_exe,
                "-m",
                "otpilot.cli.app",
                "daemon",
                "run-internal",
            ],
            "WorkingDirectory": working_dir,
            "RunAtLoad": False,
            "KeepAlive": {
                "SuccessfulExit": False,
                "Crashed": True,
            },
            "StandardOutPath": str(self._stdout_log),
            "StandardErrorPath": str(self._stderr_log),
            "EnvironmentVariables": {
                "PATH": os.environ.get("PATH", "/usr/bin:/bin:/usr/sbin:/sbin"),
                "HOME": str(Path.home()),
            },
            "ProcessType": "Interactive",
        }

    def _write_plist(self) -> None:
        """Write the plist file."""
        self._launch_agents_dir.mkdir(parents=True, exist_ok=True)
        plist_data = self._build_plist()
        with open(self._plist_path, "wb") as f:
            plistlib.dump(plist_data, f)

    def _load_plist(self) -> None:
        """Load the LaunchAgent."""
        subprocess.run(
            ["launchctl", "bootstrap", f"gui/{os.getuid()}", str(self._plist_path)],
            capture_output=True,
            check=False,
            timeout=10,
        )

    def _unload_plist(self) -> None:
        """Unload the LaunchAgent."""
        subprocess.run(
            ["launchctl", "bootout", f"gui/{os.getuid()}", str(self._plist_path)],
            capture_output=True,
            check=False,
            timeout=10,
        )

    def _get_pid_from_launchctl(self) -> int | None:
        """Get the PID of the running service from launchctl."""
        try:
            result = subprocess.run(
                ["launchctl", "list", self.LABEL],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                return None
            # Parse output: PID is the first field
            for line in result.stdout.strip().split("\n"):
                if line and not line.startswith("PID"):
                    parts = line.split()
                    if parts:
                        try:
                            pid = int(parts[0])
                            if pid > 0:
                                return pid
                        except ValueError:
                            pass
        except (subprocess.SubprocessError, OSError, TimeoutError):
            pass
        return None

    def _is_process_running(self, pid: int) -> bool:
        """Check if a process with the given PID is running."""
        try:
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False

    def install(self, autostart: bool = False) -> None:
        """Install the daemon (create and load LaunchAgent)."""
        self._write_plist()
        if autostart:
            # RunAtLoad is set in plist, but we also enable it for the current session
            self._load_plist()

    def uninstall(self) -> None:
        """Uninstall the daemon."""
        self.stop()
        try:
            self._plist_path.unlink(missing_ok=True)
        except OSError:
            pass

    def start(self) -> None:
        """Start the daemon."""
        if self.is_running():
            return

        if not self.is_installed():
            self.install()

        self._load_plist()
        # Give launchd a moment to start the process
        time.sleep(0.5)

    def stop(self) -> None:
        """Stop the daemon."""
        self._unload_plist()
        time.sleep(0.2)

    def restart(self) -> None:
        """Restart the daemon."""
        self.stop()
        time.sleep(0.5)
        self.start()

    def status(self) -> DaemonStatus:
        """Return the current daemon status."""
        pid = self._get_pid_from_launchctl()
        running = pid is not None and self._is_process_running(pid)
        autostart = self._is_autostart_enabled()

        return DaemonStatus(
            installed=self.is_installed(),
            running=running,
            pid=pid if running else None,
            autostart_enabled=autostart,
        )

    def is_installed(self) -> bool:
        """Check if the daemon is installed (plist exists)."""
        return self._plist_path.exists()

    def is_running(self) -> bool:
        """Check if the daemon process is currently running."""
        pid = self._get_pid_from_launchctl()
        return pid is not None and self._is_process_running(pid)

    def _is_autostart_enabled(self) -> bool:
        """Check if autostart is enabled (LaunchAgent loaded for user)."""
        try:
            result = subprocess.run(
                ["launchctl", "print", f"gui/{os.getuid()}"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return self.LABEL in result.stdout
        except (subprocess.SubprocessError, OSError, TimeoutError):
            return False

    def enable_autostart(self) -> None:
        """Enable autostart (load LaunchAgent for current user session)."""
        if not self.is_installed():
            self.install(autostart=True)
        else:
            self._load_plist()

    def disable_autostart(self) -> None:
        """Disable autostart (unload LaunchAgent)."""
        self._unload_plist()