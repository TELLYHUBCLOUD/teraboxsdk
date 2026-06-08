from __future__ import annotations

from pathlib import Path

import pytest

from teraboxsdk.downloader import AsyncChunkedDownloader, ChunkedDownloader
from teraboxsdk.exceptions import TeraBoxDownloadError


class MockHTTPClient:
    def __init__(self, chunks: list[bytes]):
        self.chunks = chunks
        self.called_url = None
        self.called_headers = None
        self.called_chunk_size = None

    def stream(self, url: str, headers: dict[str, str] | None = None, chunk_size: int = 8192):
        self.called_url = url
        self.called_headers = headers
        self.called_chunk_size = chunk_size
        return iter(self.chunks)

class MockAsyncHTTPClient:
    def __init__(self, chunks: list[bytes]):
        self.chunks = chunks
        self.called_url = None
        self.called_headers = None
        self.called_chunk_size = None

    async def stream(self, url: str, headers: dict[str, str] | None = None, chunk_size: int = 8192):
        self.called_url = url
        self.called_headers = headers
        self.called_chunk_size = chunk_size
        for chunk in self.chunks:
            yield chunk


def test_chunked_downloader_basic(tmp_path: Path) -> None:
    client = MockHTTPClient([b"hello ", b"world"])
    downloader = ChunkedDownloader(client, chunk_size=1024)
    dest = tmp_path / "test.txt"

    progress_calls = []
    def callback(pct: float, downloaded: int, total: int) -> None:
        progress_calls.append((pct, downloaded, total))

    res = downloader.download(
        "https://example.com/dl",
        dest,
        total_size=11,
        progress_callback=callback
    )

    assert res == dest
    assert dest.read_bytes() == b"hello world"
    assert client.called_url == "https://example.com/dl"
    assert client.called_chunk_size == 1024
    assert len(progress_calls) == 2
    assert progress_calls[-1] == (100.0, 11, 11)


def test_chunked_downloader_already_downloaded(tmp_path: Path) -> None:
    dest = tmp_path / "test.txt"
    dest.write_bytes(b"hello world")

    client = MockHTTPClient([b"new data"])
    downloader = ChunkedDownloader(client)

    res = downloader.download("https://example.com/dl", dest, total_size=11)
    assert res == dest
    assert dest.read_bytes() == b"hello world"
    assert client.called_url is None  # stream not called


def test_chunked_downloader_resume(tmp_path: Path) -> None:
    dest = tmp_path / "test.txt"
    dest.write_bytes(b"hello ")

    client = MockHTTPClient([b"world"])
    downloader = ChunkedDownloader(client)

    res = downloader.download("https://example.com/dl", dest, total_size=11)
    assert res == dest
    assert dest.read_bytes() == b"hello world"
    assert client.called_headers.get("Range") == "bytes=6-"


def test_chunked_downloader_error(tmp_path: Path) -> None:
    class ErrorHTTPClient:
        def stream(self, url: str, headers: dict[str, str] | None = None, chunk_size: int = 8192):
            raise ValueError("Stream failed")

    downloader = ChunkedDownloader(ErrorHTTPClient())
    dest = tmp_path / "test.txt"

    with pytest.raises(TeraBoxDownloadError) as exc_info:
        downloader.download("https://example.com/dl", dest, total_size=100)
    assert "Stream failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_async_chunked_downloader_basic(tmp_path: Path) -> None:
    client = MockAsyncHTTPClient([b"async ", b"hello"])
    downloader = AsyncChunkedDownloader(client, chunk_size=2048)
    dest = tmp_path / "async_test.txt"

    progress_calls = []
    async def callback(pct: float, downloaded: int, total: int) -> None:
        progress_calls.append((pct, downloaded, total))

    res = await downloader.download(
        "https://example.com/dl",
        dest,
        total_size=11,
        progress_callback=callback
    )

    assert res == dest
    assert dest.read_bytes() == b"async hello"
    assert client.called_url == "https://example.com/dl"
    assert client.called_chunk_size == 2048
    assert len(progress_calls) == 2
    assert progress_calls[-1] == (100.0, 11, 11)


@pytest.mark.asyncio
async def test_async_chunked_downloader_already_downloaded(tmp_path: Path) -> None:
    dest = tmp_path / "async_test.txt"
    dest.write_bytes(b"async hello")

    client = MockAsyncHTTPClient([b"more"])
    downloader = AsyncChunkedDownloader(client)

    res = await downloader.download("https://example.com/dl", dest, total_size=11)
    assert res == dest
    assert dest.read_bytes() == b"async hello"
    assert client.called_url is None


@pytest.mark.asyncio
async def test_async_chunked_downloader_resume(tmp_path: Path) -> None:
    dest = tmp_path / "async_test.txt"
    dest.write_bytes(b"async ")

    client = MockAsyncHTTPClient([b"hello"])
    downloader = AsyncChunkedDownloader(client)

    res = await downloader.download("https://example.com/dl", dest, total_size=11)
    assert res == dest
    assert dest.read_bytes() == b"async hello"
    assert client.called_headers.get("Range") == "bytes=6-"


@pytest.mark.asyncio
async def test_async_chunked_downloader_error(tmp_path: Path) -> None:
    class ErrorAsyncHTTPClient:
        async def stream(self, url: str, headers: dict[str, str] | None = None, chunk_size: int = 8192):
            raise ValueError("Async stream failed")
            yield b""  # keep generator type check happy

    downloader = AsyncChunkedDownloader(ErrorAsyncHTTPClient())
    dest = tmp_path / "async_test.txt"

    with pytest.raises(TeraBoxDownloadError) as exc_info:
        await downloader.download("https://example.com/dl", dest, total_size=100)
    assert "Async stream failed" in str(exc_info.value)
