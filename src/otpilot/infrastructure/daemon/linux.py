"""Linux daemon manager using systemd --user with fallback to background process."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

from otpilot.application.ports import DaemonManager, DaemonStatus
from otpilot.domain.errors import OTPilotError
from otpilot.infrastructure.platform.environment import environment_info


class LinuxDaemonManager(DaemonManager):
    """Daemon manager for Linux using systemd --user with fallback."""

    SERVICE_NAME = "otpilot.service"
    FALLBACK_PID_FILE = Path.home() / ".local" / "state" / "otpilot" / "daemon.pid"
    FALLBACK_LOG_FILE = Path.home() / ".local" / "state" / "otpilot" / "daemon.log"

    def __init__(self) -> None:
        self._info = environment_info()
        self._config_dir = Path.home() / ".config" / "systemd" / "user"
        self._service_path = self._config_dir / self.SERVICE_NAME
        self._use_systemd = self._check_systemd_available()
        self._fallback_state_dir = self.FALLBACK_PID_FILE.parent

    def _check_systemd_available(self) -> bool:
        """Check if systemd --user is available and functional."""
        try:
            result = subprocess.run(
                ["systemctl", "--user", "status"],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, OSError, TimeoutError, FileNotFoundError):
            return False

    def _get_python_executable(self) -> str:
        """Get the Python executable path, handling virtual environments."""
        return sys.executable

    def _get_working_directory(self) -> str:
        """Get the working directory for the daemon."""
        return str(Path.home())

    def _build_service_content(self) -> str:
        """Build the systemd service unit content."""
        python_exe = self._get_python_executable()
        working_dir = self._get_working_directory()

        self._fallback_state_dir.mkdir(parents=True, exist_ok=True)

        return f"""[Unit]
Description=OTPilot OTP Daemon
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart={python_exe} -m otpilot.cli.app daemon run-internal
WorkingDirectory={working_dir}
Restart=on-failure
RestartSec=5
StandardOutput=append:{self.FALLBACK_LOG_FILE}
StandardError=append:{self.FALLBACK_LOG_FILE}
Environment=PATH={os.environ.get('PATH', '/usr/bin:/bin:/usr/sbin:/sbin')}
Environment=HOME={Path.home()}

