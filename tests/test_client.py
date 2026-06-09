from __future__ import annotations

from pathlib import Path

import pytest
import respx
from httpx import Response

from teraboxsdk import AsyncTeraBoxClient, TeraBoxClient
from teraboxsdk.models import FileInfo

MOCK_SHARE_HTML = """
<html>
<script>
    window.jsToken = "mock-jstoken";
    window.bdstoken = "mock-bdstoken";
    window.logid = "mock-logid";
    window.shareid = 12345678;
    window.uk = 999888;
    window.share_uk = 777666;
    window.share_username = "mock-user-123";
</script>
</html>
"""

@respx.mock
def test_sync_client_get_files() -> None:
    # 1. Share page fetch mock
    route_page = respx.get("https://terabox.com/s/1ABCDEF").mock(
        return_value=Response(200, text=MOCK_SHARE_HTML)
    )
    # 2. Short URL info mock
    route_info = respx.get("https://terabox.com/api/shorturlinfo").mock(
        return_value=Response(200, json={"errno": 0, "errmsg": "succ"})
    )
    # 3. Share list files mock
    route_list = respx.get("https://terabox.com/api/share/list").mock(
        return_value=Response(
            200,
            json={
                "errno": 0,
                "list": [
                  {"server_filename": "doc.pdf", "size": "1048576", "fs_id": 101, "isdir": 0, "path": "/doc.pdf"},
                  {"server_filename": "pics", "size": "0", "fs_id": 102, "isdir": 1, "path": "/pics"}
                ],
                "count": 2
            }
        )
    )

    with TeraBoxClient() as client:
        listing = client.get_files("https://terabox.com/s/1ABCDEF")
        assert len(listing.files) == 2
        assert listing.files[0].name == "doc.pdf"
        assert listing.files[0].is_dir is False
        assert listing.files[1].name == "pics"
        assert listing.files[1].is_dir is True

        assert route_page.called
        assert route_info.called
        assert route_list.called


@respx.mock
def test_sync_client_get_folder_info_recursive() -> None:
    # 1. HTML fetch
    respx.get("https://terabox.com/s/1ABCDEF").mock(
        return_value=Response(200, text=MOCK_SHARE_HTML)
    )
    # 2. Short URL info
    respx.get("https://terabox.com/api/shorturlinfo").mock(
        return_value=Response(200, json={"errno": 0})
    )
    # 3. Root list (returns 1 file, 1 dir)
    respx.get("https://terabox.com/api/share/list", params={"root": "1"}).mock(
        return_value=Response(
            200,
            json={
                "errno": 0,
                "list": [
                  {"server_filename": "root.txt", "size": "100", "fs_id": 1, "isdir": 0, "path": "/root.txt"},
                  {"server_filename": "subdir", "size": "0", "fs_id": 2, "isdir": 1, "path": "/subdir"}
                ]
            }
        )
    )
    # 4. Subdir list (returns 1 file)
    respx.get("https://terabox.com/api/share/list", params={"dir": "/subdir"}).mock(
        return_value=Response(
            200,
            json={
                "errno": 0,
                "list": [
                  {"server_filename": "sub.txt", "size": "200", "fs_id": 3, "isdir": 0, "path": "/subdir/sub.txt"}
                ]
            }
        )
    )

    with TeraBoxClient() as client:
        folder = client.get_folder_info("https://terabox.com/s/1ABCDEF", recursive=True)
        assert folder.folder_name == "root.txt"  # splits listing.files[0].path
        assert len(folder.files) == 1
        assert folder.files[0].name == "root.txt"
        assert len(folder.subfolders) == 1
        assert folder.subfolders[0].folder_name == "subdir"
        assert len(folder.subfolders[0].files) == 1
        assert folder.subfolders[0].files[0].name == "sub.txt"


@respx.mock
def test_sync_client_get_user_info() -> None:
    respx.get("https://terabox.com/s/1ABCDEF").mock(
        return_value=Response(200, text=MOCK_SHARE_HTML)
    )

    with TeraBoxClient() as client:
        user = client.get_user_info("https://terabox.com/s/1ABCDEF")
        assert user.username == "mock-user-123"
        assert user.uk == 999888


@respx.mock
def test_sync_client_download(tmp_path: Path) -> None:
    # 1. Download link mock
    respx.get("https://terabox.com/api/share/list/download").mock(
        return_value=Response(
            200,
            json={
                "errno": 0,
                "dlink": "https://example.com/stream-download/file.txt"
            }
        )
    )

    # 2. File download streaming mock
    respx.get("https://example.com/stream-download/file.txt").mock(
        return_value=Response(200, content=b"chunk1 chunk2")
    )

    file_info = FileInfo(
        name="test.txt",
        size=13,
        fs_id=999,
        is_dir=False,
        path="/test.txt"
    )

    with TeraBoxClient() as client:
        dest = tmp_path / "test.txt"
        res_path = client.download(file_info, dest)
        assert res_path == dest
        assert dest.read_bytes() == b"chunk1 chunk2"


