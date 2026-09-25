# Installation

## Requirements

- Python 3.12 or newer.
- Supported Operating System: Windows, macOS, or Linux X11 (*Wayland is unsupported*).
- A Gmail account with IMAP enabled and a Google App Password for the first provider target.

## Runtime Installation

Install OTPilot from PyPI:

```bash
pip install otpilot
```

## Development Installation

```bash
python -m pip install -e ".[dev]"
```

## Verify Installation

```bash
otpilot version
otpilot doctor
```

*Note:* `otpilot doctor` is currently a scaffolded command that reports diagnostic status.
