"""Tests for teraboxsdk.models module (9 tests)."""

from __future__ import annotations

from datetime import datetime, timezone

from teraboxsdk.models import DownloadInfo, FileInfo, FileListing, FolderInfo, UserInfo


class TestFileInfo:
    def test_from_api_basic(self) -> None:
        data = {
            "server_filename": "test.mp4",
            "size": "1048576",
            "fs_id": 12345,
            "isdir": 0,
            "path": "/test.mp4",
            "md5": "abc123",
            "dlink": "https://example.com/dl",
            "thumbnails": "https://example.com/thumb.jpg",
            "server_ctime": 1609459200,
            "server_mtime": 1609545600,
            "category": 1,
        }
        f = FileInfo.from_api(data)
        assert f.name == "test.mp4"
        assert f.size == 1048576
        assert f.fs_id == 12345
        assert f.is_dir is False
        assert f.md5 == "abc123"
        assert f.dlink == "https://example.com/dl"
        assert f.thumbnail == "https://example.com/thumb.jpg"
        assert f.create_time == datetime(2021, 1, 1, 0, 0, 0, tzinfo=timezone.utc).replace(tzinfo=None)
        assert f.category == 1

    def test_from_api_stringified_bools(self) -> None:
        # Test stringified 'isdir'
        data_string_dir = {"isdir": "1", "size": "100", "fs_id": "99"}
        f1 = FileInfo.from_api(data_string_dir)
        assert f1.is_dir is True
        assert f1.size == 100
        assert f1.fs_id == 99

        data_string_file = {"isdir": "0"}
        f2 = FileInfo.from_api(data_string_file)
        assert f2.is_dir is False

        data_false_str = {"isdir": "false"}
        f3 = FileInfo.from_api(data_false_str)
        assert f3.is_dir is False

    def test_from_api_nulls(self) -> None:
        # Test null and missing fields
        data = {
            "isdir": None,
            "size": None,
            "fs_id": None,
            "category": None,
        }
        f = FileInfo.from_api(data)
        assert f.is_dir is False
        assert f.size == 0
        assert f.fs_id == 0
        assert f.category == 0
        assert f.create_time is None
        assert f.modify_time is None

    def test_size_human_bytes(self) -> None:
        f = FileInfo(name="a.txt", size=500, fs_id=1, is_dir=False, path="/a.txt")
        assert f.size_human == "500 B"

    def test_size_human_kb(self) -> None:
        f = FileInfo(name="a.txt", size=1536, fs_id=1, is_dir=False, path="/a.txt")
        assert f.size_human == "1.5 KB"

    def test_size_human_mb(self) -> None:
        f = FileInfo(name="a.txt", size=2 * 1024 * 1024, fs_id=1, is_dir=False, path="/a.txt")
        assert f.size_human == "2.0 MB"

    def test_size_human_gb(self) -> None:
        f = FileInfo(name="a.txt", size=3 * 1024**3 + 500 * 1024**2, fs_id=1, is_dir=False, path="/a.txt")
        assert f.size_human == "3.49 GB"

    def test_extension(self) -> None:
        f = FileInfo(name="archive.zip", size=0, fs_id=1, is_dir=False, path="/archive.zip")
        assert f.extension == "zip"

    def test_extension_empty(self) -> None:
        f = FileInfo(name="README", size=0, fs_id=1, is_dir=False, path="/README")
        assert f.extension == ""


class TestDownloadInfo:
    def test_from_api(self) -> None:
        data = {"dlink": "https://example.com/file", "size": "2048", "expires": 1700000000}
        d = DownloadInfo.from_api(data, filename="video.mp4")
        assert d.url == "https://example.com/file"
        assert d.filename == "video.mp4"
        assert d.size == 2048
        assert d.size_human == "2.0 KB"


class TestFolderInfo:
    def test_total_size_and_files(self) -> None:
        files = [
            FileInfo(name="a.txt", size=100, fs_id=1, is_dir=False, path="/a.txt"),
            FileInfo(name="b.txt", size=200, fs_id=2, is_dir=False, path="/b.txt"),
        ]
        folder = FolderInfo(folder_name="root", path="/", share_id="s1", uk=1, files=files)
        assert folder.total_size == 300
        assert folder.total_files == 2
        assert folder.total_items == 2

    def test_empty_folder(self) -> None:
        folder = FolderInfo(folder_name="empty", path="/", share_id="s1", uk=1)
        assert folder.total_size == 0
        assert folder.is_empty if hasattr(folder, "is_empty") else len(folder.files) == 0


class TestFileListing:
    def test_is_empty(self) -> None:
        listing = FileListing()
        assert listing.is_empty is True

    def test_has_more(self) -> None:
        files = [FileInfo(name="f.txt", size=0, fs_id=1, is_dir=False, path="/f.txt")]
        listing = FileListing(files=files, has_more=True, cursor="2", total_count=10)
        assert listing.is_empty is False
        assert listing.has_more is True


class TestUserInfo:
    def test_basic(self) -> None:
        user = UserInfo(uk=12345, username="testuser", avatar_url="https://example.com/avatar.jpg")
        assert user.uk == 12345
        assert user.username == "testuser"
        assert user.avatar_url == "https://example.com/avatar.jpg"