@pytest.mark.asyncio
@respx.mock
async def test_async_client_get_files() -> None:
    respx.get("https://terabox.com/s/1ABCDEF").mock(
        return_value=Response(200, text=MOCK_SHARE_HTML)
    )
    respx.get("https://terabox.com/api/shorturlinfo").mock(
        return_value=Response(200, json={"errno": 0})
    )
    respx.get("https://terabox.com/api/share/list").mock(
        return_value=Response(
            200,
            json={
                "errno": 0,
                "list": [{"server_filename": "file.txt", "size": "10", "fs_id": 501, "isdir": 0, "path": "/file.txt"}],
                "count": 1
            }
        )
    )

    async with AsyncTeraBoxClient() as client:
        listing = await client.get_files("https://terabox.com/s/1ABCDEF")
        assert len(listing.files) == 1
        assert listing.files[0].name == "file.txt"


@pytest.mark.asyncio
@respx.mock
async def test_async_client_get_folder_info_recursive() -> None:
    respx.get("https://terabox.com/s/1ABCDEF").mock(
        return_value=Response(200, text=MOCK_SHARE_HTML)
    )
    respx.get("https://terabox.com/api/shorturlinfo").mock(
        return_value=Response(200, json={"errno": 0})
    )
    respx.get("https://terabox.com/api/share/list", params={"root": "1"}).mock(
        return_value=Response(
            200,
            json={
                "errno": 0,
                "list": [
                  {"server_filename": "root.txt", "size": "100", "fs_id": 1, "isdir": 0, "path": "/root.txt"},
                  {"server_filename": "subdir", "size": "0", "fs_id": 2, "isdir": 1, "path": "/subdir"}
                ]
            }
        )
    )
    respx.get("https://terabox.com/api/share/list", params={"dir": "/subdir"}).mock(
        return_value=Response(
            200,
            json={
                "errno": 0,
                "list": [
                  {"server_filename": "sub.txt", "size": "200", "fs_id": 3, "isdir": 0, "path": "/subdir/sub.txt"}
                ]
            }
        )
    )

    async with AsyncTeraBoxClient() as client:
        folder = await client.get_folder_info("https://terabox.com/s/1ABCDEF", recursive=True)
        assert len(folder.files) == 1
        assert folder.files[0].name == "root.txt"
        assert len(folder.subfolders) == 1
        assert folder.subfolders[0].folder_name == "subdir"
        assert len(folder.subfolders[0].files) == 1
        assert folder.subfolders[0].files[0].name == "sub.txt"


@pytest.mark.asyncio
@respx.mock
async def test_async_client_get_user_info() -> None:
    respx.get("https://terabox.com/s/1ABCDEF").mock(
        return_value=Response(200, text=MOCK_SHARE_HTML)
    )

    async with AsyncTeraBoxClient() as client:
        user = await client.get_user_info("https://terabox.com/s/1ABCDEF")
        assert user.username == "mock-user-123"
        assert user.uk == 999888


@pytest.mark.asyncio
@respx.mock
async def test_async_client_download(tmp_path: Path) -> None:
    respx.get("https://terabox.com/api/share/list/download").mock(
        return_value=Response(
            200,
            json={
                "errno": 0,
                "dlink": "https://example.com/stream-download/file.txt"
            }
        )
    )

    respx.get("https://example.com/stream-download/file.txt").mock(
        return_value=Response(200, content=b"async chunk1 chunk2")
    )

    file_info = FileInfo(
        name="test.txt",
        size=19,
        fs_id=999,
        is_dir=False,
        path="/test.txt"
    )

    async with AsyncTeraBoxClient() as client:
        dest = tmp_path / "async_test.txt"
        res_path = await client.download(file_info, dest)
        assert res_path == dest
        assert dest.read_bytes() == b"async chunk1 chunk2"


@respx.mock
def test_sync_client_with_ndus() -> None:
    respx.get("https://terabox.com/s/1ABCDEF").mock(
        return_value=Response(200, text=MOCK_SHARE_HTML)
    )
    respx.get("https://terabox.com/api/shorturlinfo").mock(
        return_value=Response(200, json={"errno": 0})
    )
    respx.get("https://terabox.com/api/share/list").mock(
        return_value=Response(200, json={"errno": 0, "list": []})
    )

    with TeraBoxClient(ndus="my-mock-ndus") as client:
        assert client.ndus == "my-mock-ndus"
        assert client._http._client.cookies.get("ndus") == "my-mock-ndus"
        client.get_files("https://terabox.com/s/1ABCDEF")


@pytest.mark.asyncio
@respx.mock
async def test_async_client_with_ndus() -> None:
    respx.get("https://terabox.com/s/1ABCDEF").mock(
        return_value=Response(200, text=MOCK_SHARE_HTML)
    )
    respx.get("https://terabox.com/api/shorturlinfo").mock(
        return_value=Response(200, json={"errno": 0})
    )
    respx.get("https://terabox.com/api/share/list").mock(
        return_value=Response(200, json={"errno": 0, "list": []})
    )

    async with AsyncTeraBoxClient(ndus="async-mock-ndus") as client:
        assert client.ndus == "async-mock-ndus"
        assert client._http._client.cookies.get("ndus") == "async-mock-ndus"
        await client.get_files("https://terabox.com/s/1ABCDEF")
