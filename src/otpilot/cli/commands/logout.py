import typer

from otpilot.application.services import LogoutService
from otpilot.infrastructure.credentials.keyring_store import KeyringCredentialStore


def command(
    account: str = typer.Argument(
        ...,
        help="Email account whose credential should be removed.",
    ),
) -> None:
    """Remove stored credentials for an email account."""
    LogoutService(KeyringCredentialStore()).logout(account)
    typer.echo(f"Credentials removed for {account}.")
