"""Example: Synchronous TeraBox SDK usage."""

from teraboxsdk import TeraBoxClient

TERABOX_URL = "https://terabox.com/s/1ABCDEFexample"


def show_progress(pct: float, downloaded: int, total: int) -> None:
    """Print download progress."""
    bar = "█" * int(pct // 5) + "░" * (20 - int(pct // 5))
    print(f"\r[{bar}] {pct:.1f}% ({downloaded}/{total})", end="", flush=True)


def main() -> None:
    client = TeraBoxClient(timeout=30.0)

    try:
        # List files
        print(f"Listing files for: {TERABOX_URL}")
        listing = client.get_files(TERABOX_URL)
        print(f"Found {len(listing.files)} files (total: {listing.total_count})")

        for file in listing.files:
            print(f"  {'📁' if file.is_dir else '📄'} {file.name} ({file.size_human})")

        # Download first file
        if listing.files and not listing.files[0].is_dir:
            target = listing.files[0]
            print(f"\nDownloading: {target.name}")
            path = client.download(target, "./downloads", progress_callback=show_progress)
            print(f"\nSaved to: {path}")

    except Exception as exc:
        print(f"Error: {exc}")
    finally:
        client.close()


if __name__ == "__main__":
    main()
