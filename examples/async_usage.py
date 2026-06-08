"""Example: Asynchronous TeraBox SDK usage."""

import asyncio

from teraboxsdk import AsyncTeraBoxClient

TERABOX_URL = "https://terabox.com/s/1ABCDEFexample"


def show_progress(pct: float, downloaded: int, total: int) -> None:
    """Print download progress."""
    bar = "█" * int(pct // 5) + "░" * (20 - int(pct // 5))
    print(f"\r[{bar}] {pct:.1f}% ({downloaded}/{total})", end="", flush=True)


async def main() -> None:
    async with AsyncTeraBoxClient(timeout=30.0) as client:
        try:
            # List files
            print(f"Listing files for: {TERABOX_URL}")
            listing = await client.get_files(TERABOX_URL)
            print(f"Found {len(listing.files)} files (total: {listing.total_count})")

            for file in listing.files:
                icon = "📁" if file.is_dir else "📄"
                print(f"  {icon} {file.name} ({file.size_human})")

            # Download first file
            if listing.files and not listing.files[0].is_dir:
                target = listing.files[0]
                print(f"\nDownloading: {target.name}")
                path = await client.download(
                    target, "./downloads", progress_callback=show_progress
                )
                print(f"\nSaved to: {path}")

        except Exception as exc:
            print(f"Error: {exc}")


if __name__ == "__main__":
    asyncio.run(main())
