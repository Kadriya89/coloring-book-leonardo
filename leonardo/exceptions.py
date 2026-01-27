"""Custom exceptions for Leonardo AI API client."""

from __future__ import annotations


class LeonardoAPIError(Exception):
    """Base exception for Leonardo API errors."""

    def __init__(self, message: str, status_code: int | None = None, response: dict | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response = response or {}

    def __str__(self) -> str:
        if self.status_code:
            return f"[{self.status_code}] {self.message}"
        return self.message


class LeonardoAuthError(LeonardoAPIError):
    """Authentication/authorization error (401/403)."""

    pass


class LeonardoRateLimitError(LeonardoAPIError):
    """Rate limit exceeded (429)."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: int | None = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class LeonardoTimeoutError(LeonardoAPIError):
    """Request or polling timeout."""

    pass


class LeonardoGenerationError(LeonardoAPIError):
    """Generation failed or returned unexpected status."""

    def __init__(self, message: str, generation_id: str | None = None, **kwargs):
        super().__init__(message, **kwargs)
        self.generation_id = generation_id
