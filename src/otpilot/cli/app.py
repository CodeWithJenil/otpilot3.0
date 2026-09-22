"""OTPilot CLI entrypoint."""

import typer

from otpilot import __version__
from otpilot.cli.commands import config, doctor, fetch, hotkey, login, logout, watch

app = typer.Typer(
    name="otpilot",
    help="Local-first OTP extraction from email accounts.",
    no_args_is_help=True,
)
app.command("fetch")(fetch.command)
app.command("watch")(watch.command)
app.command("hotkey")(hotkey.command)
app.command("login")(login.command)
app.command("logout")(logout.command)
app.command("config")(config.command)
app.command("doctor")(doctor.command)


@app.command("version")
def version() -> None:
    """Show the installed OTPilot version."""
    typer.echo(__version__)


def main() -> None:
    app()
