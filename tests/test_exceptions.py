"""Tests for teraboxsdk.exceptions module (5 tests)."""

from __future__ import annotations

from teraboxsdk.exceptions import (
    TeraBoxAPIError,
    TeraBoxAuthError,
    TeraBoxDownloadError,
    TeraBoxError,
    TeraBoxNotFoundError,
    TeraBoxURLError,
)


class TestBaseException:
    def test_basic_message(self) -> None:
        exc = TeraBoxError("something went wrong")
        assert str(exc) == "something went wrong"
        assert exc.message == "something went wrong"

    def test_with_response_body(self) -> None:
        exc = TeraBoxError("api failed", response_body='{"errno": -1}')
        assert "api failed" in str(exc)
        assert '{"errno": -1}' in str(exc)


class TestAPIError:
    def test_with_status_and_error_code(self) -> None:
        exc = TeraBoxAPIError(
            "rate limited",
            status_code=429,
            error_code=31034,
            response_body='{"errno": 31034}',
        )
        assert "rate limited" in str(exc)
        assert "HTTP 429" in str(exc)
        assert "Error Code: 31034" in str(exc)


class TestDownloadError:
    def test_progress_display(self) -> None:
        exc = TeraBoxDownloadError(
            "connection reset",
            url="https://example.com/file",
            downloaded_bytes=500,
            total_bytes=1000,
        )
        assert "connection reset" in str(exc)
        assert "50.0%" in str(exc)


class TestNotFoundError:
    def test_default_message(self) -> None:
        exc = TeraBoxNotFoundError(share_id="ABC123")
        assert "File or folder not found" in str(exc)
        assert exc.share_id == "ABC123"

    def test_custom_message(self) -> None:
        exc = TeraBoxNotFoundError("Custom not found", status_code=404, error_code=31066)
        assert exc.status_code == 404
        assert exc.error_code == 31066


class TestURLError:
    def test_with_url(self) -> None:
        exc = TeraBoxURLError("Invalid URL", url="https://bad.url")
        assert "Invalid URL" in str(exc)
        assert "https://bad.url" in str(exc)


class TestAuthError:
    def test_default(self) -> None:
        exc = TeraBoxAuthError()
        assert "Authentication failed" in str(exc)

    def test_custom(self) -> None:
        exc = TeraBoxAuthError("Token expired", status_code=403, error_code=418)
        assert "Token expired" in str(exc)
        assert "HTTP 403" in str(exc)
