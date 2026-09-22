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
    fail_search = False
    fail_fetch = False
    fail_logout = False

    def __init__(self, *args, **kwargs) -> None:
        self.args = args
        self.kwargs = kwargs
        self.logged_out = False
        self.logout_calls = 0
        self.__class__.instances.append(self)

    def login(self, username: str, password: str) -> None:
        if self.fail_login:
            raise OSError("transport failure")
        self.login_args = (username, password)

    def select_folder(self, mailbox: str, readonly: bool = False) -> None:
        self.folder = (mailbox, readonly)

    def search(self, criteria) -> list[int]:
        if self.fail_search:
            raise OSError("search failure")
        self.criteria = criteria
        return [1]

    def fetch(self, messages, data):
        if self.fail_fetch:
            raise OSError("fetch failure")
        return {1: {b"RFC822": RAW_MESSAGE, b"INTERNALDATE": datetime.now(UTC)}}

    def logout(self) -> None:
        self.logout_calls += 1
        self.logged_out = True
        if self.fail_logout:
            raise OSError("logout failure")


def make_provider() -> ImapProvider:
    return ImapProvider.generic(ImapConnectionConfig("imap.gmail.com"), ImapSearchStrategy())


def reset_failures() -> None:
    FakeClient.fail_login = False
    FakeClient.fail_search = False
    FakeClient.fail_fetch = False
    FakeClient.fail_logout = False


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
        reset_failures()


def test_imap_provider_handles_malformed_body_part_without_exposing_content(monkeypatch) -> None:
    malformed = (
        b"From: security@example.com\nSubject: Verification code\n"
        b"Content-Type: text/plain; charset=unknown-charset\n\n482913"
    )

    class MalformedClient(FakeClient):
        def fetch(self, messages, data):
            return {1: {b"RFC822": malformed, b"INTERNALDATE": datetime.now(UTC)}}

    monkeypatch.setattr(provider_module, "IMAPClient", MalformedClient)
    provider = make_provider()
    provider.authenticate(AccountId("account"), "user@example.com", "app-password")

    emails = list(provider.search(AccountId("account"), SearchCriteria(unseen_only=False)))

    assert len(emails) == 1
    assert emails[0].text_body == ""


@pytest.mark.parametrize("failure", ["fail_search", "fail_fetch"])
def test_imap_operation_failure_logs_out_and_hides_credentials(monkeypatch, failure: str) -> None:
    FakeClient.instances.clear()
    reset_failures()
    setattr(FakeClient, failure, True)
    monkeypatch.setattr(provider_module, "IMAPClient", FakeClient)
    provider = make_provider()
    provider.authenticate(AccountId("account"), "user@example.com", "app-password")

    with pytest.raises(ImapTransportError) as error:
        provider.search(AccountId("account"), SearchCriteria(unseen_only=False))

    assert FakeClient.instances[-1].logged_out is True
    assert "user@example.com" not in str(error.value)
    assert "app-password" not in str(error.value)
    reset_failures()


def test_logout_failure_does_not_mask_search_failure(monkeypatch) -> None:
    FakeClient.instances.clear()
    reset_failures()
    FakeClient.fail_search = True
    FakeClient.fail_logout = True
    monkeypatch.setattr(provider_module, "IMAPClient", FakeClient)
    provider = make_provider()
    provider.authenticate(AccountId("account"), "user@example.com", "app-password")

    with pytest.raises(ImapTransportError, match="search or message retrieval"):
        provider.search(AccountId("account"), SearchCriteria(unseen_only=False))

    assert FakeClient.instances[-1].logged_out is True
    reset_failures()


def test_connection_timeout_is_translated_without_storing_credentials(monkeypatch) -> None:
    class TimeoutClient(FakeClient):
        def __init__(self, *args, **kwargs) -> None:
            raise TimeoutError("socket timed out")

    monkeypatch.setattr(provider_module, "IMAPClient", TimeoutClient)
    provider = make_provider()

    with pytest.raises(ImapTransportError, match="establish an IMAP connection") as error:
        provider.authenticate(AccountId("account"), "user@example.com", "app-password")

    assert "app-password" not in str(error.value)
    assert provider._credentials is None


def test_connection_timeout_is_configured_and_successful_operations_logout(monkeypatch) -> None:
    FakeClient.instances.clear()
    reset_failures()
    monkeypatch.setattr(provider_module, "IMAPClient", FakeClient)
    provider = ImapProvider.generic(
        ImapConnectionConfig("imap.gmail.com", timeout_seconds=12.5), ImapSearchStrategy()
    )

    provider.authenticate(AccountId("account"), "user@example.com", "app-password")
    provider.search(AccountId("account"), SearchCriteria(unseen_only=False))

    assert all(client.logged_out for client in FakeClient.instances)
    assert all(client.logout_calls == 1 for client in FakeClient.instances)
    assert all(client.kwargs["timeout"] == 12.5 for client in FakeClient.instances)


def test_partial_client_initialization_is_translated_safely(monkeypatch) -> None:
    class PartiallyInitializedClient(FakeClient):
        created: ClassVar[list["PartiallyInitializedClient"]] = []

        def __init__(self, *args, **kwargs) -> None:
            super().__init__(*args, **kwargs)
            self.__class__.created.append(self)
            raise OSError("TLS setup failed")

    monkeypatch.setattr(provider_module, "IMAPClient", PartiallyInitializedClient)

    with pytest.raises(ImapTransportError, match="establish an IMAP connection"):
        make_provider().authenticate(AccountId("account"), "user@example.com", "app-password")

    assert len(PartiallyInitializedClient.created) == 1
    assert PartiallyInitializedClient.created[0].logout_calls == 0


def test_invalid_fetch_response_is_typed_and_connection_is_cleaned_up(monkeypatch) -> None:
    class InvalidResponseClient(FakeClient):
        def fetch(self, messages, data):
            return []

    InvalidResponseClient.instances.clear()
    monkeypatch.setattr(provider_module, "IMAPClient", InvalidResponseClient)
    provider = make_provider()
    provider.authenticate(AccountId("account"), "user@example.com", "app-password")

    with pytest.raises(ImapTransportError, match="search or message retrieval"):
        provider.search(AccountId("account"), SearchCriteria(unseen_only=False))

    assert InvalidResponseClient.instances[-1].logged_out is True
