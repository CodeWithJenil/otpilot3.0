"""Built-in provider registry composition."""

from otpilot.domain.providers import ProviderRegistry
from otpilot.providers.gmail.config import create_gmail_provider


def build_provider_registry() -> ProviderRegistry:
    registry = ProviderRegistry()
    registry.register(create_gmail_provider())
    return registry

