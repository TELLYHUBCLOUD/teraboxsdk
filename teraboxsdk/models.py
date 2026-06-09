"""Data models for TeraBox API responses."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

__all__ = [
    "FileInfo",
    "DownloadInfo",
    "FolderInfo",
    "FileListing",
    "UserInfo",
]


@dataclass(slots=True)
class FileInfo:
    """Represents a single file in a TeraBox share."""

    name: str
    size: int
    fs_id: int
    is_dir: bool
    path: str
    md5: str | None = None
    dlink: str | None = None
    thumbnail: str | None = None
    create_time: datetime | None = None
    modify_time: datetime | None = None
    category: int = 0

    @property
    def size_human(self) -> str:
        """Human-readable file size."""
        if self.size < 1024:
            return f"{self.size} B"
        elif self.size < 1024**2:
            return f"{self.size / 1024:.1f} KB"
        elif self.size < 1024**3:
            return f"{self.size / 1024**2:.1f} MB"
        else:
            return f"{self.size / 1024**3:.2f} GB"

    @property
    def extension(self) -> str:
        """File extension (lowercase)."""
        if "." in self.name:
            return self.name.rsplit(".", 1)[-1].lower()
        return ""

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> FileInfo:
        """Create FileInfo from raw API response dict."""
        isdir_raw = data.get("isdir", data.get("is_dir", 0))
        is_dir = (
            isdir_raw not in ("0", "false", "", False, 0)
            if isinstance(isdir_raw, (str, int, bool))
            else bool(isdir_raw)
        )
        return cls(
            name=data.get("server_filename", data.get("filename", "unknown")),
            size=int(data.get("size") or 0),
            fs_id=int(data.get("fs_id") or 0),
            is_dir=is_dir,
            path=data.get("path", ""),
            md5=data.get("md5") or None,
            dlink=data.get("dlink") or None,
            thumbnail=data.get("thumbnails") or data.get("thumb") or None,
            create_time=(
                datetime.fromtimestamp(float(data["server_ctime"]), tz=timezone.utc).replace(tzinfo=None)
                if data.get("server_ctime") is not None
                else None
            ),
            modify_time=(
                datetime.fromtimestamp(float(data["server_mtime"]), tz=timezone.utc).replace(tzinfo=None)
                if data.get("server_mtime") is not None
                else None
            ),
            category=int(data.get("category") or 0),
        )


@dataclass(slots=True)
class DownloadInfo:
    """Contains direct download URL and metadata."""

    url: str
    filename: str
    size: int
    expires_at: datetime | None = None
    headers: dict[str, str] = field(default_factory=dict)

    @property
    def size_human(self) -> str:
        if self.size < 1024:
            return f"{self.size} B"
        elif self.size < 1024**2:
            return f"{self.size / 1024:.1f} KB"
        elif self.size < 1024**3:
            return f"{self.size / 1024**2:.1f} MB"
        else:
            return f"{self.size / 1024**3:.2f} GB"

    @classmethod
    def from_api(cls, data: dict[str, Any], filename: str = "unknown") -> DownloadInfo:
        """Create DownloadInfo from raw API response."""
        return cls(
            url=data.get("dlink", data.get("url", "")),
            filename=filename,
            size=int(data.get("size") or 0),
            expires_at=(
                datetime.fromtimestamp(float(data["expires"]), tz=timezone.utc).replace(tzinfo=None)
                if data.get("expires") is not None
                else None
            ),
            headers=data.get("headers", {}),
        )


@dataclass(slots=True)
class FolderInfo:
    """Represents a shared folder and its contents."""

    folder_name: str
    path: str
    share_id: str
    uk: int
    files: list[FileInfo] = field(default_factory=list)
    subfolders: list[FolderInfo] = field(default_factory=list)
    create_time: datetime | None = None

    @property
    def total_size(self) -> int:
        return sum(f.size for f in self.files)

    @property
    def total_files(self) -> int:
        return len(self.files)

    @property
    def total_items(self) -> int:
        return len(self.files) + len(self.subfolders)


@dataclass(slots=True)
class FileListing:
    """Paginated file listing result."""

    files: list[FileInfo] = field(default_factory=list)
    cursor: str | None = None
    has_more: bool = False
    total_count: int = 0

    @property
    def is_empty(self) -> bool:
        return len(self.files) == 0


@dataclass(slots=True)
class UserInfo:
    """Minimal user info from share context."""

    uk: int
    username: str
    avatar_url: str | None = None
