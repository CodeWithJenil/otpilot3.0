import typer

from otpilot.application.services import LoginService
from otpilot.infrastructure.config_storage.toml import TomlConfigurationRepository
from otpilot.infrastructure.credentials.windows import WindowsCredentialManagerStore


def command(
    email: str = typer.Argument(
        ...,
        help="Email account to associate with a stored app password.",
    ),
) -> None:
    """Store credentials for an email account using the configured secure credential backend."""
    password = typer.prompt("Gmail app password", hide_input=True, confirmation_prompt=True)
    LoginService(
        WindowsCredentialManagerStore(),
        TomlConfigurationRepository(),
    ).login(email, password)
    typer.echo(f"Credentials stored for {email}.")
