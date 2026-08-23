import pytest

from otpilot.domain.errors import ClipboardError
from otpilot.infrastructure.clipboard import pyperclip_adapter


def test_pyperclip_adapter_copies_value(monkeypatch) -> None:
    copied: list[str] = []
    monkeypatch.setattr(pyperclip_adapter.pyperclip, "copy", copied.append)

    pyperclip_adapter.PyperclipClipboard().copy("482731")

    assert copied == ["482731"]


def test_pyperclip_adapter_converts_library_failure(monkeypatch) -> None:
    def fail(value: str) -> None:
        raise RuntimeError("clipboard unavailable")

    monkeypatch.setattr(pyperclip_adapter.pyperclip, "copy", fail)

    with pytest.raises(ClipboardError, match="Unable to copy"):
        pyperclip_adapter.PyperclipClipboard().copy("482731")
