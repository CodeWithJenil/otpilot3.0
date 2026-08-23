"""Windows Credential Manager adapter backed by the platform keyring."""

import json

import keyring

from otpilot.domain.errors import CredentialError
from otpilot.domain.models import AccountId


class WindowsCredentialManagerStore:
    service_name = "OTPilot"

    def _target(self, account_id: AccountId) -> str:
        return f"{self.service_name}:{account_id}"

    def save_app_password(self, account_id: AccountId, username: str, app_password: str) -> None:
        if not username or not app_password:
            raise CredentialError("Username and app password are required.")
        try:
            keyring.set_password(
                self._target(account_id),
                str(account_id),
                json.dumps({"username": username, "password": app_password}),
            )
        except Exception as exc:
            raise CredentialError(
                "Unable to store credentials in the operating system vault."
            ) from exc

    def get_app_password(self, account_id: AccountId) -> tuple[str, str] | None:
        try:
            stored = keyring.get_password(self._target(account_id), str(account_id))
        except Exception as exc:
            raise CredentialError(
                "Unable to read credentials from the operating system vault."
            ) from exc
        if stored is None:
            return None
        try:
            value = json.loads(stored)
            username = value["username"]
            password = value["password"]
        except (TypeError, ValueError, KeyError) as exc:
            raise CredentialError("Stored credentials are invalid.") from exc
        if not isinstance(username, str) or not isinstance(password, str):
            raise CredentialError("Stored credentials are invalid.")
        return username, password

    def delete_app_password(self, account_id: AccountId) -> None:
        try:
            keyring.delete_password(self._target(account_id), str(account_id))
        except keyring.errors.PasswordDeleteError:
            return
        except Exception as exc:
            raise CredentialError(
                "Unable to remove credentials from the operating system vault."
            ) from exc
