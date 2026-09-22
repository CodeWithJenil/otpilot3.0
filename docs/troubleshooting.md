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

## Hotkey does not start or respond

`otpilot hotkey` is supported only on Windows and requires the configured `pynput` package.
Use a valid combination such as `ctrl+shift+o`, ensure no other program owns the combination,
and run `otpilot login <email>` before starting the listener. A fetch failure is reported without
stopping the listener; press `Ctrl+C` to stop it cleanly.

## Documentation looks stale

Open an issue or pull request. Public behavior changes are incomplete unless the relevant documentation is updated.
