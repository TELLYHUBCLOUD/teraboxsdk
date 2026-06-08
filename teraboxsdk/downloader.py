"""Chunked file downloader with sync and async support + progress tracking."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Protocol

from .exceptions import TeraBoxDownloadError

__all__ = [
    "DownloadProgress",
    "ProgressCallback",
    "ChunkedDownloader",
    "AsyncChunkedDownloader",
]

logger = logging.getLogger(__name__)


class ProgressCallback(Protocol):
    """Protocol for progress callback functions."""

    def __call__(self, percentage: float, downloaded: int, total: int) -> Any:
        ...


@dataclass
class DownloadProgress:
    """Tracks download progress and calculates speed/ETA."""

    total: int
    downloaded: int = 0
    start_time: float = field(default_factory=time.time)
    last_update: float = field(default_factory=time.time)
    speed: float = 0.0  # bytes/sec

    @property
    def percentage(self) -> float:
        if self.total <= 0:
            return 0.0
        return min(100.0, (self.downloaded / self.total) * 100)

    @property
    def remaining(self) -> int:
        return max(0, self.total - self.downloaded)

    @property
    def eta_seconds(self) -> float:
        if self.speed <= 0:
            return float("inf")
        return self.remaining / self.speed

    @property
    def is_complete(self) -> bool:
        return self.total > 0 and self.downloaded >= self.total

    def update(self, chunk_size: int) -> None:
        self.downloaded += chunk_size
        now = time.time()
        elapsed = now - self.last_update
        if elapsed > 0:
            self.speed = chunk_size / elapsed
        self.last_update = now

    def __str__(self) -> str:
        pct = self.percentage
        speed_str = f"{self.speed / 1024:.1f} KB/s" if self.speed > 0 else "N/A"
        eta_str = f"{self.eta_seconds:.0f}s" if self.eta_seconds != float("inf") else "N/A"
        return f"{pct:.1f}% | {self.downloaded}/{self.total} | {speed_str} | ETA {eta_str}"


class ChunkedDownloader:
    """Synchronous chunked downloader with resume support."""

    def __init__(
        self,
        http_client: Any,
        chunk_size: int = 64 * 1024,  # 64 KB
    ) -> None:
        self.http = http_client
        self.chunk_size = chunk_size

    def download(
        self,
        url: str,
        dest: str | Path,
        *,
        total_size: int = 0,
        progress_callback: ProgressCallback | None = None,
        headers: dict[str, str] | None = None,
    ) -> Path:
        """Download file with progress tracking and resume.

        Args:
            url: Direct download URL.
            dest: Destination path.
            total_size: Expected file size (for progress).
            progress_callback: Optional callback(percentage, downloaded, total).
            headers: Additional HTTP headers.

        Returns:
            Path to downloaded file.
        """
        dest_path = Path(dest)
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        # Check for partial download
        downloaded = dest_path.stat().st_size if dest_path.exists() else 0
        progress = DownloadProgress(total=total_size)
        progress.downloaded = downloaded

        req_headers = {**(headers or {})}
        if downloaded > 0:
            req_headers["Range"] = f"bytes={downloaded}-"
            logger.info("Resuming download from byte %d", downloaded)

        logger.info("Starting download: %s -> %s", url, dest_path)
        start = time.time()

        try:
            for chunk in self.http.stream(url, headers=req_headers):
                with open(dest_path, "ab") as f:
                    f.write(chunk)
                progress.update(len(chunk))

                if progress_callback:
                    progress_callback(
                        progress.percentage, progress.downloaded, progress.total
                    )

        except Exception as exc:
            raise TeraBoxDownloadError(
                f"Download failed: {exc}",
                url=url,
                downloaded_bytes=progress.downloaded,
                total_bytes=total_size,
            ) from exc

        elapsed = time.time() - start
        speed = progress.downloaded / elapsed if elapsed > 0 else 0
        logger.info(
            "Download complete: %s (%s in %.1fs @ %.1f KB/s)",
            dest_path,
            progress,
            elapsed,
            speed / 1024,
        )
        return dest_path


class AsyncChunkedDownloader:
    """Asynchronous chunked downloader with resume support."""

    def __init__(
        self,
        http_client: Any,
        chunk_size: int = 64 * 1024,
    ) -> None:
        self.http = http_client
        self.chunk_size = chunk_size

    async def download(
        self,
        url: str,
        dest: str | Path,
        *,
        total_size: int = 0,
        progress_callback: ProgressCallback | None = None,
        headers: dict[str, str] | None = None,
    ) -> Path:
        """Download file asynchronously with progress tracking.

        Args:
            url: Direct download URL.
            dest: Destination path.
            total_size: Expected file size.
            progress_callback: Optional async callback(percentage, downloaded, total).
            headers: Additional HTTP headers.

        Returns:
            Path to downloaded file.
        """
        dest_path = Path(dest)
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        downloaded = dest_path.stat().st_size if dest_path.exists() else 0
        progress = DownloadProgress(total=total_size)
        progress.downloaded = downloaded

        req_headers = {**(headers or {})}
        if downloaded > 0:
            req_headers["Range"] = f"bytes={downloaded}-"
            logger.info("Resuming download from byte %d", downloaded)

        logger.info("Starting async download: %s -> %s", url, dest_path)
        start = time.time()

        try:
            async for chunk in self.http.stream(url, headers=req_headers):
                with open(dest_path, "ab") as f:
                    f.write(chunk)
                progress.update(len(chunk))

                if progress_callback:
                    result = progress_callback(
                        progress.percentage, progress.downloaded, progress.total
                    )
                    if hasattr(result, "__await__"):
                        await result

        except Exception as exc:
            raise TeraBoxDownloadError(
                f"Download failed: {exc}",
                url=url,
                downloaded_bytes=progress.downloaded,
                total_bytes=total_size,
            ) from exc

        elapsed = time.time() - start
        speed = progress.downloaded / elapsed if elapsed > 0 else 0
        logger.info(
            "Download complete: %s (%s in %.1fs @ %.1f KB/s)",
            dest_path,
            progress,
            elapsed,
            speed / 1024,
        )
        return dest_path
