"""Shared logic for TeraBox sync and async clients (DRY)."""

from __future__ import annotations

import json
import re
from typing import Any, Generic, TypeVar

from .exceptions import (
    TeraBoxAPIError,
    TeraBoxAuthError,
    TeraBoxNotFoundError,
    TeraBoxURLError,
)

T = TypeVar("T")

__all__ = ["BaseTeraBoxClient"]

# API endpoints
API_BASE = "https://terabox.com"
API_V1 = f"{API_BASE}/api"
SHARE_ENDPOINT = f"{API_V1}/shorturlinfo"
FILE_LIST_ENDPOINT = f"{API_V1}/share/list"
DOWNLOAD_ENDPOINT = f"{API_V1}/sharedownload"

# Regex for extracting jsToken and bdstoken from HTML
_JSTOKEN_RE = re.compile(r'"jsToken"\s*:\s*"([^"]+)"')
_BDSTOKEN_RE = re.compile(r'"bdstoken"\s*:\s*"([^"]+)"')
_LOGID_RE = re.compile(r'"logid"\s*:\s*"([^"]+)"')


def _raise_for_status(data: dict[str, Any], status_code: int) -> None:
    """Raise appropriate exception based on API response."""
    errno = data.get("errno")
    if errno == -3:
        errmsg = "Password required or incorrect password"
    else:
        errmsg = data.get("errmsg", "Unknown API error")

    if status_code == 404 or errno in (31066, 31075, -9):
        raise TeraBoxNotFoundError(
            message=f"File or folder not found: {errmsg}",
            status_code=status_code,
            error_code=errno,
            response_body=json.dumps(data),
        )
    if status_code == 403 or errno in (-3, -6, 401, 418):
        raise TeraBoxAuthError(
            message=f"Authentication failed: {errmsg}",
            status_code=status_code,
            error_code=errno,
            response_body=json.dumps(data),
        )
    if errno and errno != 0:
        raise TeraBoxAPIError(
            message=f"API error: {errmsg}",
            status_code=status_code,
            error_code=errno,
            response_body=json.dumps(data),
        )


class BaseTeraBoxClient(Generic[T]):
    """Base class with shared logic. Concrete classes provide the HTTP client."""

    def __init__(self, timeout: float = 30.0, proxy: str | None = None) -> None:
        self.timeout = timeout
        self.proxy = proxy
        self._js_token: str | None = None
        self._bds_token: str | None = None
        self._log_id: str | None = None
        self._uk: int | None = None
        self._share_uk: int | None = None
        self._share_id: str | None = None
        self._pwd: str | None = None
        self._surl: str | None = None

    def _extract_tokens(self, html: str) -> None:
        """Parse HTML to extract required tokens."""
        if match := _JSTOKEN_RE.search(html):
            self._js_token = match.group(1)
        if match := _BDSTOKEN_RE.search(html):
            self._bds_token = match.group(1)
        if match := _LOGID_RE.search(html):
            self._log_id = match.group(1)

        # Extract share metadata from inline JS
        if share_id_match := re.search(r'[\'"]?shareid[\'"]?\s*[=:]\s*"?(\d+)"?', html):
            self._share_id = share_id_match.group(1)
        if uk_match := re.search(r'[\'"]?uk[\'"]?\s*[=:]\s*"?(\d+)"?', html):
            self._uk = int(uk_match.group(1))
        if share_uk_match := re.search(r'[\'"]?share_uk[\'"]?\s*[=:]\s*"?(\d+)"?', html):
            self._share_uk = int(share_uk_match.group(1))

    def _get_default_params(self) -> dict[str, Any]:
        """Common query parameters for most API calls."""
        params: dict[str, Any] = {
            "app_id": "250528",
            "channel": "dubox",
            "clienttype": "0",
        }
        if self._js_token:
            params["jsToken"] = self._js_token
        if self._log_id:
            params["dp-logid"] = self._log_id
        return params

    def _get_download_params(self, fs_id: int) -> dict[str, Any]:
        """Build parameters for the download API."""
        params = self._get_default_params()
        params.update(
            {
                "sign": self._bds_token or "",
                "timestamp": "",
                "bdstoken": self._bds_token or "",
                "primaryid": self._share_id or "",
                "uk": self._share_uk or self._uk or 0,
                "shareid": self._share_id or "",
                "type": "nolimit",
                "fid_list": f"[{fs_id}]",
                "fs_id": fs_id,
            }
        )
        if self._pwd:
            params["pwd"] = self._pwd
        return params

    @staticmethod
    def _check_share_url(url: str) -> None:
        if not url:
            raise TeraBoxURLError("URL is empty", url=url)
