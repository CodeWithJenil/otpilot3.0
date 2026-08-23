from otpilot.providers.registry import build_provider_registry


def test_gmail_registers_as_imap_configured_provider() -> None:
    provider = build_provider_registry().get("gmail")
    assert provider is not None
    assert provider.descriptor.supports_imap is True
