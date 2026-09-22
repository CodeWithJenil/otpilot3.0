# Dependency List

## Runtime

- `typer`: CLI command framework.
- `rich`: terminal output formatting.
- `pydantic`: typed config and preference models.
- `pydantic-settings`: future settings loading support.
- `platformdirs`: platform-correct local app paths.
- `keyring`: cross-platform credential backend abstraction.
- `pywin32`: Windows Credential Manager support target.
- `imapclient`: IMAP over SSL client.
- `pyperclip`: clipboard integration target.
- `pynput`: Windows global hotkey registration for `otpilot hotkey`; declared only on Windows
  to keep its OS-specific hook implementation outside the application core.
- `tomli-w`: TOML config writing target.

## Development

- `pytest`: test runner.
- `ruff`: linting and import sorting.
- `mypy`: static type checking.
