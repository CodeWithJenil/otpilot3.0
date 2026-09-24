"""Command entry point for interactive configuration.

This module simply delegates to :func:`config_controller.run_interactive`
and :func:`config_controller.run_non_interactive`.  The heavy lifting
is performed by the controller which implements a deterministic state
machine.
"""

from __future__ import annotations

import typer
from rich.console import Console

from otpilot.cli.commands.config_controller import run_interactive, run_non_interactive

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
    if non_interactive:
        run_non_interactive(console)
    else:
        run_interactive(console)

