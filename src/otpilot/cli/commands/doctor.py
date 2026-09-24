"""Inspect local configuration, provider availability, and platform support."""

from __future__ import annotations

import typer

from otpilot.application.doctor import DoctorService
from otpilot.domain.diagnostics import CheckStatus, DiagnosticCheck, DiagnosticReport
from otpilot.domain.errors import OTPilotError
from otpilot.infrastructure.config_storage.toml import TomlConfigurationRepository
from otpilot.infrastructure.credentials.keyring_store import KeyringCredentialStore
from otpilot.infrastructure.diagnostics.platform import DefaultPlatformDiagnostics
from otpilot.infrastructure.preferences.toml import TomlPreferencesRepository
from otpilot.providers.registry import build_provider_registry


def build_doctor_service(*, test_connectivity: bool) -> DoctorService:
    return DoctorService(
        config=TomlConfigurationRepository(),
        credentials=KeyringCredentialStore(),
        providers=build_provider_registry(),
        platform=DefaultPlatformDiagnostics(),
        preferences=TomlPreferencesRepository(),
        test_connectivity=test_connectivity,
    )


def _print_report(report: DiagnosticReport) -> None:
    typer.echo("OTPilot Doctor")
    current_category = ""
    for check in report.checks:
        if check.category != current_category:
            typer.echo("")
            typer.echo(check.category)
            current_category = check.category
        typer.echo(_format_check(check))
        if (
            check.remediation
            and check.status in {CheckStatus.FAIL, CheckStatus.WARN, CheckStatus.SKIP}
        ):
            typer.echo(f"        {check.remediation}")
    counts = report.counts()
    typer.echo("")
    typer.echo("Summary")
    typer.echo(f"  Passed: {counts[CheckStatus.PASS]}")
    typer.echo(f"  Warnings: {counts[CheckStatus.WARN]}")
    typer.echo(f"  Failed: {counts[CheckStatus.FAIL]}")
    typer.echo(f"  Skipped: {counts[CheckStatus.SKIP]}")


def _format_check(check: DiagnosticCheck) -> str:
    return f"  {check.status.value:<4}  {check.message}"


def command(
    offline: bool = typer.Option(
        False,
        "--offline",
        help="Skip the live Gmail IMAP login check.",
    ),
) -> None:
    """Inspect local configuration, provider availability, and platform support."""
    try:
        report = build_doctor_service(test_connectivity=not offline).inspect()
    except OTPilotError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    _print_report(report)
    if report.has_failures():
        raise typer.Exit(code=1)
