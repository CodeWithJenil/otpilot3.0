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

    def test_build_daemon_watch_service(self) -> None:
        """Test that build_daemon_watch_service can be imported."""
        from otpilot.cli.commands.daemon import build_daemon_watch_service
        assert callable(build_daemon_watch_service)


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
            # args[0] is the command list, e.g., ['tasklist', '/FI', 'PID eq 1234', '/NH']
            cmd_str = " ".join(args[0]) if args else ""
            if "1234" in cmd_str:
                result.stdout = "python.exe                   1234 Console                    1     10,000 K"
            else:
                result.stdout = ""
            return result

        monkeypatch.setattr("subprocess.run", mock_run)

        assert mock_manager._is_process_running(1234) is True
        assert mock_manager._is_process_running(9999) is False


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

    def test_write_plist(self, mock_manager):
        """Test writing plist file."""
        mock_manager._write_plist()
        assert mock_manager._plist_path.exists()

        import plistlib
        with open(mock_manager._plist_path, "rb") as f:
            data = plistlib.load(f)
        assert data["Label"] == "com.jenil.otpilot"


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