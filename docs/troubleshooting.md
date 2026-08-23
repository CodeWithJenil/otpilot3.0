# Troubleshooting

## Watch mode stops immediately

Watch mode requires an active account and stored credentials. Run `otpilot login <email>` first.

Use `Ctrl+C` to stop a running watch session cleanly.

## Gmail login does not work

Confirm that the Windows credential backend is available and that the account uses a Gmail App Password.

## IMAP fetch does not work

Temporary provider failures are retried by watch mode. Missing configuration or credentials are fatal and stop the command.

## Clipboard copy does not work

`otpilot fetch --copy` and `otpilot watch` require an operating-system clipboard backend supported by `pyperclip`.

## Documentation looks stale

Open an issue or pull request. Public behavior changes are incomplete unless the relevant documentation is updated.
