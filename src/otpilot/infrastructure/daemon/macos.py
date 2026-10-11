"""macOS daemon manager using launchd LaunchAgent."""

from __future__ import annotations

import os
import plistlib
import re
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
        self._pid_file = self._log_dir / "daemon.pid"

    def _get_python_executable(self) -> str:
        """Get the Python executable path, handling virtual environments."""
        return sys.executable

    def _get_working_directory(self) -> str:
        """Get the working directory for the daemon."""
        return str(Path.home())

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
        try:
            self._pid_file.parent.mkdir(parents=True, exist_ok=True)
            self._pid_file.write_text(str(pid), encoding="utf-8")
        except OSError:
            pass

    def _clear_pid(self) -> None:
        """Clear PID file."""
        try:
            self._pid_file.unlink(missing_ok=True)
        except OSError:
            pass

    def _cleanup_stale_pid(self) -> None:
        """Remove stale or invalid PID file if process is not running."""
        if not self._pid_file.exists():
            return
        pid = self._read_pid()
        if pid is None or not self._is_process_running(pid):
            self._clear_pid()

    def _build_plist(self, autostart: bool = False) -> dict:
        """Build the LaunchAgent plist dictionary."""
        python_exe = self._get_python_executable()
        working_dir = self._get_working_directory()

        self._log_dir.mkdir(parents=True, exist_ok=True)

        env = {
            "HOME": str(Path.home()),
            "PATH": f"{str(Path(python_exe).parent)}:/usr/bin:/bin:/usr/sbin:/sbin",
            "LANG": "en_US.UTF-8",
        }
        if "PYTHONPATH" in os.environ:
            env["PYTHONPATH"] = os.environ["PYTHONPATH"]

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
            "RunAtLoad": autostart,
            "KeepAlive": {
                "SuccessfulExit": False,
                "Crashed": True,
            },
            "StandardOutPath": str(self._stdout_log),
            "StandardErrorPath": str(self._stderr_log),
            "EnvironmentVariables": env,
            "ProcessType": "Interactive",
        }

    def _write_plist(self, autostart: bool = False) -> None:
        """Write the plist file."""
        self._launch_agents_dir.mkdir(parents=True, exist_ok=True)
        plist_data = self._build_plist(autostart=autostart)
        with open(self._plist_path, "wb") as f:
            plistlib.dump(plist_data, f)

    def _is_loaded_in_launchd(self) -> bool:
        """Check if the service is registered with launchd."""
        try:
            result = subprocess.run(
                ["launchctl", "list", self.LABEL],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, OSError, TimeoutError):
            return False

    def _load_plist(self) -> bool:
        """Load the LaunchAgent into launchd."""
        try:
            result = subprocess.run(
                ["launchctl", "bootstrap", f"gui/{os.getuid()}", str(self._plist_path)],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, OSError, TimeoutError):
            return False

    def _unload_plist(self) -> bool:
        """Unload the LaunchAgent from launchd."""
        try:
            result = subprocess.run(
                ["launchctl", "bootout", f"gui/{os.getuid()}", str(self._plist_path)],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, OSError, TimeoutError):
            return False

    def _get_pid_from_launchctl(self) -> int | None:
        """Get the PID of the running service from launchctl."""
        try:
            result = subprocess.run(
                ["launchctl", "list", self.LABEL],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                match = re.search(r'"PID"\s*=\s*(\d+);', result.stdout)
                if match:
                    pid = int(match.group(1))
                    if pid > 0:
                        return pid
        except (subprocess.SubprocessError, OSError, TimeoutError):
            pass

        # Fallback: check launchctl list table output
        try:
            result = subprocess.run(
                ["launchctl", "list"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                for line in result.stdout.strip().splitlines():
                    parts = line.split()
                    if len(parts) >= 3 and parts[2] == self.LABEL:
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
        if pid <= 0:
            return False
        try:
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False

    def install(self, autostart: bool = False) -> None:
        """Install the daemon (create LaunchAgent)."""
        self._write_plist(autostart=autostart)
        if autostart:
            if not self._is_loaded_in_launchd():
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
        self._cleanup_stale_pid()
        if self.is_running():
            return

        if not self.is_installed():
            self.install()

        # Ensure service is registered with launchd
        if not self._is_loaded_in_launchd():
            self._load_plist()

        # Start or kickstart the service
        result = subprocess.run(
            ["launchctl", "kickstart", "-p", f"gui/{os.getuid()}/{self.LABEL}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            # If kickstart failed, try reloading the plist once
            self._unload_plist()
            self._load_plist()
            result = subprocess.run(
                ["launchctl", "kickstart", "-p", f"gui/{os.getuid()}/{self.LABEL}"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                raise OTPilotError(
                    f"Failed to start daemon via launchctl: {result.stderr.strip() or result.stdout.strip()}"
                )

        # Verify daemon is running
        start_time = time.time()
        timeout = 3.0
        while time.time() - start_time < timeout:
            if self.is_running():
                pid = self._get_pid_from_launchctl()
                if pid:
                    self._write_pid(pid)
                return
            time.sleep(0.2)

        # Startup verification failed - inspect error log if present
        err_msg = ""
        if self._stderr_log.exists():
            try:
                content = self._stderr_log.read_text(encoding="utf-8").strip()
                if content:
                    err_lines = content.splitlines()[-5:]
                    err_msg = ": " + " ".join(err_lines)
            except OSError:
                pass

        raise OTPilotError(f"Daemon process failed to start or exited immediately{err_msg}")

    def stop(self) -> None:
        """Stop the daemon."""
        pid = self._get_pid_from_launchctl() or self._read_pid()
        self._unload_plist()

        if pid:
            start_time = time.time()
            while time.time() - start_time < 2.0:
                if not self._is_process_running(pid):
                    break
                time.sleep(0.1)
            else:
                try:
                    os.kill(pid, 9)
                except (OSError, ProcessLookupError):
                    pass

        self._clear_pid()

    def restart(self) -> None:
        """Restart the daemon."""
        self.stop()
        time.sleep(0.5)
        self.start()

    def status(self) -> DaemonStatus:
        """Return the current daemon status."""
        self._cleanup_stale_pid()
        pid = self._get_pid_from_launchctl()
        if pid is None:
            pid = self._read_pid()

        running = pid is not None and self._is_process_running(pid)
        autostart = self._is_autostart_enabled()
        state = "running" if running else "stopped"

        return DaemonStatus(
            installed=self.is_installed(),
            running=running,
            pid=pid if running else None,
            autostart_enabled=autostart,
            state=state,
        )

    def is_installed(self) -> bool:
        """Check if the daemon is installed (plist exists)."""
        return self._plist_path.exists()

    def is_running(self) -> bool:
        """Check if the daemon process is currently running."""
        self._cleanup_stale_pid()
        pid = self._get_pid_from_launchctl()
        if pid is None:
            pid = self._read_pid()
        return pid is not None and self._is_process_running(pid)

    def _is_autostart_enabled(self) -> bool:
        """Check if autostart is enabled (RunAtLoad is True in plist)."""
        if not self._plist_path.exists():
            return False
        try:
            with open(self._plist_path, "rb") as f:
                data = plistlib.load(f)
            return bool(data.get("RunAtLoad", False))
        except Exception:
            return False

    def enable_autostart(self) -> None:
        """Enable autostart (update plist with RunAtLoad=True)."""
        self._write_plist(autostart=True)
        if not self._is_loaded_in_launchd():
            self._load_plist()

    def disable_autostart(self) -> None:
        """Disable autostart (update plist with RunAtLoad=False)."""
        self._write_plist(autostart=False)