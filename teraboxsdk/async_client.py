"""Asynchronous TeraBox client."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from ._base_client import (
    API_BASE,
    FILE_LIST_ENDPOINT,
    SHARE_ENDPOINT,
    BaseTeraBoxClient,
    _raise_for_status,
)
from .downloader import DownloadProgress
from .exceptions import TeraBoxDownloadError, TeraBoxURLError
from .http import AsyncHTTPClient
from .models import DownloadInfo, FileInfo, FileListing, FolderInfo, UserInfo
from .utils import extract_surl

__all__ = ["AsyncTeraBoxClient"]

logger = logging.getLogger(__name__)


class AsyncTeraBoxClient(BaseTeraBoxClient[AsyncHTTPClient]):
    """Asynchronous TeraBox client for fetching share info and downloading files.

    Usage:
        client = AsyncTeraBoxClient()
        files = await client.get_files("https://terabox.com/s/1ABCDEF")
        await client.download(files[0], "./downloads")
        await client.close()
    """

    def __init__(self, timeout: float = 30.0, proxy: str | None = None) -> None:
        super().__init__(timeout=timeout, proxy=proxy)
        self._http = AsyncHTTPClient(timeout=timeout, proxy=proxy)

    async def _fetch_share_page(self, surl: str) -> str:
        """Fetch the share page HTML to extract tokens."""
        url = f"{API_BASE}/s/{surl}"
        logger.debug("Fetching share page: %s", url)
        resp = await self._http.get(url)
        resp.raise_for_status()
        return resp.text

    async def _get_share_info(
        self, surl: str, password: str | None = None
    ) -> dict[str, Any]:
        """Call shorturlinfo API to validate share."""
        params = self._get_default_params()
        params["shorturl"] = surl
        if password:
            params["pwd"] = password

        resp = await self._http.get(SHARE_ENDPOINT, params=params)
        resp.raise_for_status()
        data = resp.json()
        _raise_for_status(data, resp.status_code)
        return data

    async def get_files(
        self,
        url: str,
        *,
        password: str | None = None,
        page: int = 1,
        limit: int = 100,
    ) -> FileListing:
        """List files in a TeraBox share (async).

        Args:
            url: TeraBox share URL or short code.
            password: Share password if required.
            page: Page number (1-indexed).
            limit: Items per page (max 100).

        Returns:
            FileListing containing FileInfo objects.
        """
        self._check_share_url(url)
        surl = extract_surl(url)
        self._pwd = password

        html = await self._fetch_share_page(surl)
        self._extract_tokens(html)

        await self._get_share_info(surl, password)

        params = self._get_default_params()
        params.update(
            {
                "shorturl": surl,
                "page": page,
                "num": limit,
                "root": "1",
                "fid": "0",
                "order": "time",
                "desc": "1",
                "showempty": "0",
                "uk": self._uk or "",
                "shareid": self._share_id or "",
            }
        )
        if password:
            params["seckey"] = ""
            params["pwd"] = password

        resp = await self._http.get(FILE_LIST_ENDPOINT, params=params)
        resp.raise_for_status()
        data = resp.json()
        _raise_for_status(data, resp.status_code)

        records = data.get("list", [])
        files = [FileInfo.from_api(r) for r in records]

        total_count = data.get("count", len(files))
        has_more = (page * limit) < total_count
        next_cursor = str(page + 1) if has_more else None

        return FileListing(
            files=files, cursor=next_cursor, has_more=has_more, total_count=total_count
        )

    async def get_folder_info(
        self,
        url: str,
        *,
        password: str | None = None,
        recursive: bool = False,
    ) -> FolderInfo:
        """Get folder metadata and contents (async).

        Args:
            url: TeraBox share URL.
            password: Share password if required.
            recursive: Fetch subfolders recursively.

        Returns:
            FolderInfo with files and subfolders.
        """
        listing = await self.get_files(url, password=password)

        files = [f for f in listing.files if not f.is_dir]
        folders = [f for f in listing.files if f.is_dir]

        folder_info = FolderInfo(
            folder_name=listing.files[0].path.split("/")[-1] if listing.files else "root",
            path="/",
            share_id=extract_surl(url),
            uk=self._uk or 0,
            files=files,
        )

        if recursive:
            for folder in folders:
                sub = await self._list_subfolder(folder.fs_id, folder.path)
                folder_info.subfolders.append(sub)

        return folder_info

    async def _list_subfolder(self, fs_id: int, path: str) -> FolderInfo:
        """List contents of a subfolder by fs_id (async)."""
        params = self._get_default_params()
        params.update(
            {
                "dir": path,
                "page": 1,
                "num": 100,
                "order": "time",
                "desc": "1",
                "showempty": "0",
                "uk": self._uk or "",
                "shareid": self._share_id or "",
            }
        )

        resp = await self._http.get(FILE_LIST_ENDPOINT, params=params)
        resp.raise_for_status()
        data = resp.json()
        _raise_for_status(data, resp.status_code)

        records = data.get("list", [])
        files = [FileInfo.from_api(r) for r in records if not r.get("isdir")]
        subfolders = [FileInfo.from_api(r) for r in records if r.get("isdir")]

        folder = FolderInfo(
            folder_name=path.split("/")[-1] or "subfolder",
            path=path,
            share_id=self._share_id or "",
            uk=self._uk or 0,
            files=files,
        )

        for sf in subfolders:
            sub = await self._list_subfolder(sf.fs_id, sf.path)
            folder.subfolders.append(sub)

        return folder

    async def get_download_link(self, file: FileInfo) -> DownloadInfo:
        """Get a direct download link for a file (async).

        Args:
            file: FileInfo object returned from get_files().

        Returns:
            DownloadInfo containing the direct URL.
        """
        params = self._get_download_params(file.fs_id)

        resp = await self._http.get(f"{FILE_LIST_ENDPOINT}/download", params=params)
        resp.raise_for_status()
        data = resp.json()
        _raise_for_status(data, resp.status_code)

        dlink = data.get("dlink", "")
        if not dlink and "list" in data:
            dlink = data["list"][0].get("dlink", "") if data["list"] else ""

        if not dlink:
            raise TeraBoxDownloadError(
                "No download link returned by API",
                downloaded_bytes=0,
                total_bytes=file.size,
            )

        return DownloadInfo(url=dlink, filename=file.name, size=file.size)

    async def download(
        self,
        file: FileInfo,
        dest: str | Path,
        *,
        chunk_size: int = 8192,
        progress_callback: Any = None,
    ) -> Path:
        """Download a file to the specified destination (async).

        Args:
            file: FileInfo to download.
            dest: Destination directory or file path.
            chunk_size: Bytes per chunk.
            progress_callback: Optional async callback(percentage, downloaded, total).

        Returns:
            Path to the downloaded file.
        """
        download_info = await self.get_download_link(file)
        progress = DownloadProgress(file.size)

        dest_path = Path(dest)
        if dest_path.is_dir():
            dest_path = dest_path / file.name

        logger.info("Downloading %s -> %s", file.name, dest_path)
        downloaded = 0

        try:
            async for chunk in self._http.stream(download_info.url):
                if not dest_path.parent.exists():
                    dest_path.parent.mkdir(parents=True, exist_ok=True)

                with open(dest_path, "ab") as f:
                    f.write(chunk)

                downloaded += len(chunk)
                progress.update(len(chunk))

                if progress_callback:
                    if hasattr(progress_callback, "__call__"):
                        result = progress_callback(
                            progress.percentage, progress.downloaded, progress.total
                        )
                        if hasattr(result, "__await__"):
                            await result

        except Exception as exc:
            raise TeraBoxDownloadError(
                f"Download failed: {exc}",
                url=download_info.url,
                downloaded_bytes=downloaded,
                total_bytes=file.size,
            ) from exc

        logger.info("Downloaded %s (%s)", dest_path, download_info.size_human)
        return dest_path

    async def get_user_info(self, url: str) -> UserInfo:
        """Extract user info from a share URL context (async).

        Args:
            url: TeraBox share URL.

        Returns:
            UserInfo with uk and username.
        """
        self._check_share_url(url)
        surl = extract_surl(url)
        html = await self._fetch_share_page(surl)
        self._extract_tokens(html)

        import re

        username_match = re.search(r'"server_filename"\s*:\s*"([^"]+)"', html)
        username = username_match.group(1) if username_match else "unknown"

        return UserInfo(
            uk=self._uk or 0,
            username=username,
        )

    async def close(self) -> None:
        """Close the HTTP client and release resources."""
        await self._http.close()

    async def __aenter__(self) -> AsyncTeraBoxClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()
