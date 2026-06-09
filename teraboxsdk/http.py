"""HTTP client layer with sync and async support via httpx."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import Any

import httpx

__all__ = [
    "HTTPClient",
    "AsyncHTTPClient",
    "DEFAULT_TIMEOUT",
    "DEFAULT_HEADERS",
]

DEFAULT_TIMEOUT = 30.0
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.0 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.0"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}


class HTTPClient:
    """Synchronous HTTP client wrapper around httpx."""

    def __init__(
        self,
        timeout: float = DEFAULT_TIMEOUT,
        headers: dict[str, str] | None = None,
        proxy: str | None = None,
        ndus: str | None = None,
    ) -> None:
        client_headers = {**DEFAULT_HEADERS, **(headers or {})}
        transport = httpx.HTTPTransport(retries=1, http2=True)
        cookies = {"ndus": ndus} if ndus else None
        self._client = httpx.Client(
            headers=client_headers,
            cookies=cookies,
            timeout=httpx.Timeout(timeout),
            transport=transport,
            proxy=proxy,
            follow_redirects=True,
        )

    def get(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Send a GET request."""
        return self._client.get(url, params=params, headers=headers)

    def post(
        self,
        url: str,
        *,
        data: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Send a POST request."""
        return self._client.post(url, data=data, json=json, headers=headers)

    def stream(
        self,
        url: str,
        *,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        chunk_size: int = 8192,
    ) -> Iterator[bytes]:
        """Stream response content as bytes chunks."""
        with self._client.stream(
            method, url, headers=headers, params=params
        ) as response:
            response.raise_for_status()
            yield from response.iter_bytes(chunk_size=chunk_size)

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()

    def __enter__(self) -> HTTPClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


class AsyncHTTPClient:
    """Asynchronous HTTP client wrapper around httpx."""

    def __init__(
        self,
        timeout: float = DEFAULT_TIMEOUT,
        headers: dict[str, str] | None = None,
        proxy: str | None = None,
        ndus: str | None = None,
    ) -> None:
        client_headers = {**DEFAULT_HEADERS, **(headers or {})}
        transport = httpx.AsyncHTTPTransport(retries=1, http2=True)
        cookies = {"ndus": ndus} if ndus else None
        self._client = httpx.AsyncClient(
            headers=client_headers,
            cookies=cookies,
            timeout=httpx.Timeout(timeout),
            transport=transport,
            proxy=proxy,
            follow_redirects=True,
        )

    async def get(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Send an async GET request."""
        return await self._client.get(url, params=params, headers=headers)

    async def post(
        self,
        url: str,
        *,
        data: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Send an async POST request."""
        return await self._client.post(url, data=data, json=json, headers=headers)

    async def stream(
        self,
        url: str,
        *,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        chunk_size: int = 8192,
    ) -> AsyncIterator[bytes]:
        """Stream response content as async bytes chunks."""
        async with self._client.stream(
            method, url, headers=headers, params=params
        ) as response:
            response.raise_for_status()
            async for chunk in response.aiter_bytes(chunk_size=chunk_size):
                yield chunk

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> AsyncHTTPClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()
