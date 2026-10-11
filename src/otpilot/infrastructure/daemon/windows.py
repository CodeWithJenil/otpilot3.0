"""Windows daemon manager using background process with PID file."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

from otpilot.application.ports import DaemonManager, DaemonStatus
from otpilot.domain.errors import OTPilotError
from otpilot.infrastructure.platform.environment import environment_info


class WindowsDaemonManager(DaemonManager):
    """Daemon manager for Windows using background process."""

    def __init__(self) -> None:
        self._info = environment_info()
        self._state_dir = self._get_state_dir()
        self._pid_file = self._state_dir / "daemon.pid"
        self._log_file = self._state_dir / "daemon.log"
        self._run_script = self._state_dir / "run_daemon.bat"

    def _get_state_dir(self) -> Path:
        """Get the platform-specific state directory."""
        local_app_data = os.environ.get("LOCALAPPDATA")
        if not local_app_data:
            local_app_data = str(Path.home() / "AppData" / "Local")
        state_dir = Path(local_app_data) / "otpilot"
        state_dir.mkdir(parents=True, exist_ok=True)
        return state_dir

    def _get_python_executable(self) -> str:
        """Get the Python executable path, handling virtual environments."""
        return sys.executable

    def _create_run_script(self) -> None:
        """Create a batch script to run the daemon."""
        python_exe = self._get_python_executable()
        # Use pythonw.exe for no console window if available
        pythonw = python_exe.replace("python.exe", "pythonw.exe")
        if not Path(pythonw).exists():
            pythonw = python_exe

        script_content = f"""@echo off
cd /d "{Path.home()}"
"{pythonw}" -m otpilot.cli.app daemon run-internal >> "{self._log_file}" 2>&1
"""
        self._run_script.write_text(script_content, encoding="utf-8")

    def _read_pid(self) -> int | None:
        """Read PID from PID file."""
        try:
            if self._pid_file.exists():
                content = self._pid_file.read_text(encoding="utf-8").strip()
                if content:
                    return int(content)
        except (ValueError, OSError):
            pass
        return None

    def _write_pid(self, pid: int) -> None:
        """Write PID to PID file."""
        self._pid_file.write_text(str(pid), encoding="utf-8")

    def _clear_pid(self) -> None:
        """Clear PID file."""
        try:
            self._pid_file.unlink(missing_ok=True)
        except OSError:
            pass

    def _is_process_running(self, pid: int) -> bool:
        """Check if a process with the given PID is running."""
        try:
            # Use tasklist to check if process exists
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return str(pid) in result.stdout
        except (subprocess.SubprocessError, OSError, TimeoutError):
            return False

    def _cleanup_stale_pid(self) -> None:
        """Remove stale PID file if process is not running or file is invalid."""
        if not self._pid_file.exists():
            return
        pid = self._read_pid()
        if pid is None or not self._is_process_running(pid):
            self._clear_pid()

    def install(self, autostart: bool = False) -> None:
        """Install the daemon (create run script and optional autostart)."""
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._create_run_script()

        if autostart:
            self._enable_autostart()

    def uninstall(self) -> None:
        """Uninstall the daemon."""
        self.stop()
        self._disable_autostart()
        try:
            self._run_script.unlink(missing_ok=True)
            self._pid_file.unlink(missing_ok=True)
            self._log_file.unlink(missing_ok=True)
        except OSError:
            pass

    def start(self) -> None:
        """Start the daemon as a background process."""
        self._cleanup_stale_pid()

        if self.is_running():
            return  # Already running

        self._create_run_script()

        # Start the process detached
        python_exe = self._get_python_executable()
        pythonw = python_exe.replace("python.exe", "pythonw.exe")
        if not Path(pythonw).exists():
            pythonw = python_exe

        try:
            # Use CREATE_NO_WINDOW flag to run without console
            creation_flags = 0x08000000  # CREATE_NO_WINDOW
            process = subprocess.Popen(
                [pythonw, "-m", "otpilot.cli.app", "daemon", "run-internal"],
                cwd=str(Path.home()),
                stdout=open(self._log_file, "a", encoding="utf-8"),
                stderr=subprocess.STDOUT,
                creationflags=creation_flags,
                start_new_session=True,
            )
            self._write_pid(process.pid)
        except (OSError, subprocess.SubprocessError) as exc:
            raise OTPilotError(f"Failed to start daemon: {exc}") from exc

    def stop(self) -> None:
        """Stop the daemon."""
        pid = self._read_pid()
        if pid is None:
            return

        try:
            # Try graceful termination first
            subprocess.run(
                ["taskkill", "/PID", str(pid)],
                capture_output=True,
                timeout=10,
            )
            # Wait a bit for graceful shutdown
            time.sleep(0.5)
            # Force kill if still running
            if self._is_process_running(pid):
                subprocess.run(
                    ["taskkill", "/F", "/PID", str(pid)],
                    capture_output=True,
                    timeout=5,
                )
        except (subprocess.SubprocessError, OSError, TimeoutError):
            pass
        finally:
            self._clear_pid()

    def restart(self) -> None:
        """Restart the daemon."""
        self.stop()
        time.sleep(0.5)
        self.start()

    def status(self) -> DaemonStatus:
        """Return the current daemon status."""
        self._cleanup_stale_pid()
        pid = self._read_pid()
        running = pid is not None and self._is_process_running(pid)
        autostart = self._is_autostart_enabled()

        return DaemonStatus(
            installed=self.is_installed(),
            running=running,
            pid=pid if running else None,
            autostart_enabled=autostart,
        )

    def is_installed(self) -> bool:
        """Check if the daemon is installed."""
        return self._run_script.exists()

    def is_running(self) -> bool:
        """Check if the daemon process is currently running."""
        self._cleanup_stale_pid()
        pid = self._read_pid()
        return pid is not None and self._is_process_running(pid)

    def _get_autostart_registry_key(self) -> str:
        """Get the registry key path for autostart."""
        return r"HKCU\Software\Microsoft\Windows\CurrentVersion\Run"

    def _get_autostart_value_name(self) -> str:
        """Get the registry value name for autostart."""
        return "OTPilotDaemon"

    def _enable_autostart(self) -> None:
        """Enable autostart via Windows Registry."""
        try:
            python_exe = self._get_python_executable()
            pythonw = python_exe.replace("python.exe", "pythonw.exe")
            if not Path(pythonw).exists():
                pythonw = python_exe

            command = f'"{pythonw}" -m otpilot.cli.app daemon run-internal'
            subprocess.run(
                [
                    "reg",
                    "add",
                    self._get_autostart_registry_key(),
                    "/v",
                    self._get_autostart_value_name(),
                    "/t",
                    "REG_SZ",
                    "/d",
                    command,
                    "/f",
                ],
                capture_output=True,
                check=True,
                timeout=5,
            )
        except (subprocess.SubprocessError, OSError, TimeoutError):
            pass  # Silently fail - autostart is optional

    def _disable_autostart(self) -> None:
        """Disable autostart via Windows Registry."""
        try:
            subprocess.run(
                [
                    "reg",
                    "delete",
                    self._get_autostart_registry_key(),
                    "/v",
                    self._get_autostart_value_name(),
                    "/f",
                ],
                capture_output=True,
                timeout=5,
            )
        except (subprocess.SubprocessError, OSError, TimeoutError):
            pass

    def _is_autostart_enabled(self) -> bool:
        """Check if autostart is enabled."""
        try:
            result = subprocess.run(
                [
                    "reg",
                    "query",
                    self._get_autostart_registry_key(),
                    "/v",
                    self._get_autostart_value_name(),
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, OSError, TimeoutError):
            return False