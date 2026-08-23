from datetime import UTC, datetime
from typing import ClassVar

import pytest

from otpilot.domain.errors import ImapTransportError
from otpilot.domain.models import AccountId
from otpilot.domain.search import SearchCriteria
from otpilot.providers.imap import provider as provider_module
from otpilot.providers.imap.provider import ImapConnectionConfig, ImapProvider
from otpilot.providers.imap.search import ImapSearchStrategy

RAW_MESSAGE = b"From: security@example.com\nSubject: Verification code\n\nYour OTP is 482913.\n"


class FakeClient:
    instances: ClassVar[list["FakeClient"]] = []
    fail_login = False

    def __init__(self, *args, **kwargs) -> None:
        self.args = args
        self.kwargs = kwargs
        self.logged_out = False
        self.__class__.instances.append(self)

    def login(self, username: str, password: str) -> None:
        if self.fail_login:
            raise RuntimeError("transport failure")
        self.login_args = (username, password)

    def select_folder(self, mailbox: str, readonly: bool = False) -> None:
        self.folder = (mailbox, readonly)

    def search(self, criteria) -> list[int]:
        self.criteria = criteria
        return [1]

    def fetch(self, messages, data):
        return {1: {b"RFC822": RAW_MESSAGE, b"INTERNALDATE": datetime.now(UTC)}}

    def logout(self) -> None:
        self.logged_out = True


def make_provider() -> ImapProvider:
    return ImapProvider.generic(ImapConnectionConfig("imap.gmail.com"), ImapSearchStrategy())


def test_imap_provider_authenticates_searches_and_parses_message(monkeypatch) -> None:
    FakeClient.instances.clear()
    monkeypatch.setattr(provider_module, "IMAPClient", FakeClient)
    provider = make_provider()
    provider.authenticate(AccountId("account"), "user@example.com", "app-password")
    emails = list(provider.search(AccountId("account"), SearchCriteria(unseen_only=False)))

    assert emails[0].subject == "Verification code"
    assert emails[0].text_body == "Your OTP is 482913.\n"
    assert FakeClient.instances[-1].logged_out is True


def test_imap_provider_converts_transport_failure(monkeypatch) -> None:
    FakeClient.fail_login = True
    monkeypatch.setattr(provider_module, "IMAPClient", FakeClient)
    try:
        with pytest.raises(ImapTransportError):
            make_provider().authenticate(AccountId("account"), "user@example.com", "app-password")
    finally:
        FakeClient.fail_login = False
