"""Candidate generation and scoring for common email OTP messages."""

import re
from dataclasses import replace

from otpilot.domain.extraction import CandidateGenerator, CandidateScorer, ExtractableEmail
from otpilot.domain.models import OtpCandidate

OTP_PATTERN = re.compile(r"(?<!\d)(\d{4,8})(?!\d)")
HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
OTP_WORDS = ("otp", "verification", "verify", "code", "security", "passcode", "one-time")


def _content(email: ExtractableEmail) -> str:
    html = HTML_TAG_PATTERN.sub(" ", email.html_body or "")
    return f"{email.subject or ''}\n{email.text_body}\n{html}"


class EmailOtpCandidateGenerator(CandidateGenerator):
    def generate(self, email: ExtractableEmail) -> list[OtpCandidate]:
        content = _content(email)
        candidates: list[OtpCandidate] = []
        for match in OTP_PATTERN.finditer(content):
            value = match.group(1)
            if len(set(value)) == 1 or value in {"0000", "00000", "000000", "0000000", "00000000"}:
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
        direct_context = re.search(
            rf"(?:otp|code|passcode|verification code|one-time).{{0,24}}"
            rf"\b{re.escape(candidate.value)}\b",
            content,
        )
        if direct_context:
            score += 8.0
        score += sum(1.0 for word in OTP_WORDS if word in window)
        if len(candidate.value) == 6:
            score += 1.0
        if email.subject and any(word in email.subject.lower() for word in OTP_WORDS):
            score += 1.0
        return replace(candidate, score=score, reason="OTP-related context near numeric token")
