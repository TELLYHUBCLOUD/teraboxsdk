# TeraBox SDK

A modern, production-ready Python SDK for TeraBox file sharing and downloading. Supports both synchronous and asynchronous operations with full type safety.

## Features

- **Dual API**: Synchronous (`TeraBoxClient`) and Asynchronous (`AsyncTeraBoxClient`)
- **HTTP/2 Support**: Built on `httpx` with HTTP/2 for faster connections
- **Type Safe**: Full type hints, mypy-compatible
- **WAF Bypass / Proxy Support**: Built-in option to route API queries through a Cloudflare Worker proxy (`worker_proxy_url`) to bypass `need verify_v2` challenges and IP blocks
- **Obfuscation Handling**: Automatically decodes and extracts dynamically obfuscated tokens (e.g., `jsToken` wrapped in URL-encoded `eval()` blocks)
- **Robust Error Handling**: 6 custom exceptions with detailed API error mappings (supports both `errno` and newer `error_code`/`error_msg` API response fields)
- **Download Management**: Chunked downloads with progress tracking and resume support (optimally uses pre-fetched proxy download links)
- **URL Parsing**: Extract share IDs from any TeraBox URL variant
- **Production Ready**: Comprehensive test suite, CI/CD, automated PyPI publishing

## Installation

```bash
pip install teraboxsdk
```

With async support (optional):

```bash
pip install teraboxsdk[async]
```

## Documentation

For a comprehensive guide detailing:
- How to retrieve and use your **`ndus` authentication cookie** to avoid `need verify_v2` / `400210` errors
- How to use a **Cloudflare Worker proxy** to completely bypass Web Application Firewall (WAF) challenges
- How to configure **SSL verification** (`verify=False`) to bypass handshake timeouts
- Complete sync and async examples for folder traversal and download tracking

Please refer to [GUIDE.md](file:///C:/Users/Admin/OneDrive/Documents/GitHub/teraboxsdk/GUIDE.md).

## Quick Start

### Synchronous

```python
from teraboxsdk import TeraBoxClient

client = TeraBoxClient()

# List files
listing = client.get_files("https://terabox.com/s/1ABCDEF")
for file in listing.files:
    print(f"{file.name} ({file.size_human})")

# Download with progress
def progress(pct, downloaded, total):
    print(f"{pct:.1f}%")

client.download(listing.files[0], "./downloads", progress_callback=progress)
client.close()
```

### Asynchronous

```python
import asyncio
from teraboxsdk import AsyncTeraBoxClient

async def main():
    async with AsyncTeraBoxClient() as client:
        listing = await client.get_files("https://terabox.com/s/1ABCDEF")
        await client.download(listing.files[0], "./downloads")

asyncio.run(main())
```

## API Reference

### `TeraBoxClient` / `AsyncTeraBoxClient`

| Method | Description |
|--------|-------------|
| `get_files(url, password, page, limit)` | List files in a share |
| `get_folder_info(url, password, recursive)` | Get folder with contents |
| `get_download_link(file)` | Get direct download URL |
| `download(file, dest, progress_callback)` | Download file with progress |
| `get_user_info(url)` | Extract user info from share |

### Models

- `FileInfo`: name, size, fs_id, is_dir, path, md5, dlink, thumbnail, extension, size_human
- `DownloadInfo`: url, filename, size, expires_at, size_human
- `FolderInfo`: folder_name, files, subfolders, total_size, total_files
- `FileListing`: files, cursor, has_more, total_count

### Exceptions

| Exception | When Raised |
|-----------|-------------|
| `TeraBoxError` | Base exception |
| `TeraBoxAPIError` | API returns error response |
| `TeraBoxDownloadError` | Download fails |
| `TeraBoxURLError` | Invalid/malformed URL |
| `TeraBoxNotFoundError` | File/folder not found |
| `TeraBoxAuthError` | Authentication failure |

## URL Support

The SDK handles all TeraBox URL variants:

```python
from teraboxsdk import extract_surl, normalize_url

# All of these work:
extract_surl("https://terabox.com/s/1a2b3c")
extract_surl("https://1024terabox.com/s/1a2b3c")
extract_surl("https://terabox.app/s/1a2b3c")
extract_surl("1a2b3c")  # Just the short code

normalize_url("1a2b3c")  # -> https://terabox.com/s/1a2b3c
```

## Configuration

```python
from teraboxsdk import TeraBoxClient

# Custom timeout, proxy, and Cloudflare Worker proxy configuration
client = TeraBoxClient(
    timeout=60.0, 
    proxy="http://proxy:8080",
    worker_proxy_url="https://your-worker-proxy.workers.dev/"
)
```

## Development

```bash
git clone https://github.com/yourusername/teraboxsdk.git
cd teraboxsdk
pip install -r requirements-dev.txt
pytest
```

## License

MIT License - see [LICENSE](LICENSE) file.
