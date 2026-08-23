from otpilot.domain.extraction import ExtractableEmail, OtpExtractor
from otpilot.domain.models import AccountId, EmailMessageRef, ProviderId
from otpilot.domain.otp import ContextOtpCandidateScorer, EmailOtpCandidateGenerator


def make_email(text: str, subject: str = "Notification") -> ExtractableEmail:
    return ExtractableEmail(
        source=EmailMessageRef(ProviderId("gmail"), AccountId("account"), "1"),
        sender="security@example.com",
        subject=subject,
        text_body=text,
    )


def extractor() -> OtpExtractor:
    return OtpExtractor(EmailOtpCandidateGenerator(), ContextOtpCandidateScorer())


def test_normal_otp_email() -> None:
    result = extractor().extract_best(make_email("Your verification code is 482913."))
    assert result is not None
    assert result.value == "482913"


def test_multiple_numeric_values_prefers_otp_context() -> None:
    result = extractor().extract_best(make_email("Order 123456. Your OTP is 482913."))
    assert result is not None
    assert result.value == "482913"


def test_otp_surrounded_by_unrelated_numbers() -> None:
    result = extractor().extract_best(make_email("Invoice 20240101, amount 99. Code: 7312."))
    assert result is not None
    assert result.value == "7312"


def test_invalid_candidate_is_rejected() -> None:
    assert extractor().extract_best(make_email("Your code is 000000.")) is None


def test_no_otp_found() -> None:
    assert extractor().extract_best(make_email("Welcome to the service.")) is None


def test_ambiguous_candidates_use_context_and_length() -> None:
    result = extractor().extract_best(make_email("Reference 123456. Security passcode: 918273."))
    assert result is not None
    assert result.value == "918273"
