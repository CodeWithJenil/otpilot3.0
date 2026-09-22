"""Generic IMAP provider boundary.

This module owns IMAP transport concerns. Gmail, Outlook, Yahoo, Proton Bridge,
and custom servers should configure this provider instead of duplicating transport code.
"""

from collections.abc import Iterable, Iterator, Mapping
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from email import policy
from email.parser import BytesParser
from typing import Any

from imapclient import IMAPClient  # type: ignore[import-untyped]

from otpilot.domain.errors import ImapTransportError
from otpilot.domain.extraction import ExtractableEmail
from otpilot.domain.models import (
    AccountId,
    EmailMessageRef,
    ProviderDescriptor,
    ProviderId,
    ProviderKind,
)
from otpilot.domain.search import SearchCriteria, SearchStrategy

IMAP_OPERATION_ERRORS = (OSError, TimeoutError, IMAPClient.Error, IMAPClient.AbortError)


@dataclass(frozen=True, slots=True)
class ImapConnectionConfig:
    host: str
    port: int = 993
    ssl: bool = True
    mailbox: str = "INBOX"
    timeout_seconds: float = 30.0


def _received_at_sort_key(received_at: datetime | None) -> datetime:
    if received_at is None:
        return datetime.min.replace(tzinfo=UTC)
    if received_at.tzinfo is None:
        return received_at.replace(tzinfo=UTC)
    return received_at.astimezone(UTC)


@dataclass(slots=True)
class ImapProvider:
    descriptor: ProviderDescriptor
    connection: ImapConnectionConfig
    search_strategy: SearchStrategy
    _credentials: tuple[str, str] | None = None

    @classmethod
    def generic(
        cls,
        connection: ImapConnectionConfig,
        search_strategy: SearchStrategy,
    ) -> "ImapProvider":
        return cls(
            descriptor=ProviderDescriptor(
                provider_id=ProviderId("imap"),
                display_name="Custom IMAP",
                kind=ProviderKind.IMAP,
                supports_imap=True,
            ),
            connection=connection,
            search_strategy=search_strategy,
        )

    @contextmanager
    def _client(self, username: str, app_password: str) -> Iterator[IMAPClient]:
        client: IMAPClient | None = None
        try:
            client = IMAPClient(
                self.connection.host,
                port=self.connection.port,
                use_uid=True,
                ssl=self.connection.ssl,
                timeout=self.connection.timeout_seconds,
            )
        except IMAP_OPERATION_ERRORS as exc:
            raise ImapTransportError("Unable to establish an IMAP connection.") from exc
        try:
            try:
                client.login(username, app_password)
            except IMAP_OPERATION_ERRORS as exc:
                raise ImapTransportError("IMAP authentication failed.") from exc
            try:
                client.select_folder(self.connection.mailbox, readonly=True)
            except IMAP_OPERATION_ERRORS as exc:
                raise ImapTransportError("Unable to select the configured IMAP mailbox.") from exc
            yield client
        except IMAP_OPERATION_ERRORS as exc:
            raise ImapTransportError("IMAP operation failed.") from exc
        finally:
            if client is not None:
                with suppress(Exception):
                    client.logout()

    def authenticate(self, account_id: AccountId, username: str, app_password: str) -> None:
        del account_id
        with self._client(username, app_password):
            self._credentials = (username, app_password)

    def search(self, account_id: AccountId, criteria: SearchCriteria) -> Iterable[ExtractableEmail]:
        if self._credentials is None:
            raise ImapTransportError("IMAP provider is not authenticated.")
        username, app_password = self._credentials
        query = self.search_strategy.build(criteria)
        with self._client(username, app_password) as client:
            try:
                message_ids = list(client.search(query.terms))
                message_ids = list(reversed(message_ids))[: criteria.limit]
                fetched = client.fetch(message_ids, [b"RFC822", b"INTERNALDATE"])
                if not isinstance(fetched, Mapping):
                    raise TypeError("IMAP fetch response is not a mapping.")
                emails: list[ExtractableEmail] = []
                for message_id, data in fetched.items():
                    if not isinstance(data, Mapping):
                        continue
                    try:
                        emails.append(self._to_extractable(account_id, message_id, data))
                    except (TypeError, ValueError):
                        continue
                return sorted(
                    emails,
                    key=lambda email: (
                        _received_at_sort_key(email.source.received_at),
                        email.source.message_id,
                    ),
                    reverse=True,
                )
            except ImapTransportError:
                raise
            except (*IMAP_OPERATION_ERRORS, TypeError, ValueError) as exc:
                raise ImapTransportError("IMAP search or message retrieval failed.") from exc

    def _to_extractable(
        self,
        account_id: AccountId,
        message_id: Any,
        data: Mapping[Any, Any],
    ) -> ExtractableEmail:
        raw = data.get(b"RFC822") or data.get("RFC822")
        if not isinstance(raw, bytes):
            raise ImapTransportError("IMAP returned a message without content.")
        message = BytesParser(policy=policy.default).parsebytes(raw)
        text_parts: list[str] = []
        html_parts: list[str] = []
        for part in message.walk():
            if part.is_multipart():
                continue
            try:
                content = part.get_content()
            except (LookupError, TypeError, ValueError):
                continue
            if not isinstance(content, str):
                continue
            if part.get_content_type() == "text/html":
                html_parts.append(content)
            elif part.get_content_type() == "text/plain":
                text_parts.append(content)
        received = data.get(b"INTERNALDATE") or data.get("INTERNALDATE")
        received_at = received if isinstance(received, datetime) else None
        return ExtractableEmail(
            source=EmailMessageRef(
                provider_id=self.descriptor.provider_id,
                account_id=account_id,
                message_id=str(message_id),
                received_at=received_at,
            ),
            sender=message.get("From"),
            subject=message.get("Subject"),
            text_body="\n".join(text_parts),
            html_body="\n".join(html_parts) or None,
        )
