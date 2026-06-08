"""Custom exceptions for TeraBox SDK."""

from __future__ import annotations

__all__ = [
    "TeraBoxError",
    "TeraBoxAPIError",
    "TeraBoxDownloadError",
    "TeraBoxURLError",
    "TeraBoxNotFoundError",
    "TeraBoxAuthError",
]


class TeraBoxError(Exception):
    """Base exception for all TeraBox SDK errors."""

    def __init__(self, message: str, *, response_body: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.response_body = response_body

    def __str__(self) -> str:
        if self.response_body:
            return f"{self.message} | Response: {self.response_body[:500]}"
        return self.message


class TeraBoxAPIError(TeraBoxError):
    """Raised when the TeraBox API returns an error response."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        error_code: int | None = None,
        response_body: str | None = None,
    ) -> None:
        super().__init__(message, response_body=response_body)
        self.status_code = status_code
        self.error_code = error_code

    def __str__(self) -> str:
        parts = [self.message]
        if self.status_code:
            parts.append(f"HTTP {self.status_code}")
        if self.error_code:
            parts.append(f"Error Code: {self.error_code}")
        if self.response_body:
            parts.append(f"Response: {self.response_body[:500]}")
        return " | ".join(parts)


class TeraBoxDownloadError(TeraBoxError):
    """Raised when a file download fails."""

    def __init__(
        self,
        message: str,
        *,
        url: str | None = None,
        downloaded_bytes: int = 0,
        total_bytes: int = 0,
        response_body: str | None = None,
    ) -> None:
        super().__init__(message, response_body=response_body)
        self.url = url
        self.downloaded_bytes = downloaded_bytes
        self.total_bytes = total_bytes

    def __str__(self) -> str:
        progress = ""
        if self.total_bytes > 0:
            pct = (self.downloaded_bytes / self.total_bytes) * 100
            progress = f" [{self.downloaded_bytes}/{self.total_bytes} ({pct:.1f}%)]"
        return f"{self.message}{progress}"


class TeraBoxURLError(TeraBoxError):
    """Raised when a TeraBox URL is invalid or cannot be parsed."""

    def __init__(self, message: str, *, url: str | None = None) -> None:
        super().__init__(message)
        self.url = url

    def __str__(self) -> str:
        if self.url:
            return f"{self.message} | URL: {self.url}"
        return self.message


class TeraBoxNotFoundError(TeraBoxAPIError):
    """Raised when a file or folder is not found on TeraBox."""

    def __init__(
        self,
        message: str = "File or folder not found",
        *,
        status_code: int | None = None,
        error_code: int | None = None,
        response_body: str | None = None,
        share_id: str | None = None,
    ) -> None:
        super().__init__(
            message,
            status_code=status_code,
            error_code=error_code,
            response_body=response_body,
        )
        self.share_id = share_id


class TeraBoxAuthError(TeraBoxAPIError):
    """Raised when authentication fails or credentials are invalid."""

    def __init__(
        self,
        message: str = "Authentication failed",
        *,
        status_code: int | None = None,
        error_code: int | None = None,
        response_body: str | None = None,
    ) -> None:
        super().__init__(
            message,
            status_code=status_code,
            error_code=error_code,
            response_body=response_body,
        )
