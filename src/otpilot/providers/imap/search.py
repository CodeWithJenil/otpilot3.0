"""Generic IMAP search strategy implementation boundary."""

from datetime import UTC

from otpilot.domain.search import SearchCriteria, SearchQuery, SearchStrategy


class ImapSearchStrategy(SearchStrategy):
    name = "imap-default"

    def build(self, criteria: SearchCriteria) -> SearchQuery:
        terms: list[str] = []
        if criteria.unseen_only:
            terms.append("UNSEEN")
        if criteria.since is not None:
            terms.extend(["SINCE", criteria.since.astimezone(UTC).strftime("%d-%b-%Y")])
        if criteria.sender:
            terms.extend(["FROM", criteria.sender])
        if criteria.subject_contains:
            terms.extend(["SUBJECT", criteria.subject_contains])
        if criteria.recipient:
            terms.extend(["TO", criteria.recipient])
        if criteria.body_contains:
            terms.extend(["BODY", criteria.body_contains])
        return SearchQuery(terms=tuple(terms or ["ALL"]))

