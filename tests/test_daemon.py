"""Tests for the daemon module."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from otpilot.application.ports import DaemonStatus
from otpilot.cli.commands import daemon as daemon_commands
from otpilot.domain.errors import OTPilotError


class TestDaemonCommands:
    """Tests for daemon CLI commands."""

    def test_run_internal_imports(self) -> None:
        """Test that run_internal can be imported."""
        from otpilot.cli.commands.daemon import run_internal
        assert callable(run_internal)

    def test_status_command_running(self, monkeypatch) -> None:
        """Test status command when daemon is running."""
        from typer.testing import CliRunner
        runner = CliRunner()

        mock_mgr = MagicMock()
        mock_mgr.status.return_value = DaemonStatus(
            installed=True,
            running=True,
            pid=5555,
            autostart_enabled=True,
        )
        monkeypatch.setattr(daemon_commands, "_get_daemon_manager", lambda: mock_mgr)

        result = runner.invoke(daemon_commands.app, ["status"])
        assert result.exit_code == 0
        assert "Installed: Yes" in result.output
        assert "Running:   Yes" in result.output
        assert "PID:       5555" in result.output
        assert "Autostart: Enabled" in result.output

    def test_status_command_stopped(self, monkeypatch) -> None:
        """Test status command when daemon is stopped."""
        from typer.testing import CliRunner
        runner = CliRunner()

        mock_mgr = MagicMock()
        mock_mgr.status.return_value = DaemonStatus(
            installed=True,
            running=False,
            pid=None,
            autostart_enabled=False,
        )
        monkeypatch.setattr(daemon_commands, "_get_daemon_manager", lambda: mock_mgr)

        result = runner.invoke(daemon_commands.app, ["status"])
        assert result.exit_code == 0
        assert "Installed: Yes" in result.output
        assert "Running:   No" in result.output
        assert "PID:" not in result.output
        assert "Autostart: Disabled" in result.output

    def test_start_command_success(self, monkeypatch) -> None:
        """Test start command success."""
        from typer.testing import CliRunner
        runner = CliRunner()

        mock_mgr = MagicMock()
        monkeypatch.setattr(daemon_commands, "_get_daemon_manager", lambda: mock_mgr)

        result = runner.invoke(daemon_commands.app, ["start"])
        assert result.exit_code == 0
        assert "Daemon started." in result.output
        mock_mgr.start.assert_called_once()

    def test_start_command_failure(self, monkeypatch) -> None:
        """Test start command failure reports error and exits non-zero."""
        from typer.testing import CliRunner
        runner = CliRunner()

        mock_mgr = MagicMock()
        mock_mgr.start.side_effect = OTPilotError("Process died immediately")
        monkeypatch.setattr(daemon_commands, "_get_daemon_manager", lambda: mock_mgr)

        result = runner.invoke(daemon_commands.app, ["start"])
        assert result.exit_code == 1
        assert "Process died immediately" in result.output

    def test_stop_command_success(self, monkeypatch) -> None:
        """Test stop command success."""
        from typer.testing import CliRunner
        runner = CliRunner()

        mock_mgr = MagicMock()
        monkeypatch.setattr(daemon_commands, "_get_daemon_manager", lambda: mock_mgr)

        result = runner.invoke(daemon_commands.app, ["stop"])
        assert result.exit_code == 0
        assert "Daemon stopped." in result.output
        mock_mgr.stop.assert_called_once()


class TestWindowsDaemonManager:
    """Tests for WindowsDaemonManager (mocked)."""

    @pytest.fixture
    def mock_manager(self, tmp_path, monkeypatch):
        """Create a mocked WindowsDaemonManager."""
        # Mock platform detection
        monkeypatch.setattr(sys, "platform", "win32")

        from otpilot.infrastructure.daemon.windows import WindowsDaemonManager

        manager = WindowsDaemonManager()
        manager._state_dir = tmp_path
        manager._pid_file = tmp_path / "daemon.pid"
        manager._log_file = tmp_path / "daemon.log"
        manager._run_script = tmp_path / "run_daemon.bat"

        return manager

    def test_pid_file_operations(self, mock_manager):
        """Test PID file read/write/clear operations."""
        # Initially no PID
        assert mock_manager._read_pid() is None

        # Write PID
        mock_manager._write_pid(1234)
        assert mock_manager._read_pid() == 1234

        # Clear PID
        mock_manager._clear_pid()
        assert mock_manager._read_pid() is None

    def test_is_process_running_mock(self, mock_manager, monkeypatch):
        """Test process running check with mocked tasklist."""
        def mock_run(*args, **kwargs):
            result = MagicMock()
            cmd_str = " ".join(args[0]) if args else ""
            if "1234" in cmd_str:
                result.stdout = "python.exe                   1234 Console                    1     10,000 K"
            else:
                result.stdout = ""
            return result

        monkeypatch.setattr("subprocess.run", mock_run)

        assert mock_manager._is_process_running(1234) is True
        assert mock_manager._is_process_running(9999) is False

    def test_cleanup_stale_or_invalid_pid(self, mock_manager, monkeypatch):
        """Test cleaning up stale or corrupt PID files on Windows."""
        # Non-running stale PID
        mock_manager._write_pid(9999)
        monkeypatch.setattr(mock_manager, "_is_process_running", lambda pid: False)
        mock_manager._cleanup_stale_pid()
        assert not mock_manager._pid_file.exists()

        # Running valid PID
        mock_manager._write_pid(1234)
        monkeypatch.setattr(mock_manager, "_is_process_running", lambda pid: True)
        mock_manager._cleanup_stale_pid()
        assert mock_manager._pid_file.exists()

        # Corrupt / non-numeric PID file
        mock_manager._pid_file.write_text("invalid_pid", encoding="utf-8")
        mock_manager._cleanup_stale_pid()
        assert not mock_manager._pid_file.exists()


class TestMacOSDaemonManager:
    """Tests for MacOSDaemonManager (mocked)."""

    @pytest.fixture
    def mock_manager(self, tmp_path, monkeypatch):
        """Create a mocked MacOSDaemonManager."""
        monkeypatch.setattr(sys, "platform", "darwin")

        from otpilot.infrastructure.daemon.macos import MacOSDaemonManager

        manager = MacOSDaemonManager()
        manager._launch_agents_dir = tmp_path
        manager._plist_path = tmp_path / "com.jenil.otpilot.plist"
        manager._log_dir = tmp_path / "logs"
        manager._stdout_log = tmp_path / "logs" / "daemon.out.log"
        manager._stderr_log = tmp_path / "logs" / "daemon.err.log"
        manager._pid_file = tmp_path / "logs" / "daemon.pid"

        return manager

    def test_build_plist(self, mock_manager):
        """Test plist generation."""
        plist = mock_manager._build_plist()

        assert plist["Label"] == "com.jenil.otpilot"
        assert "ProgramArguments" in plist
        assert "WorkingDirectory" in plist
        assert "StandardOutPath" in plist
        assert "StandardErrorPath" in plist
        assert plist["RunAtLoad"] is False
        assert plist["KeepAlive"]["Crashed"] is True

    def test_build_plist_autostart(self, mock_manager):
        """Test plist generation with autostart=True."""
        plist = mock_manager._build_plist(autostart=True)
        assert plist["RunAtLoad"] is True

    def test_write_plist(self, mock_manager):
        """Test writing plist file."""
        mock_manager._write_plist()
        assert mock_manager._plist_path.exists()

        import plistlib
        with open(mock_manager._plist_path, "rb") as f:
            data = plistlib.load(f)
        assert data["Label"] == "com.jenil.otpilot"
        assert data["RunAtLoad"] is False

    def test_pid_file_operations(self, mock_manager):
        """Test PID file read/write/clear operations."""
        assert mock_manager._read_pid() is None
        mock_manager._write_pid(4321)
        assert mock_manager._read_pid() == 4321
        mock_manager._clear_pid()
        assert mock_manager._read_pid() is None

    def test_cleanup_stale_or_invalid_pid(self, mock_manager, monkeypatch):
        """Test cleaning up stale or corrupt PID files."""
        # Non-running stale PID
        mock_manager._write_pid(9999)
        monkeypatch.setattr(mock_manager, "_is_process_running", lambda pid: False)
        mock_manager._cleanup_stale_pid()
        assert not mock_manager._pid_file.exists()

        # Running valid PID
        mock_manager._write_pid(4321)
        monkeypatch.setattr(mock_manager, "_is_process_running", lambda pid: True)
        mock_manager._cleanup_stale_pid()
        assert mock_manager._pid_file.exists()

        # Corrupt / non-numeric PID file
        mock_manager._pid_file.write_text("corrupted_data", encoding="utf-8")
        mock_manager._cleanup_stale_pid()
        assert not mock_manager._pid_file.exists()

    def test_get_pid_from_launchctl_dict_format(self, mock_manager, monkeypatch):
        """Test parsing dictionary output from launchctl list <label>."""
        dict_output = """{
\t"StandardOutPath" = "/Users/test/Library/Logs/otpilot/daemon.out.log";
\t"LimitLoadToSessionType" = "Aqua";
\t"Label" = "com.jenil.otpilot";
\t"OnDemand" = true;
\t"LastExitStatus" = 0;
\t"PID" = 4321;
\t"Program" = "/opt/homebrew/bin/python3";
};"""

        def mock_run(cmd, *args, **kwargs):
            result = MagicMock()
            if cmd == ["launchctl", "list", mock_manager.LABEL]:
                result.returncode = 0
                result.stdout = dict_output
            else:
                result.returncode = 1
                result.stdout = ""
            return result

        monkeypatch.setattr("subprocess.run", mock_run)
        assert mock_manager._get_pid_from_launchctl() == 4321

    def test_get_pid_from_launchctl_stopped_no_pid(self, mock_manager, monkeypatch):
        """Test parsing launchctl list when service is stopped (no PID key)."""
        stopped_output = """{
\t"Label" = "com.jenil.otpilot";
\t"OnDemand" = true;
\t"LastExitStatus" = 0;
};"""

        def mock_run(cmd, *args, **kwargs):
            result = MagicMock()
            if cmd == ["launchctl", "list", mock_manager.LABEL]:
                result.returncode = 0
                result.stdout = stopped_output
            else:
                result.returncode = 0
                result.stdout = "PID\tStatus\tLabel\n-\t0\tcom.jenil.otpilot\n"
            return result

        monkeypatch.setattr("subprocess.run", mock_run)
        assert mock_manager._get_pid_from_launchctl() is None

    def test_get_pid_from_launchctl_table_fallback(self, mock_manager, monkeypatch):
        """Test fallback to launchctl list table output."""
        def mock_run(cmd, *args, **kwargs):
            result = MagicMock()
            if cmd == ["launchctl", "list", mock_manager.LABEL]:
                result.returncode = 1
                result.stdout = ""
            elif cmd == ["launchctl", "list"]:
                result.returncode = 0
                result.stdout = "PID\tStatus\tLabel\n8888\t0\tcom.jenil.otpilot\n"
            else:
                result.returncode = 1
                result.stdout = ""
            return result

        monkeypatch.setattr("subprocess.run", mock_run)
        assert mock_manager._get_pid_from_launchctl() == 8888

    def test_is_running(self, mock_manager, monkeypatch):
        """Test is_running accurately checks process status."""
        monkeypatch.setattr(mock_manager, "_get_pid_from_launchctl", lambda: 4321)
        monkeypatch.setattr(mock_manager, "_is_process_running", lambda pid: pid == 4321)
        assert mock_manager.is_running() is True

        monkeypatch.setattr(mock_manager, "_is_process_running", lambda pid: False)
        assert mock_manager.is_running() is False

        monkeypatch.setattr(mock_manager, "_get_pid_from_launchctl", lambda: None)
        assert mock_manager.is_running() is False

    def test_status_running_and_stopped(self, mock_manager, monkeypatch):
        """Test status returns correct DaemonStatus for running and stopped states."""
        mock_manager._write_plist()

        # Running state
        monkeypatch.setattr(mock_manager, "_get_pid_from_launchctl", lambda: 4321)
        monkeypatch.setattr(mock_manager, "_is_process_running", lambda pid: True)
        status = mock_manager.status()
        assert status.installed is True
        assert status.running is True
        assert status.pid == 4321

        # Stopped state
        monkeypatch.setattr(mock_manager, "_get_pid_from_launchctl", lambda: None)
        monkeypatch.setattr(mock_manager, "_is_process_running", lambda pid: False)
        status_stopped = mock_manager.status()
        assert status_stopped.installed is True
        assert status_stopped.running is False
        assert status_stopped.pid is None

    def test_start_daemon_success(self, mock_manager, monkeypatch):
        """Test starting the daemon successfully."""
        is_running_state = [False]
        monkeypatch.setattr(mock_manager, "_is_loaded_in_launchd", lambda: False)
        monkeypatch.setattr(mock_manager, "_load_plist", lambda: True)

        def mock_run(cmd, *args, **kwargs):
            is_running_state[0] = True
            result = MagicMock()
            result.returncode = 0
            result.stdout = "service spawned with pid: 4321"
            return result

        monkeypatch.setattr("subprocess.run", mock_run)
        monkeypatch.setattr(mock_manager, "_get_pid_from_launchctl", lambda: 4321 if is_running_state[0] else None)
        monkeypatch.setattr(mock_manager, "_is_process_running", lambda pid: is_running_state[0])

        mock_manager.start()
        assert mock_manager.is_running() is True
        assert mock_manager._read_pid() == 4321

    def test_start_daemon_failure(self, mock_manager, monkeypatch):
        """Test daemon startup failure raises OTPilotError."""
        monkeypatch.setattr(mock_manager, "_is_loaded_in_launchd", lambda: True)

        def mock_run(cmd, *args, **kwargs):
            result = MagicMock()
            result.returncode = 0
            return result

        monkeypatch.setattr("subprocess.run", mock_run)
        monkeypatch.setattr(mock_manager, "is_running", lambda: False)

        with pytest.raises(OTPilotError, match="Daemon process failed to start"):
            mock_manager.start()

    def test_repeated_start_when_running(self, mock_manager, monkeypatch):
        """Test repeated start returns early without re-launching."""
        monkeypatch.setattr(mock_manager, "is_running", lambda: True)
        mock_kickstart = MagicMock()
        monkeypatch.setattr("subprocess.run", mock_kickstart)

        mock_manager.start()
        mock_kickstart.assert_not_called()

    def test_repeated_stop(self, mock_manager, monkeypatch):
        """Test repeated stop executes cleanly."""
        monkeypatch.setattr(mock_manager, "_get_pid_from_launchctl", lambda: None)
        monkeypatch.setattr(mock_manager, "_unload_plist", lambda: True)
        mock_manager._write_pid(4321)

        mock_manager.stop()
        assert mock_manager._read_pid() is None

        # Call again
        mock_manager.stop()
        assert mock_manager._read_pid() is None

    def test_autostart_toggle(self, mock_manager, monkeypatch):
        """Test enable_autostart and disable_autostart update the plist."""
        monkeypatch.setattr(mock_manager, "_is_loaded_in_launchd", lambda: True)
        mock_manager.install(autostart=False)
        assert mock_manager._is_autostart_enabled() is False

        mock_manager.enable_autostart()
        assert mock_manager._is_autostart_enabled() is True

        mock_manager.disable_autostart()
        assert mock_manager._is_autostart_enabled() is False


class TestLinuxDaemonManager:
    """Tests for LinuxDaemonManager (mocked)."""

    @pytest.fixture
    def mock_manager(self, tmp_path, monkeypatch):
        """Create a mocked LinuxDaemonManager."""
        monkeypatch.setattr(sys, "platform", "linux")

        from otpilot.infrastructure.daemon.linux import LinuxDaemonManager

        manager = LinuxDaemonManager()
        manager._config_dir = tmp_path / "systemd" / "user"
        manager._service_path = manager._config_dir / "otpilot.service"
        manager._fallback_state_dir = tmp_path / "state"
        manager._fallback_state_dir.mkdir(parents=True, exist_ok=True)
        manager.FALLBACK_PID_FILE = manager._fallback_state_dir / "daemon.pid"
        manager.FALLBACK_LOG_FILE = manager._fallback_state_dir / "daemon.log"

        return manager

    def test_check_systemd_available(self, monkeypatch):
        """Test systemd availability check."""
        from otpilot.infrastructure.daemon.linux import LinuxDaemonManager

        # Mock systemctl --user status returning success
        def mock_run_success(*args, **kwargs):
            result = MagicMock()
            result.returncode = 0
            return result

        monkeypatch.setattr("subprocess.run", mock_run_success)
        manager = LinuxDaemonManager()
        assert manager._use_systemd is True

        # Mock systemctl --user status returning failure
        def mock_run_fail(*args, **kwargs):
            result = MagicMock()
            result.returncode = 1
            return result

        monkeypatch.setattr("subprocess.run", mock_run_fail)
        manager2 = LinuxDaemonManager()
        assert manager2._use_systemd is False

    def test_build_service_content(self, mock_manager):
        """Test systemd service unit generation."""
        content = mock_manager._build_service_content()

        assert "[Unit]" in content
        assert "[Service]" in content
        assert "[Install]" in content
        assert "Type=simple" in content
        assert "ExecStart=" in content
        assert "Restart=on-failure" in content
        assert "WantedBy=default.target" in content

    def test_fallback_pid_operations(self, mock_manager):
        """Test fallback PID file operations."""
        assert mock_manager._get_pid_fallback() is None

        mock_manager._write_pid_fallback(5678)
        assert mock_manager._get_pid_fallback() == 5678

        mock_manager._clear_pid_fallback()
        assert mock_manager._get_pid_fallback() is None

    def test_cleanup_stale_or_invalid_fallback_pid(self, mock_manager, monkeypatch):
        """Test cleaning up stale or corrupt fallback PID files on Linux."""
        # Non-running stale PID
        mock_manager._write_pid_fallback(9999)
        monkeypatch.setattr(mock_manager, "_is_process_running", lambda pid: False)
        mock_manager._cleanup_stale_fallback_pid()
        assert not mock_manager.FALLBACK_PID_FILE.exists()

        # Running valid PID
        mock_manager._write_pid_fallback(5678)
        monkeypatch.setattr(mock_manager, "_is_process_running", lambda pid: True)
        mock_manager._cleanup_stale_fallback_pid()
        assert mock_manager.FALLBACK_PID_FILE.exists()

        # Corrupt / non-numeric PID file
        mock_manager.FALLBACK_PID_FILE.write_text("invalid_pid", encoding="utf-8")
        mock_manager._cleanup_stale_fallback_pid()
        assert not mock_manager.FALLBACK_PID_FILE.exists()


class TestDaemonFactory:
    """Tests for daemon factory."""

    def test_create_daemon_manager_windows(self, monkeypatch):
        """Test factory creates Windows manager on win32."""
        monkeypatch.setattr(sys, "platform", "win32")

        from otpilot.infrastructure.daemon.factory import create_daemon_manager
        from otpilot.infrastructure.daemon.windows import WindowsDaemonManager

        manager = create_daemon_manager()
        assert isinstance(manager, WindowsDaemonManager)

    def test_create_daemon_manager_macos(self, monkeypatch):
        """Test factory creates macOS manager on darwin."""
        monkeypatch.setattr(sys, "platform", "darwin")

        from otpilot.infrastructure.daemon.factory import create_daemon_manager
        from otpilot.infrastructure.daemon.macos import MacOSDaemonManager

        manager = create_daemon_manager()
        assert isinstance(manager, MacOSDaemonManager)

    def test_create_daemon_manager_linux(self, monkeypatch):
        """Test factory creates Linux manager on linux."""
        monkeypatch.setattr(sys, "platform", "linux")

        from otpilot.infrastructure.daemon.factory import create_daemon_manager
        from otpilot.infrastructure.daemon.linux import LinuxDaemonManager

        manager = create_daemon_manager()
        assert isinstance(manager, LinuxDaemonManager)

    def test_create_daemon_manager_unsupported(self, monkeypatch):
        """Test factory raises on unsupported platform."""
        monkeypatch.setattr(sys, "platform", "freebsd")

        from otpilot.infrastructure.daemon.factory import create_daemon_manager
        from otpilot.domain.errors import OTPilotError

        with pytest.raises(OTPilotError):
            create_daemon_manager()


class TestDaemonStatus:
    """Tests for DaemonStatus dataclass."""

    def test_daemon_status_creation(self) -> None:
        """Test DaemonStatus creation with all fields."""
        from otpilot.application.ports import DaemonStatus

        status = DaemonStatus(
            installed=True,
            running=True,
            pid=1234,
            autostart_enabled=True,
            error=None,
        )
        assert status.installed is True
        assert status.running is True
        assert status.pid == 1234
        assert status.autostart_enabled is True
        assert status.error is None

    def test_daemon_status_defaults(self) -> None:
        """Test DaemonStatus with defaults."""
        from otpilot.application.ports import DaemonStatus

        status = DaemonStatus(installed=False, running=False)
        assert status.installed is False
        assert status.running is False
        assert status.pid is None
        assert status.autostart_enabled is False
        assert status.error is None