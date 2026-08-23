from otpilot.infrastructure.logging.setup import redact


def test_redact_masks_secret_like_values() -> None:
    assert "password=[REDACTED]" in redact("password=abc123")
    assert "abc123" not in redact("password=abc123")

