"""Candidate generation and scoring for common email OTP messages."""

import re
from dataclasses import replace
from html import unescape
from html.parser import HTMLParser

from otpilot.domain.extraction import CandidateGenerator, CandidateScorer, ExtractableEmail
from otpilot.domain.models import OtpCandidate

OTP_PATTERN = re.compile(r"(?<!\d)(\d{4,8})(?!\d)")
OTP_WORDS = ("otp", "verification", "verify", "code", "security", "passcode", "one-time")
NEGATIVE_WORDS = (
    "invoice",
    "order",
    "receipt",
    "shipment",
    "tracking",
    "transaction",
    "newsletter",
)


class _HtmlTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag in {"script", "style"}:
            self._ignored_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self._ignored_depth:
            self._ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth:
            self.parts.append(data)


def _html_text(value: str) -> str:
    parser = _HtmlTextExtractor()
    try:
        parser.feed(value)
        parser.close()
    except Exception:
        return ""
    return unescape(" ".join(parser.parts))


def _content(email: ExtractableEmail) -> str:
    html = _html_text(email.html_body or "")
    return f"{email.subject or ''}\n{email.text_body}\n{html}"


def _has_otp_context(content: str, value: str) -> bool:
    escaped = re.escape(value)
    return bool(
        re.search(
            rf"(?:otp|passcode|verification(?:\s+code)?|security\s+code|one-time\s+code|code)"
            rf"\D{{0,24}}\b{escaped}\b",
            content,
            re.IGNORECASE,
        )
        or re.search(
            rf"\b{escaped}\b\s*(?:is|:|-)?\s*(?:your\s+)?"
            rf"(?:otp|passcode|verification(?:\s+code)?|security\s+code|one-time\s+code|code)",
            content,
            re.IGNORECASE,
        )
    )


class EmailOtpCandidateGenerator(CandidateGenerator):
    def generate(self, email: ExtractableEmail) -> list[OtpCandidate]:
        content = _content(email)
        candidates: list[OtpCandidate] = []
        for match in OTP_PATTERN.finditer(content):
            value = match.group(1)
            if len(set(value)) == 1 or value in {"0000", "00000", "000000", "0000000", "00000000"}:
                continue
            if value.startswith(("19", "20")) and len(value) == 8:
                continue
            if not _has_otp_context(content, value):
                continue
            candidates.append(
                OtpCandidate(
                    value=value,
                    score=0.0,
                    source=email.source,
                    reason="numeric token in email content",
                )
            )
        return candidates


class ContextOtpCandidateScorer(CandidateScorer):
    def score(self, email: ExtractableEmail, candidate: OtpCandidate) -> OtpCandidate:
        content = _content(email).lower()
        position = content.find(candidate.value.lower())
        window = content[max(0, position - 80) : position + len(candidate.value) + 80]
        score = 1.0
        if _has_otp_context(content, candidate.value):
            score += 8.0
        score += sum(1.0 for word in OTP_WORDS if word in window)
        if len(candidate.value) == 6:
            score += 1.0
        if email.subject and any(word in email.subject.lower() for word in OTP_WORDS):
            score += 2.0
        sender = (email.sender or "").lower()
        subject = (email.subject or "").lower()
        score += sum(1.0 for word in ("security", "verify", "auth", "account") if word in sender)
        score -= 3.0 * sum(1 for word in NEGATIVE_WORDS if word in subject)
        score -= 2.0 * sum(1 for word in NEGATIVE_WORDS if word in sender)
        return replace(candidate, score=score, reason="OTP-related context near numeric token")
