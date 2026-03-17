class CSQAQClientError(Exception):
    """Base exception for CSQAQ API client."""

    def __init__(self, message: str, status_code: int | None = None):
        self.status_code = status_code
        super().__init__(message)


class CSQAQAuthError(CSQAQClientError):
    """401/403 — token invalid or IP not bound."""


class CSQAQValidationError(CSQAQClientError):
    """422 — request parameters invalid."""


class CSQAQRateLimitError(CSQAQClientError):
    """429 — rate limit exceeded."""


class CSQAQServerError(CSQAQClientError):
    """5xx — CSQAQ server error."""
