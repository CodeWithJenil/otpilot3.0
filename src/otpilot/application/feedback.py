"""Feedback prompt service for OTPilot CLI."""

from __future__ import annotations

import random
import sys
import typer
import webbrowser
from dataclasses import dataclass
from typing import Protocol

from otpilot.application.settings import SettingsService
from otpilot.preferences.models import UserPreferences


class BrowserOpener(Protocol):
    """Protocol for opening URLs in a browser."""

    def open(self, url: str) -> bool:
        """Open the URL in the default browser. Returns True if successful."""
        ...


class DefaultBrowserOpener:
    """Default browser opener using webbrowser module."""

    def open(self, url: str) -> bool:
        try:
            return webbrowser.open(url)
        except Exception:
            return False


@dataclass(frozen=True, slots=True)
class FeedbackConfig:
    """Configuration for feedback prompts."""

    enabled: bool
    min_commands: int
    commands_since_prompt: int
    prompt_probability: float = 0.1  # 10% chance after minimum is reached

    def should_prompt(self) -> bool:
        """Check if a feedback prompt should be shown."""
        if not self.enabled:
            return False
        if self.commands_since_prompt < self.min_commands:
            return False
        # Random trigger after minimum
        return random.random() < self.prompt_probability


class FeedbackPromptService:
    """Service for managing feedback prompts in the CLI."""

    FEEDBACK_URL = "https://jenil-otpilot.vercel.app/feedback"

    def __init__(
        self,
        settings_service: SettingsService,
        browser_opener: BrowserOpener | None = None,
        random_source: random.Random | None = None,
    ) -> None:
        self._settings = settings_service
        self._browser = browser_opener or DefaultBrowserOpener()
        self._random = random_source or random.Random()

    def _get_preferences(self) -> UserPreferences:
        """Get current preferences from settings service."""
        snapshot = self._settings.snapshot()
        entry = snapshot.entry("preferences")
        if entry.value is None:
            return UserPreferences()
        return entry.value  # type: ignore[return-value]

    def _update_feedback_counter(self, commands_since_prompt: int) -> None:
        """Update the feedback commands counter in preferences."""
        self._settings.set("preferences.feedback_commands_since_prompt", str(commands_since_prompt))

    def _build_feedback_url(self, version: str) -> str:
        """Build the feedback URL with version parameter."""
        return f"{self.FEEDBACK_URL}?version={version}"

    def maybe_prompt(self, version: str) -> None:
        """
        Check if feedback prompt should be shown and show it if so.
        
        This method is non-blocking and will never raise exceptions that
        could break the CLI command flow.
        """
        try:
            # Only prompt in interactive TTY environments
            if not sys.stdout.isatty() or not sys.stdin.isatty():
                return

            prefs = self._get_preferences()

            config = FeedbackConfig(
                enabled=prefs.feedback_prompts_enabled,
                min_commands=prefs.feedback_prompt_min_commands,
                commands_since_prompt=prefs.feedback_commands_since_prompt,
            )

            if not config.enabled:
                # Don't increment counter if disabled
                return

            if not config.should_prompt():
                # Increment counter and return
                self._update_feedback_counter(config.commands_since_prompt + 1)
                return

            # Show prompt
            self._show_prompt(version)

            # Reset counter after prompting
            self._update_feedback_counter(0)

        except Exception:
            # Never let feedback functionality break the CLI
            pass

    def _show_prompt(self, version: str) -> None:
        """Display the feedback prompt and handle user response."""
        import typer

        # Build the feedback URL with version
        url = self._build_feedback_url(version)

        # Display prompt using OTPilot's visual style
        typer.echo("")
        typer.secho("Want to help improve OTPilot?", fg=typer.colors.BRIGHT_GREEN, bold=True)
        typer.echo(f"Share your feedback: {url}")
        typer.echo("")

        # Ask for confirmation
        try:
            response = typer.prompt("Open feedback page? [y/N]", default="n", show_default=False)
            if response.strip().lower() in ("y", "yes"):
                self._browser.open(url)
        except (typer.Abort, KeyboardInterrupt, EOFError):
            # User cancelled - just continue silently
            pass
        except Exception:
            # Any other error - silently continue
            pass


def create_feedback_prompt_service(
    settings_service: SettingsService,
    browser_opener: BrowserOpener | None = None,
    random_source: random.Random | None = None,
) -> FeedbackPromptService:
    """Factory to create a feedback prompt service."""
    return FeedbackPromptService(settings_service, browser_opener, random_source)