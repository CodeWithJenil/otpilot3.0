# Installation

## Requirements

- Python 3.12 or newer.
- Windows for the first production credential backend.
- A Gmail account with IMAP enabled and a Google App Password for the first provider target.

## Development Installation

```bash
python -m pip install -e ".[dev]"
```

## Runtime Installation

OTPilot is not published to PyPI in this scaffold phase. When packaged, the runtime install command will be:

```bash
python -m pip install otpilot
```

## Verify Installation

```bash
otpilot version
otpilot doctor
```

In this scaffold phase, `doctor` reports that diagnostics are not implemented yet.

