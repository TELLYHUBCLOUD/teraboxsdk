"""Utility functions for URL parsing and surl extraction."""

from __future__ import annotations

import re
from urllib.parse import parse_qs, unquote, urlparse

from .exceptions import TeraBoxURLError

__all__ = [
    "extract_surl",
    "extract_share_id",
    "is_terabox_url",
    "normalize_url",
    "parse_terabox_url",
]

# TeraBox domain variants
_TB_DOMAINS = {
    "terabox.com",
    "www.terabox.com",
    "1024terabox.com",
    "www.1024terabox.com",
    "terabox.app",
    "www.terabox.app",
    "terabox.fun",
    "www.terabox.fun",
    "terafileshare.com",
    "www.terafileshare.com",
    "nephobox.com",
    "www.nephobox.com",
    "freeterabox.com",
    "www.freeterabox.com",
    "teraboxshare.com",
    "www.teraboxshare.com",
    "teraboxlink.com",
    "www.teraboxlink.com",
    "teraboxapp.com",
    "www.teraboxapp.com",
}

_SURL_RE = re.compile(r"surl[=/]([a-zA-Z0-9_-]+)")
_SHARE_ID_RE = re.compile(r"/s/([a-zA-Z0-9_-]+)")
_SHORT_CODE_RE = re.compile(r"^([a-zA-Z0-9_-]{4,})$")


def is_terabox_url(url: str) -> bool:
    """Check if the given URL is a valid TeraBox share URL.

    Args:
        url: The URL to validate.

    Returns:
        True if the URL is a recognized TeraBox URL.
    """
    if not url or not url.startswith(("http://", "https://")):
        return False
    try:
        parsed = urlparse(url)
        return parsed.netloc.lower() in _TB_DOMAINS
    except Exception:
        return False


def extract_surl(url: str) -> str:
    """Extract the surl parameter from a TeraBox URL.

    Args:
        url: The TeraBox share URL.

    Returns:
        The surl value (share unique identifier).

    Raises:
        TeraBoxURLError: If the URL is invalid or surl cannot be extracted.
    """
    if not url:
        raise TeraBoxURLError("URL is empty", url=url)

    url = url.strip()

    # Direct short code (e.g., user pasted just the code)
    if _SHORT_CODE_RE.match(url) and "/" not in url:
        return url

    if not is_terabox_url(url):
        raise TeraBoxURLError(f"Not a valid TeraBox URL: {url}", url=url)

    parsed = urlparse(url)

    # 1. Try query param: ?surl=XXXX
    qs = parse_qs(parsed.query)
    if "surl" in qs:
        return qs["surl"][0]

    # 2. Try path: /surl/XXXX or /sharing?...surl=XXXX
    match = _SURL_RE.search(url)
    if match:
        return match.group(1)

    # 3. Try path segment: /s/XXXX
    match = _SHARE_ID_RE.search(parsed.path)
    if match:
        return match.group(1)

    raise TeraBoxURLError(
        f"Could not extract surl/share_id from URL: {url}",
        url=url,
    )


def extract_share_id(url: str) -> str:
    """Alias for extract_surl."""
    return extract_surl(url)


def normalize_url(url: str) -> str:
    """Normalize a TeraBox URL to the standard format.

    Args:
        url: Raw TeraBox URL or short code.

    Returns:
        A normalized https://terabox.com/s/... URL.

    Raises:
        TeraBoxURLError: If the URL cannot be normalized.
    """
    if not url:
        raise TeraBoxURLError("URL is empty", url=url)

    url = url.strip()

    # Already a full URL
    if url.startswith(("http://", "https://")):
        if not is_terabox_url(url):
            raise TeraBoxURLError(f"Not a valid TeraBox URL: {url}", url=url)

        surl = extract_surl(url)
        return f"https://terabox.com/s/{surl}"

    # Just a short code / surl
    if _SHORT_CODE_RE.match(url):
        return f"https://terabox.com/s/{url}"

    raise TeraBoxURLError(f"Cannot normalize TeraBox URL: {url}", url=url)


def parse_terabox_url(url: str) -> dict[str, str]:
    """Parse a TeraBox URL into its components.

    Args:
        url: The TeraBox share URL.

    Returns:
        Dictionary with keys: surl, folder_path (optional), password (optional).

    Raises:
        TeraBoxURLError: If the URL is invalid.
    """
    if not url:
        raise TeraBoxURLError("URL is empty", url=url)

    surl = extract_surl(url)
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)

    result: dict[str, str] = {"surl": surl}

    # Extract password if present
    if "pwd" in qs:
        result["password"] = qs["pwd"][0]

    # Extract folder path if present
    if "path" in qs:
        result["folder_path"] = qs["path"][0]
    elif "dir" in qs:
        result["folder_path"] = qs["dir"][0]
    else:
        # Extract folder path if present in URL path (path after /s/{surl}/...)
        path_parts = [p for p in unquote(parsed.path).split("/") if p]
        if len(path_parts) > 2 and path_parts[0] == "s":
            result["folder_path"] = "/" + "/".join(path_parts[2:])

    return result