[Install]
WantedBy=default.target
"""

    def _write_service(self) -> None:
        """Write the systemd service file."""
        self._config_dir.mkdir(parents=True, exist_ok=True)
        content = self._build_service_content()
        self._service_path.write_text(content, encoding="utf-8")

    def _systemctl_user(self, *args: str) -> subprocess.CompletedProcess:
        """Run systemctl --user command."""
        return subprocess.run(
            ["systemctl", "--user", *args],
            capture_output=True,
            text=True,
            timeout=10,
        )

    def _get_pid_systemd(self) -> int | None:
        """Get PID from systemd."""
        try:
            result = self._systemctl_user("show", self.SERVICE_NAME, "--property=MainPID")
            if result.returncode != 0:
                return None
            for line in result.stdout.strip().split("\n"):
                if line.startswith("MainPID="):
                    pid = int(line.split("=", 1)[1])
                    return pid if pid > 0 else None
        except (subprocess.SubprocessError, OSError, TimeoutError, ValueError):
            pass
        return None

    def _get_pid_fallback(self) -> int | None:
        """Get PID from fallback PID file."""
        try:
            if self.FALLBACK_PID_FILE.exists():
                content = self.FALLBACK_PID_FILE.read_text(encoding="utf-8").strip()
                if content:
                    return int(content)
        except (ValueError, OSError):
            pass
        return None

    def _write_pid_fallback(self, pid: int) -> None:
        """Write PID to fallback PID file."""
        self._fallback_state_dir.mkdir(parents=True, exist_ok=True)
        self.FALLBACK_PID_FILE.write_text(str(pid), encoding="utf-8")

    def _clear_pid_fallback(self) -> None:
        """Clear fallback PID file."""
        try:
            self.FALLBACK_PID_FILE.unlink(missing_ok=True)
        except OSError:
            pass

    def _is_process_running(self, pid: int) -> bool:
        """Check if a process with the given PID is running."""
        try:
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False

    def _cleanup_stale_fallback_pid(self) -> None:
        """Remove stale fallback PID file if process is not running or file is invalid."""
        if not self.FALLBACK_PID_FILE.exists():
            return
        pid = self._get_pid_fallback()
        if pid is None or not self._is_process_running(pid):
            self._clear_pid_fallback()

    def install(self, autostart: bool = False) -> None:
        """Install the daemon."""
        if self._use_systemd:
            self._write_service()
            self._systemctl_user("daemon-reload")
            if autostart:
                self._systemctl_user("enable", self.SERVICE_NAME)
        else:
            self._fallback_state_dir.mkdir(parents=True, exist_ok=True)
            # For fallback, autostart is not reliably supported without systemd
            # User can add to their shell profile or use crontab @reboot if desired

    def uninstall(self) -> None:
        """Uninstall the daemon."""
        self.stop()
        if self._use_systemd:
            self._systemctl_user("disable", self.SERVICE_NAME)
            try:
                self._service_path.unlink(missing_ok=True)
                self._systemctl_user("daemon-reload")
            except OSError:
                pass
        else:
            self._clear_pid_fallback()
            try:
                self.FALLBACK_LOG_FILE.unlink(missing_ok=True)
            except OSError:
                pass

    def start(self) -> None:
        """Start the daemon."""
        if self.is_running():
            return

        if self._use_systemd:
            if not self.is_installed():
                self.install()
            result = self._systemctl_user("start", self.SERVICE_NAME)
            if result.returncode != 0:
                raise OTPilotError(f"Failed to start daemon: {result.stderr.strip()}")
            time.sleep(0.5)
        else:
            self._cleanup_stale_fallback_pid()
            if self.is_running():
                return

            python_exe = self._get_python_executable()
            self._fallback_state_dir.mkdir(parents=True, exist_ok=True)

            try:
                process = subprocess.Popen(
                    [python_exe, "-m", "otpilot.cli.app", "daemon", "run-internal"],
                    cwd=str(Path.home()),
                    stdout=open(self.FALLBACK_LOG_FILE, "a", encoding="utf-8"),
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
                self._write_pid_fallback(process.pid)
            except (OSError, subprocess.SubprocessError) as exc:
                raise OTPilotError(f"Failed to start daemon: {exc}") from exc

    def stop(self) -> None:
        """Stop the daemon."""
        if self._use_systemd:
            self._systemctl_user("stop", self.SERVICE_NAME)
            time.sleep(0.2)
        else:
            pid = self._get_pid_fallback()
            if pid is None:
                return
            try:
                os.kill(pid, 15)  # SIGTERM
                time.sleep(0.5)
                if self._is_process_running(pid):
                    os.kill(pid, 9)  # SIGKILL
            except (OSError, ProcessLookupError):
                pass
            finally:
                self._clear_pid_fallback()

    def restart(self) -> None:
        """Restart the daemon."""
        self.stop()
        time.sleep(0.5)
        self.start()

    def status(self) -> DaemonStatus:
        """Return the current daemon status."""
        if self._use_systemd:
            pid = self._get_pid_systemd()
            running = pid is not None and self._is_process_running(pid)
            autostart = self._is_autostart_enabled_systemd()
        else:
            self._cleanup_stale_fallback_pid()
            pid = self._get_pid_fallback()
            running = pid is not None and self._is_process_running(pid)
            autostart = False  # Fallback doesn't support reliable autostart

        return DaemonStatus(
            installed=self.is_installed(),
            running=running,
            pid=pid if running else None,
            autostart_enabled=autostart,
        )

    def is_installed(self) -> bool:
        """Check if the daemon is installed."""
        if self._use_systemd:
            return self._service_path.exists()
        return self._fallback_state_dir.exists()

    def is_running(self) -> bool:
        """Check if the daemon process is currently running."""
        if self._use_systemd:
            pid = self._get_pid_systemd()
        else:
            self._cleanup_stale_fallback_pid()
            pid = self._get_pid_fallback()
        return pid is not None and self._is_process_running(pid)

    def _is_autostart_enabled_systemd(self) -> bool:
        """Check if systemd service is enabled."""
        try:
            result = self._systemctl_user("is-enabled", self.SERVICE_NAME)
            return result.returncode == 0 and "enabled" in result.stdout
        except (subprocess.SubprocessError, OSError, TimeoutError):
            return False

    def enable_autostart(self) -> None:
        """Enable autostart."""
        if self._use_systemd:
            if not self.is_installed():
                self.install(autostart=True)
            else:
                self._systemctl_user("enable", self.SERVICE_NAME)
        else:
            # Fallback: print instructions for manual setup
            pass

    def disable_autostart(self) -> None:
        """Disable autostart."""
        if self._use_systemd:
            self._systemctl_user("disable", self.SERVICE_NAME)
        else:
            pass