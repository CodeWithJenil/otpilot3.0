"""Generic IMAP provider boundary.

This module owns IMAP transport concerns. Gmail, Outlook, Yahoo, Proton Bridge,
and custom servers should configure this provider instead of duplicating transport code.
"""

import logging
import random
import time
from collections.abc import Generator, Iterable, Iterator, Mapping
from contextlib import contextmanager, suppress
from dataclasses import dataclass, field
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

logger = logging.getLogger(__name__)

IMAP_OPERATION_ERRORS = (OSError, TimeoutError, IMAPClient.Error, IMAPClient.AbortError)

# How long (seconds) each IDLE session runs before we exit, re-sync, and re-enter.
# This is a *defensive* refresh, not the Gmail 24h session renewal interval.
_IDLE_REFRESH_SECONDS: int = 300  # 5 minutes

# Backoff configuration for transient errors during IDLE.
_BACKOFF_BASE: float = 1.0
_BACKOFF_MAX: float = 60.0


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
    session_renewal_hours: float = field(default=23.0)

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

    def idle_fetch(
        self,
        account_id: AccountId,
        criteria: SearchCriteria,
    ) -> Generator[ExtractableEmail, None, None]:
        """Monitor the mailbox with IMAP IDLE and yield each new message as it arrives.

        This is a long-running generator intended for the daemon's watch loop.
        It:
        - Maintains a single persistent IMAP connection.
        - Enters IDLE mode and waits for server notifications.
        - Exits IDLE every ``_IDLE_REFRESH_SECONDS`` (5 min) to re-sync missed
          messages and avoid server-enforced IDLE limits.
        - Reconnects after ``session_renewal_hours`` (default 23 h) to stay well
          under Gmail's ~24 h session limit.
        - Uses exponential backoff with jitter on transient connection errors.
        - Tracks ``last_seen_uid`` across reconnections so no message is processed
          twice and no message is missed.
        - Never logs OTP values, email bodies, passwords, or other sensitive data.

        The generator runs indefinitely; callers stop it by closing the generator
        or by catching ``StopIteration`` after the caller's own shutdown signal.
        """
        if self._credentials is None:
            raise ImapTransportError("IMAP provider is not authenticated.")

        username, app_password = self._credentials
        renewal_seconds: float = self.session_renewal_hours * 3600
        last_seen_uid: int = 0
        backoff: float = _BACKOFF_BASE
        session_start = datetime.now(UTC)

        while True:
            # ── Proactive session renewal ────────────────────────────────────
            if (datetime.now(UTC) - session_start).total_seconds() >= renewal_seconds:
                logger.info(
                    "IMAP IDLE: session renewal threshold reached (%.0f h); reconnecting.",
                    self.session_renewal_hours,
                )
                session_start = datetime.now(UTC)

            try:
                with self._client_raw(username, app_password) as client:
                    # ── Select mailbox ────────────────────────────────────────
                    try:
                        client.select_folder(self.connection.mailbox, readonly=True)
                    except IMAP_OPERATION_ERRORS as exc:
                        raise ImapTransportError(
                            "Unable to select the configured IMAP mailbox."
                        ) from exc

                    # ── Initial sync: establish baseline UID ─────────────────
                    if last_seen_uid == 0:
                        try:
                            existing_uids: list[int] = list(client.search(["UID", "1:*"]))
                            if existing_uids:
                                last_seen_uid = max(existing_uids)
                            logger.debug(
                                "IMAP IDLE: initial sync complete; baseline UID = %d.", last_seen_uid
                            )
                        except IMAP_OPERATION_ERRORS:
                            pass  # Non-fatal; we will process everything from UID 1

                    # ── IDLE loop ─────────────────────────────────────────────
                    while True:
                        # Check whether session renewal is due before next IDLE round.
                        elapsed = (datetime.now(UTC) - session_start).total_seconds()
                        if elapsed >= renewal_seconds:
                            logger.info(
                                "IMAP IDLE: %.0f h elapsed; breaking to reconnect.",
                                elapsed / 3600,
                            )
                            break  # Break inner loop → reconnect via outer loop.

                        # Enter IDLE for up to _IDLE_REFRESH_SECONDS seconds.
                        try:
                            client.idle()
                            responses = client.idle_check(timeout=_IDLE_REFRESH_SECONDS)
                            client.idle_done()
                        except IMAP_OPERATION_ERRORS as exc:
                            logger.warning("IMAP IDLE: connection error during IDLE: %s", exc)
                            break  # reconnect

                        # Check for new messages regardless of response type.
                        # Some servers send EXISTS on new mail; others send RECENT.
                        # We always re-query by UID to avoid missing anything.
                        try:
                            if last_seen_uid > 0:
                                search_term = ["UID", f"{last_seen_uid + 1}:*"]
                            else:
                                search_term = ["UID", "1:*"]
                            new_uids: list[int] = list(client.search(search_term))
                        except IMAP_OPERATION_ERRORS as exc:
                            logger.warning("IMAP IDLE: UID search failed: %s", exc)
                            break  # reconnect

                        if new_uids:
                            logger.debug("IMAP IDLE: %d new message(s) detected.", len(new_uids))
                            try:
                                fetched = client.fetch(new_uids, [b"RFC822", b"INTERNALDATE"])
                            except IMAP_OPERATION_ERRORS as exc:
                                logger.warning("IMAP IDLE: fetch failed: %s", exc)
                                break  # reconnect

                            if isinstance(fetched, Mapping):
                                for uid, data in sorted(fetched.items()):
                                    if not isinstance(data, Mapping):
                                        continue
                                    try:
                                        email = self._to_extractable(account_id, uid, data)
                                        yield email
                                    except (ImapTransportError, TypeError, ValueError):
                                        pass
                            if new_uids:
                                last_seen_uid = max(new_uids)

                        # Reset backoff on successful round.
                        backoff = _BACKOFF_BASE

            except ImapTransportError as exc:
                # Permanent credential errors should not be silently retried.
                if "authentication" in str(exc).lower():
                    logger.error("IMAP IDLE: authentication failed; stopping: %s", exc)
                    raise

                # Transient connection errors: back off and retry.
                jitter = random.uniform(0, backoff * 0.5)
                sleep_secs = min(backoff + jitter, _BACKOFF_MAX)
                logger.warning(
                    "IMAP IDLE: transient error (%s); reconnecting in %.1f s.", exc, sleep_secs
                )
                time.sleep(sleep_secs)
                backoff = min(backoff * 2, _BACKOFF_MAX)

    @contextmanager
    def _client_raw(self, username: str, app_password: str) -> Iterator[IMAPClient]:
        """Open a raw IMAPClient without selecting a folder (caller does that)."""
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
            yield client
        finally:
            if client is not None:
                with suppress(Exception):
                    client.logout()

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
