from otpilot.domain.models import AccountId
from otpilot.infrastructure.credentials import windows


def test_credential_store_round_trip(monkeypatch) -> None:
    values: dict[tuple[str, str], str] = {}
    monkeypatch.setattr(
        windows.keyring,
        "set_password",
        lambda service, username, password: values.__setitem__((service, username), password),
    )
    monkeypatch.setattr(
        windows.keyring,
        "get_password",
        lambda service, username: values.get((service, username)),
    )
    monkeypatch.setattr(
        windows.keyring,
        "delete_password",
        lambda service, username: values.pop((service, username), None),
    )
    store = windows.WindowsCredentialManagerStore()
    account = AccountId("user@example.com")

    store.save_app_password(account, "user@example.com", "app-secret")
    assert store.get_app_password(account) == ("user@example.com", "app-secret")
    store.delete_app_password(account)
    assert store.get_app_password(account) is None
    assert "app-secret" not in str(values)


def test_missing_credential_returns_none(monkeypatch) -> None:
    monkeypatch.setattr(windows.keyring, "get_password", lambda service, username: None)
    assert windows.WindowsCredentialManagerStore().get_app_password(AccountId("missing")) is None
