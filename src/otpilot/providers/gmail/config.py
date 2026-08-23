"""Gmail provider configuration layered on the generic IMAP transport."""

from otpilot.domain.models import ProviderDescriptor, ProviderId, ProviderKind
from otpilot.providers.imap.provider import ImapConnectionConfig, ImapProvider
from otpilot.providers.imap.search import ImapSearchStrategy

GMAIL_DESCRIPTOR = ProviderDescriptor(
    provider_id=ProviderId("gmail"),
    display_name="Gmail",
    kind=ProviderKind.IMAP,
    supports_imap=True,
)

GMAIL_IMAP = ImapConnectionConfig(host="imap.gmail.com", port=993, ssl=True, mailbox="INBOX")


def create_gmail_provider() -> ImapProvider:
    return ImapProvider(
        descriptor=GMAIL_DESCRIPTOR,
        connection=GMAIL_IMAP,
        search_strategy=ImapSearchStrategy(),
    )

