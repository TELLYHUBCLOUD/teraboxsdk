# Comprehensive Guide to using `teraboxsdk`

`teraboxsdk` is a modern, fully-typed Python library designed to parse TeraBox share links, retrieve metadata, list files and folders, generate direct download links, and manage file downloading. It provides both synchronous (`TeraBoxClient`) and asynchronous (`AsyncTeraBoxClient`) clients.

---

## Table of Contents
1. [Installation](#1-installation)
2. [Authenticating with `ndus` Cookie](#2-authenticating-with-ndus-cookie)
3. [SSL/TLS Verification Configuration](#3-ssltls-verification-configuration)
4. [Dynamic Domain Routing (e.g., 1024terabox.com)](#4-dynamic-domain-routing-eg-1024teraboxcom)
5. [Synchronous Examples (`TeraBoxClient`)](#5-synchronous-examples-teraboxclient)
    - [Listing Files](#listing-files)
    - [Folder Hierarchy Lookup](#folder-hierarchy-lookup)
    - [Generating Direct Download Links](#generating-direct-download-links)
    - [Downloading Files with Progress](#downloading-files-with-progress)
6. [Asynchronous Examples (`AsyncTeraBoxClient`)](#6-asynchronous-examples-asyncteraboxclient)
    - [Async Listing and Direct Link Extraction](#async-listing-and-direct-link-extraction)
    - [Async Downloading](#async-downloading)
7. [Error Handling](#7-error-handling)
8. [Advanced Configuration (Timeouts & Proxies)](#8-advanced-configuration-timeouts--proxies)

---

## 1. Installation

Install the library via `pip`:

```bash
pip install teraboxsdk
```

For async features, install with async support:

```bash
pip install teraboxsdk[async]
```

---

## 2. Authenticating with `ndus` Cookie

### What is the `ndus` cookie?
TeraBox requires users to be authenticated to download files or query specific share link details. If you query a share link without authenticating, the TeraBox API will return:
```json
{"errno": 400210, "errmsg": "need verify_v2", "request_id": ...}
```
Passing the active `ndus` cookie solves this issue.

### How to retrieve your `ndus` cookie:
1. Open your web browser (Chrome, Firefox, Edge, etc.).
2. Go to [https://www.terabox.com/](https://www.terabox.com/) or [https://www.1024terabox.com/](https://www.1024terabox.com/) and log in.
3. Once logged in, press `F12` (or right-click and select **Inspect**) to open Developer Tools.
4. Go to the **Application** (Chrome) or **Storage** (Firefox) tab.
5. In the left panel, expand **Cookies** and select the TeraBox domain.
6. Look for a cookie named `ndus`.
7. Copy its value (a long alphanumeric string, e.g., `Yf3YAiCteHuiQQ2te6ekMTzqMElAanfNpGVSPheD`).

### Passing the cookie to the client:
```python
from teraboxsdk import TeraBoxClient

client = TeraBoxClient(ndus="YOUR_NDUS_COOKIE_VALUE")
```

---

## 3. SSL/TLS Verification Configuration

When running on certain cloud providers, behind restrictive corporate firewalls, or using specific proxies, SSL handshakes might fail or cause connection timeouts.

To bypass SSL certificate verification issues, you can set `verify=False` when instantiating the client:

```python
from teraboxsdk import TeraBoxClient

# Disable SSL verification
client = TeraBoxClient(ndus="YOUR_NDUS_COOKIE", verify=False)
```

For async operations:
```python
from teraboxsdk import AsyncTeraBoxClient

async with AsyncTeraBoxClient(ndus="YOUR_NDUS_COOKIE", verify=False) as client:
    # Operations go here
    pass
```

> [!WARNING]
> Disabling SSL verification (`verify=False`) makes your application vulnerable to Man-in-the-Middle (MITM) attacks. Only use this configuration in secure environments or when strictly necessary to bypass network handshakes.

---

## 4. Dynamic Domain Routing

TeraBox uses different domain extensions (e.g., `terabox.com`, `teraboxapp.com`, `1024terabox.com`, `terabox.app`) depending on geographic regions and network routing rules.

The `teraboxsdk` dynamically extracts the domain from the input URL you pass. For example, if you input:
`https://www.1024terabox.com/s/150xS47GYk5kJ6HnX0SGCaQ`

The SDK will automatically:
1. Detect that the request origin is `https://www.1024terabox.com`.
2. Direct all backend token parsing, lists, and direct link generation requests to `https://www.1024terabox.com/api/...`.

This prevents CORS errors, regional blockages, and redirects that trigger verification check failures.

---

## 5. Synchronous Examples (`TeraBoxClient`)

### Listing Files

To fetch files in a shared folder:

```python
from teraboxsdk import TeraBoxClient

# Initialize client
client = TeraBoxClient(ndus="YOUR_NDUS_COOKIE")

try:
    # Get file listing for a share link
    share_url = "https://teraboxapp.com/s/150xS47GYk5kJ6HnX0SGCaQ"
    listing = client.get_files(share_url)

    print(f"Total files found: {listing.total_count}")
    for file in listing.files:
        if file.is_dir:
            print(f"[Folder] {file.name}")
        else:
            print(f"[File] {file.name} - Size: {file.size_human}")
finally:
    client.close()
```

### Folder Hierarchy Lookup

To traverse subfolders and retrieve nested folder structures:

```python
from teraboxsdk import TeraBoxClient

client = TeraBoxClient(ndus="YOUR_NDUS_COOKIE")

try:
    share_url = "https://teraboxapp.com/s/150xS47GYk5kJ6HnX0SGCaQ"
    
    # get_folder_info returns detailed folder contents
    folder_info = client.get_folder_info(share_url, recursive=True)
    
    print(f"Folder Name: {folder_info.folder_name}")
    print(f"Total files size: {folder_info.total_size}")
    
    for file in folder_info.files:
        print(f"Path: {file.path} | Size: {file.size_human}")
finally:
    client.close()
```

### Generating Direct Download Links

Once you have a `FileInfo` object, you can generate a high-speed direct download link.

```python
from teraboxsdk import TeraBoxClient

client = TeraBoxClient(ndus="YOUR_NDUS_COOKIE")

try:
    share_url = "https://teraboxapp.com/s/150xS47GYk5kJ6HnX0SGCaQ"
    listing = client.get_files(share_url)
    
    for file in listing.files:
        if not file.is_dir:
            # Generate the direct download URL
            download_info = client.get_download_link(file)
            print(f"File: {download_info.filename}")
            print(f"Direct URL: {download_info.url}")
            print(f"Expires at: {download_info.expires_at}")
finally:
    client.close()
```

### Downloading Files with Progress

You can download a file directly using the SDK, which handles chunked writes and supports a progress callback:

```python
from teraboxsdk import TeraBoxClient

def progress_callback(pct: float, downloaded: int, total: int) -> None:
    print(f"Progress: {pct:.2f}% | Downloaded: {downloaded}/{total} bytes", end="\r")

client = TeraBoxClient(ndus="YOUR_NDUS_COOKIE")

try:
    share_url = "https://teraboxapp.com/s/150xS47GYk5kJ6HnX0SGCaQ"
    listing = client.get_files(share_url)
    
    # Get the first non-directory file
    files_to_download = [f for f in listing.files if not f.is_dir]
    if files_to_download:
        target_file = files_to_download[0]
        print(f"Starting download for: {target_file.name}")
        
        # Download the file to local directory
        client.download(target_file, dest_dir="./downloads", progress_callback=progress_callback)
        print("\nDownload complete!")
finally:
    client.close()
```

---

## 6. Asynchronous Examples (`AsyncTeraBoxClient`)

Using the asynchronous client is recommended for high-performance applications (such as Telegram bots or web scrapers) to prevent blocking the execution thread.

### Async Listing and Direct Link Extraction

```python
import asyncio
from teraboxsdk import AsyncTeraBoxClient

async def run_async_example():
    # Use AsyncTeraBoxClient context manager to handle automatic cleanup of HTTP clients
    async with AsyncTeraBoxClient(ndus="YOUR_NDUS_COOKIE", verify=False) as client:
        share_url = "https://teraboxapp.com/s/150xS47GYk5kJ6HnX0SGCaQ"
        listing = await client.get_files(share_url)
        
        print(f"Found {len(listing.files)} items in folder:")
        for file in listing.files:
            if not file.is_dir:
                download_info = await client.get_download_link(file)
                print(f"- Filename: {download_info.filename}")
                print(f"  Direct Link: {download_info.url}")
                print(f"  Size: {download_info.size_human}")

if __name__ == "__main__":
    asyncio.run(run_async_example())
```

### Async Downloading

```python
import asyncio
from teraboxsdk import AsyncTeraBoxClient

async def progress_callback(pct: float, downloaded: int, total: int) -> None:
    print(f"Downloading: {pct:.1f}% ({downloaded}/{total} bytes)", end="\r")

async def download_async():
    async with AsyncTeraBoxClient(ndus="YOUR_NDUS_COOKIE") as client:
        share_url = "https://teraboxapp.com/s/150xS47GYk5kJ6HnX0SGCaQ"
        listing = await client.get_files(share_url)
        
        files = [f for f in listing.files if not f.is_dir]
        if files:
            await client.download(files[0], dest_dir="./downloads", progress_callback=progress_callback)
            print("\nAsync download finished!")

if __name__ == "__main__":
    asyncio.run(download_async())
```

---

## 7. Error Handling

The SDK exposes specific exceptions matching API responses to help structure clean recovery code:

```python
from teraboxsdk import TeraBoxClient
from teraboxsdk.exceptions import (
    TeraBoxAuthError,
    TeraBoxNotFoundError,
    TeraBoxAPIError,
    TeraBoxURLError,
    TeraBoxError
)

client = TeraBoxClient(ndus="INVALID_OR_EXPIRED_COOKIE")

try:
    client.get_files("https://teraboxapp.com/s/150xS47GYk5kJ6HnX0SGCaQ")
except TeraBoxAuthError as e:
    print(f"Authentication failed! Please check your ndus cookie. Details: {e.message}")
except TeraBoxNotFoundError as e:
    print(f"The shared resource was deleted or the URL is invalid. Details: {e.message}")
except TeraBoxURLError as e:
    print(f"Malformed URL provided: {e.url}")
except TeraBoxAPIError as e:
    print(f"API returned error code {e.error_code}: {e.message}")
except TeraBoxError as e:
    print(f"Base SDK error: {e}")
finally:
    client.close()
```

---

## 8. Advanced Configuration (Timeouts & Proxies)

You can supply timeouts, proxy configs, and custom headers when initializing either client:

```python
from teraboxsdk import TeraBoxClient

client = TeraBoxClient(
    ndus="YOUR_NDUS_COOKIE",
    timeout=60.0,  # Increase timeout to 60 seconds
    proxy="http://127.0.0.1:7890",  # Set proxy server
    headers={"X-Custom-Header": "value"}  # Inject custom headers
)
```
