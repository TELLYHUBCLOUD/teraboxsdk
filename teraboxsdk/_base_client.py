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
    errno = data.get("errno", data.get("error_code"))
    if errno == -3:
        errmsg = "Password required or incorrect password"
    else:
        errmsg = data.get("errmsg", data.get("error_msg", "Unknown API error"))

    if status_code == 404 or errno in (31066, 31075, -9, 31045):
        raise TeraBoxNotFoundError(
            message=f"File or folder not found: {errmsg}",
            status_code=status_code,
            error_code=errno,
            response_body=json.dumps(data),
        )
    if status_code == 403 or errno in (-3, -6, 401, 418, 31211):
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

    def __init__(
        self,
        timeout: float = 30.0,
        proxy: str | None = None,
        ndus: str | None = None,
        worker_proxy_url: str | None = None,
    ) -> None:
        self.timeout = timeout
        self.proxy = proxy
        self.ndus = ndus
        self.worker_proxy_url = worker_proxy_url
        self.api_base = API_BASE
        self._js_token: str | None = None
        self._bds_token: str | None = None
        self._log_id: str | None = None
        self._sign: str | None = None
        self._timestamp: str | None = None
        self._uk: int | None = None
        self._share_uk: int | None = None
        self._share_id: str | None = None
        self._pwd: str | None = None
        self._surl: str | None = None

    @property
    def share_endpoint(self) -> str:
        return f"{self.api_base}/api/shorturlinfo"

    @property
    def file_list_endpoint(self) -> str:
        return f"{self.api_base}/api/share/list"

    @property
    def download_endpoint(self) -> str:
        return f"{self.api_base}/api/sharedownload"

    def _set_dynamic_api_base(self, url: str) -> None:
        """Parse domain and scheme of input URL and dynamically set api_base."""
        if url and url.startswith(("http://", "https://")):
            from urllib.parse import urlparse
            parsed = urlparse(url)
            self.api_base = f"{parsed.scheme}://{parsed.netloc}"

    def _extract_tokens(self, html: str) -> None:
        """Parse HTML to extract required tokens."""
        from urllib.parse import unquote

        # Decode URL-encoded content (e.g. obfuscated jsToken under eval(decodeURIComponent(...)))
        decoded_html = unquote(html)

        if match := re.search(r'[\'"]?jsToken[\'"]?\s*[:=]\s*[\'"]([^\'"]+)[\'"]', decoded_html):
            self._js_token = match.group(1)
        else:
            # Fallback to match the obfuscated jsToken eval pattern:
            # e.g., function fn(a){window.jsToken = a};fn("TOKEN_VALUE")
            obfuscated_pattern = (
                r'function\s+([a-zA-Z0-9_]+)\s*\(\s*([a-zA-Z0-9_]+)\s*\)\s*{\s*'
                r'(?:window\.)?jsToken\s*=\s*\2\s*}\s*;\s*\1\(\s*[\'"]([^\'"]+)[\'"]\)'
            )
            if match := re.search(obfuscated_pattern, decoded_html):
                self._js_token = match.group(3)

        if match := re.search(r'[\'"]?bdstoken[\'"]?\s*[:=]\s*[\'"]([^\'"]*)[\'"]', decoded_html):
            self._bds_token = match.group(1)
        if match := re.search(r'[\'"]?logid[\'"]?\s*[:=]\s*[\'"]([^\'"]+)[\'"]', decoded_html):
            self._log_id = match.group(1)
        if match := re.search(r'[\'"]?sign[\'"]?\s*[:=]\s*[\'"]([^\'"]+)[\'"]', decoded_html):
            self._sign = match.group(1)
        if match := re.search(r'[\'"]?timestamp[\'"]?\s*[:=]\s*[\'"]?(\d+)[\'"]?', decoded_html):
            self._timestamp = match.group(1)

        # Extract share metadata from inline JS
        if share_id_match := re.search(
            r'[\'"]?share[iI]d[\'"]?\s*[=:]\s*[\'"]?(\d+)[\'"]?', decoded_html
        ):
            self._share_id = share_id_match.group(1)

        clean_html = re.sub(r'thirdUserInfo\s*:\s*\{[^}]+\}', '', decoded_html)
        if uk_match := re.search(r'[\'"]?uk[\'"]?\s*[=:]\s*[\'"]?(\d+)[\'"]?', clean_html):
            self._uk = int(uk_match.group(1))

        if share_uk_match := re.search(
            r'[\'"]?share_uk[\'"]?\s*[=:]\s*[\'"]?(\d+)[\'"]?', decoded_html
        ):
            self._share_uk = int(share_uk_match.group(1))

    def _get_default_params(self) -> dict[str, Any]:
        """Common query parameters for most API calls."""
        params: dict[str, Any] = {
            "app_id": "250528",
            "channel": "dubox",
            "clienttype": "0",
            "web": "1",
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
                "sign": self._sign or self._bds_token or "",
                "timestamp": self._timestamp or "",
                "bdstoken": self._bds_token or "",
                "primaryid": self._share_id or "",
                "uk": self._share_uk or self._uk or 0,
                "shareid": self._share_id or "",
                "shorturl": self._surl or "",
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
