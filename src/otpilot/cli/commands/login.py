"""Interactive login command.

Prompts user for email address and Gmail App Password, validates the IMAP connection,
and stores credentials securely in the OS keyring.

Usage:
    otpilot login

The command will:
1. Prompt for email address (with validation)
2. Prompt for App Password (masked input)
3. Test IMAP connection with provided credentials
4. Store credentials in OS keyring on success
5. Display appropriate success/failure messages
"""

import typer

from otpilot.application.services import LoginService
from otpilot.infrastructure.config_storage.toml import TomlConfigurationRepository
from otpilot.infrastructure.credentials.keyring_store import KeyringCredentialStore
from otpilot.domain.errors import OTPilotError


def command() -> None:
    """Interactive login: prompt for email and app password, validate, and store credentials."""
    # Prompt for email address
    email = typer.prompt("Email address", default="")

    if not email or "@" not in email:
        raise typer.BadParameter("Please enter a valid email address.")

    # Prompt for App Password (masked)
    password = typer.prompt("App password", hide_input=True, confirmation_prompt=True)

    if not password:
        raise typer.BadParameter("App password cannot be empty.")

    # Store credentials using the keyring-backed service
    try:
        LoginService(
            KeyringCredentialStore(),
            TomlConfigurationRepository(),
        ).login(email, password)
        typer.echo(f"Credentials stored for {email}.")
    except OTPilotError as exc:
        raise typer.Exit(code=1) from exc
