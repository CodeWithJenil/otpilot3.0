import sys
from collections.abc import Callable
from types import SimpleNamespace
from typing import ClassVar

import pytest

from otpilot.application.services import HotkeyService
from otpilot.domain.errors import (
    BackgroundServiceError,
    ClipboardError,
    CredentialError,
    ExtractionError,
)
from otpilot.infrastructure.hotkeys.pynput_adapter import PynputHotkeyListener


class FakeListener:
    def __init__(self, *, error: Exception | None = None, interrupt: bool = False) -> None:
        self.error = error
        self.interrupt = interrupt
        self.hotkey: str | None = None
        self.callback: Callable[[], None] | None = None
        self.shutdown_calls = 0

    def register(self, hotkey: str, callback: Callable[[], None]) -> None:
        if self.error is not None:
            raise self.error
        self.hotkey = hotkey
        self.callback = callback

    def run(self) -> None:
        if self.interrupt:
            raise KeyboardInterrupt

    def shutdown(self) -> None:
        self.shutdown_calls += 1


class FakeFetchService:
    def __init__(self, outcome: Exception | None = None) -> None:
        self.outcome = outcome
        self.validated = False
        self.fetch_calls = 0
        self.copy_calls = 0

    def validate_ready(self) -> None:
        self.validated = True

    def fetch(self) -> object:
        self.fetch_calls += 1
        if self.outcome is not None:
            raise self.outcome
        return object()

    def copy_result(self, result: object) -> None:
        self.copy_calls += 1


def test_hotkey_service_validates_registers_and_unregisters_listener() -> None:
    listener = FakeListener()
    fetch = FakeFetchService()
    statuses: list[str] = []
    service = HotkeyService(fetch, listener, "ctrl+shift+o", statuses.append)  # type: ignore[arg-type]

    service.run()

    assert fetch.validated is True
    assert listener.hotkey == "ctrl+shift+o"
    assert listener.shutdown_calls == 1
    assert statuses == ["Hotkey active: Ctrl+Shift+O", "Press Ctrl+C to stop."]


def test_hotkey_service_cleans_up_after_interruption() -> None:
    listener = FakeListener(interrupt=True)
    service = HotkeyService(FakeFetchService(), listener, "ctrl+shift+o")  # type: ignore[arg-type]

    service.run()

    assert listener.shutdown_calls == 1


def test_hotkey_service_does_not_register_when_validation_fails() -> None:
    listener = FakeListener()
    fetch = FakeFetchService(CredentialError("missing credentials"))

    def fail_validation() -> None:
        raise fetch.outcome  # type: ignore[misc]

    fetch.validate_ready = fail_validation
    service = HotkeyService(fetch, listener, "ctrl+shift+o")  # type: ignore[arg-type]

    with pytest.raises(CredentialError, match="missing credentials"):
        service.run()

    assert listener.hotkey is None
    assert listener.shutdown_calls == 0


def test_hotkey_trigger_fetches_and_copies_without_printing_otp() -> None:
    statuses: list[str] = []
    fetch = FakeFetchService()
    service = HotkeyService(fetch, FakeListener(), "ctrl+shift+o", statuses.append)  # type: ignore[arg-type]

    service.trigger()
    service._executor.shutdown(wait=True)

    assert fetch.fetch_calls == 1
    assert fetch.copy_calls == 1
    assert statuses == ["OTP copied to clipboard."]


@pytest.mark.parametrize("error", [ExtractionError("not found"), ClipboardError("unavailable")])
def test_hotkey_trigger_reports_recoverable_failures(error: Exception) -> None:
    statuses: list[str] = []
    service = HotkeyService(
        FakeFetchService(error), FakeListener(), "ctrl+shift+o", statuses.append
    )  # type: ignore[arg-type]

    service.trigger()
    service._executor.shutdown(wait=True)

    assert statuses == [f"OTP fetch failed: {error}"]


def test_hotkey_trigger_contains_unexpected_callback_errors() -> None:
    statuses: list[str] = []
    service = HotkeyService(
        FakeFetchService(RuntimeError("sensitive detail")),
        FakeListener(),
        "ctrl+shift+o",
        statuses.append,
    )  # type: ignore[arg-type]

    service.trigger()
    service._executor.shutdown(wait=True)

    assert statuses == ["OTP fetch failed: An unexpected error occurred."]


def test_hotkey_trigger_ignores_repeated_trigger_while_active() -> None:
    fetch = FakeFetchService()
    service = HotkeyService(fetch, FakeListener(), "ctrl+shift+o")  # type: ignore[arg-type]
    assert service._active.acquire(blocking=False)
    try:
        service.trigger()
    finally:
        service._active.release()
    service._executor.shutdown(wait=True)

    assert fetch.fetch_calls == 0


def test_pynput_listener_rejects_unsupported_platform(monkeypatch) -> None:
    monkeypatch.setattr("otpilot.infrastructure.hotkeys.pynput_adapter.sys.platform", "linux")

    with pytest.raises(BackgroundServiceError, match="only on Windows"):
        PynputHotkeyListener().register("ctrl+shift+o", lambda: None)


def test_pynput_listener_reports_missing_dependency(monkeypatch) -> None:
    monkeypatch.setattr("otpilot.infrastructure.hotkeys.pynput_adapter.sys.platform", "win32")
    monkeypatch.setitem(sys.modules, "pynput", None)
    monkeypatch.delitem(sys.modules, "pynput.keyboard", raising=False)

    with pytest.raises(BackgroundServiceError, match="unavailable"):
        PynputHotkeyListener().register("ctrl+shift+o", lambda: None)


def test_pynput_listener_registers_prevents_duplicates_and_shutdown_is_idempotent(
    monkeypatch,
) -> None:
    class FakeGlobalHotKeys:
        instances: ClassVar[list["FakeGlobalHotKeys"]] = []

        def __init__(self, hotkeys: dict[str, Callable[[], None]]) -> None:
            self.hotkeys = hotkeys
            self.started = False
            self.stopped = 0
            self.__class__.instances.append(self)

        def start(self) -> None:
            self.started = True

        def join(self) -> None:
            return

        def stop(self) -> None:
            self.stopped += 1

    monkeypatch.setattr("otpilot.infrastructure.hotkeys.pynput_adapter.sys.platform", "win32")
    monkeypatch.setitem(
        sys.modules, "pynput.keyboard", SimpleNamespace(GlobalHotKeys=FakeGlobalHotKeys)
    )
    listener = PynputHotkeyListener()

    def callback() -> None:
        return None

    listener.register("ctrl+shift+o", callback)
    with pytest.raises(BackgroundServiceError, match="already registered"):
        listener.register("ctrl+shift+o", callback)
    listener.shutdown()
    listener.shutdown()

    instance = FakeGlobalHotKeys.instances[0]
    assert instance.hotkeys == {"<ctrl>+<shift>+o": callback}
    assert instance.started is True
    assert instance.stopped == 1


def test_pynput_listener_translates_registration_failure(monkeypatch) -> None:
    class FailingGlobalHotKeys:
        def __init__(self, hotkeys: dict[str, Callable[[], None]]) -> None:
            raise RuntimeError("library detail")

    monkeypatch.setattr("otpilot.infrastructure.hotkeys.pynput_adapter.sys.platform", "win32")
    monkeypatch.setitem(
        sys.modules, "pynput.keyboard", SimpleNamespace(GlobalHotKeys=FailingGlobalHotKeys)
    )

    with pytest.raises(BackgroundServiceError, match="Unable to register"):
        PynputHotkeyListener().register("ctrl+shift+o", lambda: None)
