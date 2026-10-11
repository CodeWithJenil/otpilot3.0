"""Built-in provider registry composition."""

from otpilot.domain.providers import ProviderRegistry
from otpilot.providers.gmail.config import create_gmail_provider


def build_provider_registry(session_renewal_hours: float = 23.0) -> ProviderRegistry:
    registry = ProviderRegistry()
    registry.register(create_gmail_provider(session_renewal_hours=session_renewal_hours))
    return registry

