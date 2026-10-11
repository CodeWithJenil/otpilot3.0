"""Daemon runtime state tracking."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

import platformdirs


@dataclass(frozen=True, slots=True)
class DaemonRuntimeState:
    state: str  # "starting", "running", "reconnecting", "stopping", "stopped"
    pid: int | None = None
    connected_at: float | None = None
    last_event_at: float | None = None
    error: str | None = None
    account: str | None = None
    updated_at: float = field(default_factory=time.time)


class DaemonStateStore:
    """Read and write daemon runtime state to disk for cross-process status inspection."""

    def __init__(self, state_dir: Path | None = None) -> None:
        self._dir = state_dir or Path(platformdirs.user_state_path("otpilot"))
        self._file = self._dir / "daemon_state.json"

    def write(self, runtime_state: DaemonRuntimeState) -> None:
        try:
            self._dir.mkdir(parents=True, exist_ok=True)
            data = asdict(runtime_state)
            temp_file = self._file.with_suffix(".tmp")
            temp_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
            temp_file.replace(self._file)
        except OSError:
            pass

    def read(self) -> DaemonRuntimeState | None:
        try:
            if not self._file.exists():
                return None
            data = json.loads(self._file.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return None
            return DaemonRuntimeState(
                state=str(data.get("state", "stopped")),
                pid=data.get("pid"),
                connected_at=data.get("connected_at"),
                last_event_at=data.get("last_event_at"),
                error=data.get("error"),
                account=data.get("account"),
                updated_at=data.get("updated_at", 0.0),
            )
        except (OSError, json.JSONDecodeError, ValueError):
            return None

    def clear(self) -> None:
        try:
            self._file.unlink(missing_ok=True)
        except OSError:
            pass
