"""Final safety-net sanitization applied to any model response before
it's returned to the caller, catching PII the model may have
hallucinated or echoed back that wasn't in the original detected set."""
import re
from typing import List, Tuple

# (pattern, replacement) pairs, checked in order
SAFETY_NET_PATTERNS: List[Tuple[str, str]] = [
    (r"\b[0-9]{13}\b", "[ID_REDACTED]"),
    (r"\b(0[6-8][0-9]|0[1-9][0-9]?)[0-9]{7}\b", "[PHONE_REDACTED]"),
    (r"\b[0-9]{4}/[0-9]{6}/[0-9]{2}\b", "[COMPANY_REDACTED]"),
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "[EMAIL_REDACTED]"),
]


def sanitize(text: str) -> str:
    """Apply the safety-net regex patterns to a piece of model output text."""
    sanitized = text
    for pattern, replacement in SAFETY_NET_PATTERNS:
        sanitized = re.sub(pattern, replacement, sanitized)
    return sanitized
