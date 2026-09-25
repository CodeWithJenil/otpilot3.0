"""Command entry point for interactive configuration.

This module delegates to :class:`config_controller.ConfigController` for
interactive editing and to :func:`config_controller.run_non_interactive` for
read-only output.  When stdin is not a TTY the command automatically falls
back to non-interactive mode.
"""

from __future__ import annotations

import sys

import typer
from rich.console import Console

from otpilot.cli.commands.config_controller import (
    create_controller,
    run_non_interactive,
)
from otpilot.domain.errors import OTPilotError

app = typer.Typer(
    help="Inspect or update non-secret configuration and user preferences.",
    no_args_is_help=False,
)


@app.callback(invoke_without_command=True)
def command(
    ctx: typer.Context,
    non_interactive: bool = typer.Option(
        False, "--non-interactive", "-n", help="Run in non-interactive mode."
    ),
):
    if ctx.invoked_subcommand is not None:
        return
    console = Console()
    try:
        if non_interactive or not sys.stdin.isatty():
            run_non_interactive(console)
        else:
            controller = create_controller(console)
            controller.run()
    except OTPilotError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc
