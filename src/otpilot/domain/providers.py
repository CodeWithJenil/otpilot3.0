"""Provider contracts and registry."""

from collections.abc import Iterable
from typing import Protocol

from otpilot.domain.extraction import ExtractableEmail
from otpilot.domain.models import AccountId, ProviderDescriptor, ProviderId
from otpilot.domain.search import SearchCriteria


class OtpSourceProvider(Protocol):
    descriptor: ProviderDescriptor

    def authenticate(self, account_id: AccountId, username: str, app_password: str) -> None:
        """Validate stored credentials for an account."""

    def search(self, account_id: AccountId, criteria: SearchCriteria) -> Iterable[ExtractableEmail]:
        """Return only messages that match the active search strategy."""


class ProviderRegistry:
    """Runtime registry for built-in and future providers."""

    def __init__(self) -> None:
        self._providers: dict[ProviderId, OtpSourceProvider] = {}

    def register(self, provider: OtpSourceProvider) -> None:
        self._providers[provider.descriptor.provider_id] = provider

    def get(self, provider_id: ProviderId) -> OtpSourceProvider | None:
        return self._providers.get(provider_id)

    def all(self) -> list[OtpSourceProvider]:
        return list(self._providers.values())
