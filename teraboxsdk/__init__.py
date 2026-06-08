"""TeraBox SDK - A modern Python SDK for TeraBox file sharing.

Usage:
    Sync:
        from teraboxsdk import TeraBoxClient
        client = TeraBoxClient()
        files = client.get_files("https://terabox.com/s/1ABCDEF")
        client.download(files[0], "./downloads")
        client.close()

    Async:
        from teraboxsdk import AsyncTeraBoxClient
        async with AsyncTeraBoxClient() as client:
            files = await client.get_files("https://terabox.com/s/1ABCDEF")
            await client.download(files[0], "./downloads")
"""

from .async_client import AsyncTeraBoxClient
from .client import TeraBoxClient
from .downloader import AsyncChunkedDownloader, ChunkedDownloader, DownloadProgress
from .exceptions import (
    TeraBoxAPIError,
    TeraBoxAuthError,
    TeraBoxDownloadError,
    TeraBoxError,
    TeraBoxNotFoundError,
    TeraBoxURLError,
)
from .models import DownloadInfo, FileInfo, FileListing, FolderInfo, UserInfo
from .utils import (
    extract_share_id,
    extract_surl,
    is_terabox_url,
    normalize_url,
    parse_terabox_url,
)

__version__ = "1.0.0"
__all__ = [
    # Clients
    "TeraBoxClient",
    "AsyncTeraBoxClient",
    # Models
    "FileInfo",
    "DownloadInfo",
    "FolderInfo",
    "FileListing",
    "UserInfo",
    # Exceptions
    "TeraBoxError",
    "TeraBoxAPIError",
    "TeraBoxDownloadError",
    "TeraBoxURLError",
    "TeraBoxNotFoundError",
    "TeraBoxAuthError",
    # Utilities
    "extract_surl",
    "extract_share_id",
    "is_terabox_url",
    "normalize_url",
    "parse_terabox_url",
    # Downloader
    "ChunkedDownloader",
    "AsyncChunkedDownloader",
    "DownloadProgress",
    # Version
    "__version__",
]
