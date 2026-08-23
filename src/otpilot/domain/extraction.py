"""OTP extraction pipeline contracts.

Extraction is modeled as candidate generation, scoring, and selection. The concrete
algorithm is intentionally deferred so OTPilot can evolve beyond regex-only matching.
"""

from dataclasses import dataclass
from typing import Protocol

from otpilot.domain.models import EmailMessageRef, OtpCandidate


@dataclass(frozen=True, slots=True)
class ExtractableEmail:
    source: EmailMessageRef
    sender: str | None
    subject: str | None
    text_body: str
    html_body: str | None = None


class CandidateGenerator(Protocol):
    def generate(self, email: ExtractableEmail) -> list[OtpCandidate]:
        """Return possible OTP candidates from an email."""


class CandidateScorer(Protocol):
    def score(self, email: ExtractableEmail, candidate: OtpCandidate) -> OtpCandidate:
        """Return a candidate with an updated probability score."""


class OtpExtractor:
    """Coordinates extraction from email content into the highest-confidence OTP."""

    def __init__(
        self,
        candidate_generator: CandidateGenerator,
        candidate_scorer: CandidateScorer,
    ) -> None:
        self._candidate_generator = candidate_generator
        self._candidate_scorer = candidate_scorer

    def extract_best(self, email: ExtractableEmail) -> OtpCandidate | None:
        candidates = self._candidate_generator.generate(email)
        scored = [self._candidate_scorer.score(email, candidate) for candidate in candidates]
        return max(scored, key=lambda candidate: candidate.score, default=None)

