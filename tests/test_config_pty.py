"""Drive `otpilot config` through a real pty to verify interactive behavior."""

import os
import select
import sys
import time

import pytest


def _read(fd: int, timeout: float = 1.0) -> str:
    chunks = []
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        ready, _, _ = select.select([fd], [], [], 0.1)
        if ready:
            try:
                data = os.read(fd, 4096)
            except OSError:
                break
            if not data:
                break
            chunks.append(data.decode("utf-8", errors="replace"))
            end = time.monotonic() + 0.2  # keep draining briefly
    return "".join(chunks)


def _env(tmp_path) -> dict[str, str]:
    """Isolate the config path for a subprocess (macOS ignores XDG_CONFIG_HOME)."""
    env = dict(os.environ)
    env["HOME"] = str(tmp_path)
    env["XDG_CONFIG_HOME"] = str(tmp_path / "xdg")
    return env


@pytest.mark.skipif(sys.platform == "win32", reason="requires a Unix pty")
def test_pty_arrow_keys_navigate_without_exiting(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    import subprocess

    master, slave = os.openpty()
    proc = subprocess.Popen(
        [sys.executable, "-m", "otpilot", "config"],
        stdin=slave,
        stdout=slave,
        stderr=slave,
        env=_env(tmp_path),
        close_fds=True,
    )
    os.close(slave)
    try:
        initial = _read(master)
        assert "OTPilot Settings" in initial
        assert "Provider ID" in initial

        # Down arrow: selection must move to Account, not exit.
        os.write(master, b"\x1b[B")
        after_down = _read(master)
        assert "Goodbye" not in after_down
        assert proc.poll() is None, "arrow key must not terminate the editor"

        # Second down arrow: selection moves to Backend.
        os.write(master, b"\x1b[B")
        after_down2 = _read(master)
        assert "Goodbye" not in after_down2
        assert proc.poll() is None

        # Up arrow moves back up.
        os.write(master, b"\x1b[A")
        after_up = _read(master)
        assert "Goodbye" not in after_up
        assert proc.poll() is None

        # Bare Escape exits cleanly.
        os.write(master, b"\x1b")
        after_esc = _read(master)
        assert "Goodbye" in after_esc

        proc.wait(timeout=10)
        assert proc.returncode == 0
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)
        os.close(master)


@pytest.mark.skipif(sys.platform == "win32", reason="requires a Unix pty")
def test_pty_return_key_selects_setting(monkeypatch, tmp_path) -> None:
    """Regression: macOS Return (\\r) must select, not be swallowed."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    import subprocess

    master, slave = os.openpty()
    proc = subprocess.Popen(
        [sys.executable, "-m", "otpilot", "config"],
        stdin=slave,
        stdout=slave,
        stderr=slave,
        env=_env(tmp_path),
        close_fds=True,
    )
    os.close(slave)
    try:
        initial = _read(master)
        assert "OTPilot Settings" in initial

        # Return on the first selectable item (Provider ID) opens the
        # selection dialog.
        os.write(master, b"\r")
        dialog = _read(master)
        assert "Goodbye" not in dialog
        assert proc.poll() is None
        assert "Choose a value" in dialog or "Gmail" in dialog

        # Escape cancels back to the menu, then Escape exits.
        os.write(master, b"\x1b")
        _read(master)
        os.write(master, b"\x1b")
        after_esc = _read(master)
        assert "Goodbye" in after_esc

        proc.wait(timeout=10)
        assert proc.returncode == 0
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)
        os.close(master)
