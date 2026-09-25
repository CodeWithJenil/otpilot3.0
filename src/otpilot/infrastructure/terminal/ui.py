"""Terminal UI components for interactive configuration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from rich.align import Align
from rich.console import Console, ConsoleRenderable
from rich.panel import Panel
from rich.style import Style
from rich.text import Text

from otpilot.infrastructure.terminal.keyboard import Key


@dataclass(frozen=True, slots=True)
class MenuItem:
    """A single item in a navigation menu."""

    key: str
    label: str
    description: str
    current_value: str
    item_type: str  # "setting", "action", "section"
    section: str | None = None


class SettingsMenu:
    """Renders the interactive settings menu."""

    def __init__(self, console: Console) -> None:
        self.console = console
        self.selected_index = 0
        self.items: list[MenuItem] = []
        self.sections: dict[str, list[MenuItem]] = {}

    def build_items(self, snapshot: Any, settable_keys: set[str]) -> None:
        """Build menu items from a settings snapshot."""
        self.items = []
        self.sections = {}

        section_order = [
            "provider",
            "credential_backend",
            "watch",
            "hotkeys",
            "preferences",
        ]

        section_titles = {
            "provider": "Provider",
            "credential_backend": "Credential Backend",
            "watch": "Watch",
            "hotkeys": "Hotkeys",
            "preferences": "Preferences",
        }

        section_descriptions = {
            "provider": "Email provider configuration",
            "credential_backend": "Credential storage backend",
            "watch": "Watch mode settings",
            "hotkeys": "Global hotkey configuration",
            "preferences": "User interface preferences",
        }

        # Group settings by section
        for entry in snapshot.entries:
            if entry.key not in settable_keys and not entry.key.startswith("preferences."):
                continue

            section = self._get_section(entry.key)
            if section not in self.sections:
                self.sections[section] = []

            item = MenuItem(
                key=entry.key,
                label=self._get_label(entry.key),
                description=self._get_description(entry.key),
                current_value=entry.display_value(),
                item_type="setting",
                section=section,
            )
            self.sections[section].append(item)

        # Build flat list in order
        for section in section_order:
            if section in self.sections:
                # Add section header
                self.items.append(
                    MenuItem(
                        key=f"__section__{section}",
                        label=section_titles.get(section, section),
                        description=section_descriptions.get(section, ""),
                        current_value="",
                        item_type="section",
                        section=section,
                    )
                )
                # Add settings in this section
                self.items.extend(self.sections[section])

        # Add action items
        self.items.append(
            MenuItem(
                key="__action__reset",
                label="Reset to Defaults",
                description="Reset all settings and preferences to their default values",
                current_value="",
                item_type="action",
            )
        )
        self.items.append(
            MenuItem(
                key="__action__exit",
                label="Exit",
                description="Leave the configuration editor without saving",
                current_value="",
                item_type="action",
            )
        )

        # Start with the first selectable item rather than a section header.
        self.selected_index = self._first_selectable_index()

    def _get_section(self, key: str) -> str:
        """Get the section name for a setting key."""
        if key.startswith("provider."):
            return "provider"
        if key.startswith("credential_backend."):
            return "credential_backend"
        if key == "poll_interval_seconds":
            return "watch"
        if key == "hotkey":
            return "hotkeys"
        if key.startswith("preferences."):
            return "preferences"
        return "other"

    def _get_label(self, key: str) -> str:
        """Get a human-readable label for a setting key."""
        labels = {
            "provider.provider_id": "Provider ID",
            "provider.account": "Account",
            "credential_backend.backend": "Backend",
            "poll_interval_seconds": "Poll Interval",
            "hotkey": "Hotkey",
            "preferences.theme": "Theme",
            "preferences.notifications_enabled": "Notifications",
            "preferences.auto_paste_enabled": "Auto Paste",
        }
        return labels.get(key, key)

    def _get_description(self, key: str) -> str:
        """Get a description for a setting key."""
        descriptions = {
            "provider.provider_id": "Active email provider (currently only 'gmail')",
            "provider.account": "Email account for OTP fetching",
            "credential_backend.backend": "Credential storage backend (currently only 'keyring')",
            "poll_interval_seconds": "Polling interval in seconds (1-3600)",
            "hotkey": "Global hotkey combination (press to capture)",
            "preferences.theme": "UI theme: system, light, or dark",
            "preferences.notifications_enabled": "Enable desktop notifications",
            "preferences.auto_paste_enabled": "Auto-paste OTP after copying",
        }
        return descriptions.get(key, "")

    def _first_selectable_index(self) -> int:
        """Return the index of the first non-section item, or 0 when empty."""
        for index, item in enumerate(self.items):
            if item.item_type != "section":
                return index
        return 0

    def move_up(self) -> None:
        """Move selection up, skipping section headers."""
        target = self.selected_index - 1
        while target >= 0 and self.items[target].item_type == "section":
            target -= 1
        if target >= 0:
            self.selected_index = target

    def move_down(self) -> None:
        """Move selection down, skipping section headers."""
        target = self.selected_index + 1
        while target < len(self.items) and self.items[target].item_type == "section":
            target += 1
        if target < len(self.items):
            self.selected_index = target

    def get_selected(self) -> MenuItem | None:
        """Get the currently selected item."""
        if 0 <= self.selected_index < len(self.items):
            item = self.items[self.selected_index]
            if item.item_type != "section":
                return item
        return None

    def render(self) -> ConsoleRenderable:
        """Render the menu."""
        lines = []

        for i, item in enumerate(self.items):
            is_selected = i == self.selected_index
            prefix = "▶ " if is_selected else "  "

            if item.item_type == "section":
                style = Style(bold=True, color="blue")
                text = Text(f"{prefix}{item.label}")
                text.stylize(style)
                if is_selected:
                    text.stylize(Style(reverse=True))
                lines.append(text)
                if item.description:
                    desc_text = Text(f"    {item.description}", style="dim")
                    lines.append(desc_text)
            elif item.item_type == "action":
                style = Style(bold=True, color="red") if is_selected else Style()
                text = Text(f"{prefix}{item.label}")
                text.stylize(style)
                if is_selected:
                    text.stylize(Style(reverse=True))
                lines.append(text)
                if item.description:
                    desc_text = Text(f"    {item.description}", style="dim")
                    lines.append(desc_text)
            else:
                # Setting item
                if is_selected:
                    style = Style(reverse=True)
                else:
                    style = Style()

                label_part = f"{prefix}{item.label}"
                value_part = f" {item.current_value}" if item.current_value else ""

                text = Text()
                text.append(label_part, style)
                text.append(value_part, Style(color="cyan"))
                if is_selected:
                    text.stylize(Style(reverse=True))
                lines.append(text)

        return Align.left(Text("\n").join(lines))


class InputDialog:
    """Dialog for text/numeric input."""

    def __init__(self, console: Console) -> None:
        self.console = console
        self.buffer = ""
        self.cursor_pos = 0
        self.error: str | None = None

    def render(self, title: str, prompt: str, current_value: str = "") -> ConsoleRenderable:
        """Render the input dialog."""
        content = Text()
        content.append(f"{prompt}\n\n")
        content.append(f"Current: {current_value or '(empty)'}\n\n", Style(color="grey50"))
        content.append("> ", Style(bold=True, color="green"))
        content.append(self.buffer[:self.cursor_pos], Style(color="white"))
        text_style = Style(bgcolor="grey19", color="white")
        content.append("▌", text_style)
        content.append(self.buffer[self.cursor_pos:], Style(color="white"))
        content.append("\n\n")
        if self.error:
            content.append(f"Error: {self.error}\n\n", Style(color="red"))
        content.append("Enter to confirm • Esc to cancel", Style(dim=True))

        return Panel(content, title=title, border_style="blue", padding=(1, 2))

    def handle_key(self, event: Any) -> str | None:
        """Handle a key event. Returns the confirmed value or None.

        The event is expected to be a :class:`KeyEvent` instance from
        :mod:`otpilot.infrastructure.terminal.keyboard`.  The original
        implementation compared ``event.key`` to string literals which
        never matched.  The updated logic uses the ``Key`` enum values.
        """
        key = event.key
        if key == Key.CHAR and event.char:
            self.buffer = self.buffer[:self.cursor_pos] + event.char + self.buffer[self.cursor_pos:]
            self.cursor_pos += 1
        elif key == Key.BACKSPACE and self.cursor_pos > 0:
            self.buffer = self.buffer[:self.cursor_pos - 1] + self.buffer[self.cursor_pos:]
            self.cursor_pos -= 1
        elif key == Key.LEFT and self.cursor_pos > 0:
            self.cursor_pos -= 1
        elif key == Key.RIGHT and self.cursor_pos < len(self.buffer):
            self.cursor_pos += 1
        elif key == Key.ENTER:
            return self.buffer
        elif key == Key.ESCAPE:
            return "CANCEL"
        return None


class SelectionDialog:
    """Dialog for selecting from a list of options (enum/boolean)."""

    def __init__(self, console: Console) -> None:
        self.console = console
        self.selected_index = 0
        self.options: list[tuple[str, str]] = []
        self.error: str | None = None

    def render(self, title: str, prompt: str, options: list[tuple[str, str]], current_value: str) -> ConsoleRenderable:
        """Render the selection dialog."""
        content = Text()
        content.append(f"{prompt}\n\n")
        content.append(f"Current: {current_value}\n\n", Style(dim=True))

        for i, (value, label) in enumerate(options):
            is_selected = i == self.selected_index
            prefix = "▶ " if is_selected else "  "
            style = Style(reverse=True) if is_selected else Style()
            text = Text()
            text.append(f"{prefix}{label}", style)
            text.append(f" ({value})", Style(color="cyan"))
            if is_selected:
                text.stylize(Style(reverse=True))
            content.append_text(text)
            content.append("\n")

        content.append("\n")
        if self.error:
            content.append(f"Error: {self.error}\n\n", Style(color="red"))
        content.append("↑/↓ to navigate • Enter to select • Esc to cancel", Style(dim=True))

        return Panel(content, title=title, border_style="blue", padding=(1, 2))

    def handle_key(self, event: Any) -> str | None:
        """Handle a key event. Returns the selected value or None."""
        key = event.key
        if key == Key.UP:
            if self.selected_index > 0:
                self.selected_index -= 1
        elif key == Key.DOWN:
            if self.selected_index < len(self.options) - 1:
                self.selected_index += 1
        elif key == Key.ENTER:
            if not self.options:
                return None
            return self.options[self.selected_index][0]
        elif key == Key.ESCAPE:
            return "CANCEL"
        return None

    def set_options(self, options: list[tuple[str, str]], current: str | None = None) -> None:
        """Set the options for selection, preselecting ``current`` when present."""
        self.options = options
        self.error = None
        self.selected_index = 0
        if current is not None:
            for index, (value, _) in enumerate(options):
                if value == current:
                    self.selected_index = index
                    break


class ConfirmDialog:
    """Simple confirmation dialog."""

    def __init__(self, console: Console) -> None:
        self.console = console
        self.selected = 0  # 0 = Yes, 1 = No

    def render(self, title: str, message: str) -> ConsoleRenderable:
        """Render the confirmation dialog."""
        content = Text()
        content.append(f"{message}\n\n")

        yes_style = Style(reverse=True) if self.selected == 0 else Style()
        no_style = Style(reverse=True) if self.selected == 1 else Style()

        content.append("  [Yes]  ", yes_style)
        content.append("  [No]  ", no_style)
        content.append("\n\n")
        content.append("←/→ to navigate • Enter to confirm", Style(dim=True))

        return Panel(content, title=title, border_style="yellow", padding=(1, 2))

    def handle_key(self, event: Any) -> bool | None:
        """Handle a key event. Returns True for Yes, False for No, None for cancel."""
        key = event.key
        if key == Key.LEFT:
            self.selected = 0
        elif key == Key.RIGHT:
            self.selected = 1
        elif key == Key.ENTER:
            return self.selected == 0
        elif key == Key.ESCAPE:
            return None
        return None