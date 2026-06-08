"""Tests for teraboxsdk.utils module (8 tests)."""

from __future__ import annotations

import pytest

from teraboxsdk.exceptions import TeraBoxURLError
from teraboxsdk.utils import (
    extract_share_id,
    extract_surl,
    is_terabox_url,
    normalize_url,
    parse_terabox_url,
)


class TestIsTeraBoxUrl:
    def test_valid_https_url(self) -> None:
        assert is_terabox_url("https://terabox.com/s/1ABCDEF") is True

    def test_valid_www_url(self) -> None:
        assert is_terabox_url("https://www.terabox.com/s/1ABCDEF") is True

    def test_valid_1024_url(self) -> None:
        assert is_terabox_url("https://1024terabox.com/s/1ABCDEF") is True

    def test_valid_nephobox_url(self) -> None:
        assert is_terabox_url("https://nephobox.com/s/1ABCDEF") is True
        assert is_terabox_url("https://www.nephobox.com/s/1ABCDEF") is True

    def test_valid_freeterabox_url(self) -> None:
        assert is_terabox_url("https://freeterabox.com/s/1ABCDEF") is True

    def test_invalid_domain(self) -> None:
        assert is_terabox_url("https://google.com/s/1ABCDEF") is False

    def test_empty_url(self) -> None:
        assert is_terabox_url("") is False

    def test_non_http(self) -> None:
        assert is_terabox_url("ftp://terabox.com/s/1") is False


class TestExtractSurl:
    def test_from_path(self) -> None:
        url = "https://terabox.com/s/1a2b3c4d"
        assert extract_surl(url) == "1a2b3c4d"

    def test_from_query_param(self) -> None:
        url = "https://terabox.com/s/1a2b3c?surl=XYZ123"
        assert extract_surl(url) == "XYZ123"

    def test_direct_short_code(self) -> None:
        assert extract_surl("ABC123") == "ABC123"

    def test_invalid_url_raises(self) -> None:
        with pytest.raises(TeraBoxURLError):
            extract_surl("https://google.com")

    def test_empty_raises(self) -> None:
        with pytest.raises(TeraBoxURLError):
            extract_surl("")


class TestNormalizeUrl:
    def test_full_url(self) -> None:
        result = normalize_url("https://terabox.com/s/1a2b3c")
        assert result == "https://terabox.com/s/1a2b3c"

    def test_short_code(self) -> None:
        result = normalize_url("ABC123")
        assert result == "https://terabox.com/s/ABC123"

    def test_invalid_domain_raises(self) -> None:
        with pytest.raises(TeraBoxURLError):
            normalize_url("https://evil.com/s/1")


class TestParseTeraBoxUrl:
    def test_basic_url(self) -> None:
        result = parse_terabox_url("https://terabox.com/s/1a2b3c")
        assert result["surl"] == "1a2b3c"

    def test_with_password(self) -> None:
        result = parse_terabox_url("https://terabox.com/s/1a2b3c?pwd=secret123")
        assert result["surl"] == "1a2b3c"
        assert result["password"] == "secret123"

    def test_with_folder_path(self) -> None:
        result = parse_terabox_url("https://terabox.com/s/1a2b3c/folder/sub")
        assert result["surl"] == "1a2b3c"
        assert result["folder_path"] == "/folder/sub"

    def test_with_folder_path_query_param(self) -> None:
        result1 = parse_terabox_url("https://terabox.com/s/1a2b3c?path=%2Ffolder%2Fsub")
        assert result1["surl"] == "1a2b3c"
        assert result1["folder_path"] == "/folder/sub"

        result2 = parse_terabox_url("https://terabox.com/s/1a2b3c?dir=%2Fother%2Fdir")
        assert result2["surl"] == "1a2b3c"
        assert result2["folder_path"] == "/other/dir"


class TestExtractShareId:
    def test_alias_to_extract_surl(self) -> None:
        assert extract_share_id("https://terabox.com/s/ABC123") == "ABC123"
