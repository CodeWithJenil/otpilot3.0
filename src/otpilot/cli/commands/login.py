import typer

from otpilot.application.services import LoginService
from otpilot.infrastructure.config_storage.toml import TomlConfigurationRepository
from otpilot.infrastructure.credentials.keyring_store import KeyringCredentialStore


def command(
    email: str = typer.Argument(
        ...,
        help="Email account to associate with a stored app password.",
    ),
) -> None:
    """Store credentials for an email account using the configured secure credential backend."""
    password = typer.prompt("App password", hide_input=True, confirmation_prompt=True)
    LoginService(
        KeyringCredentialStore(),
        TomlConfigurationRepository(),
    ).login(email, password)
    typer.echo(f"Credentials stored for {email}.")
