import typer

from otpilot.application.services import LogoutService
from otpilot.infrastructure.credentials.windows import WindowsCredentialManagerStore


def command(
    account: str = typer.Argument(
        ...,
        help="Email account whose credential should be removed.",
    ),
) -> None:
    """Remove stored credentials for an email account."""
    LogoutService(WindowsCredentialManagerStore()).logout(account)
    typer.echo(f"Credentials removed for {account}.")
