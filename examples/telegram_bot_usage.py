"""Example: Telegram bot using Pyrogram with TeraBox SDK (async).

Dependencies:
    pip install pyrogram tgcrypto teraboxsdk

Environment:
    API_ID=your_api_id
    API_HASH=your_api_hash
    BOT_TOKEN=your_bot_token
"""

from __future__ import annotations

import logging
import os

from pyrogram import Client, filters
from pyrogram.types import Message

from teraboxsdk import AsyncTeraBoxClient
from teraboxsdk.exceptions import TeraBoxError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pyrogram client
app = Client(
    "terabox_bot",
    api_id=int(os.environ["API_ID"]),
    api_hash=os.environ["API_HASH"],
    bot_token=os.environ["BOT_TOKEN"],
)

# TeraBox client (reused across requests)
tb_client: AsyncTeraBoxClient | None = None


async def get_tb_client() -> AsyncTeraBoxClient:
    """Get or create the shared TeraBox client."""
    global tb_client
    if tb_client is None:
        tb_client = AsyncTeraBoxClient(timeout=30.0)
    return tb_client


@app.on_message(filters.command("start"))
async def start_handler(client: Client, message: Message) -> None:
    await message.reply(
        "👋 Send me a TeraBox link and I'll fetch the files for you!\n\n"
        "Supported formats:\n"
        "• https://terabox.com/s/1ABCDEF\n"
        "• https://1024terabox.com/s/1ABCDEF"
    )


@app.on_message(filters.regex(r"(terabox|1024terabox)\.com/s/[a-zA-Z0-9_-]+"))
async def terabox_link_handler(client: Client, message: Message) -> None:
    """Handle TeraBox share links."""
    url = message.text.strip()
    processing_msg = await message.reply("🔍 Fetching files...")

    try:
        tb = await get_tb_client()
        listing = await tb.get_files(url)

        if listing.is_empty:
            await processing_msg.edit("📂 The share is empty.")
            return

        # Build response
        lines = [f"📁 <b>{listing.total_count} item(s) found:</b>", ""]
        for i, file in enumerate(listing.files[:20], 1):
            icon = "📁" if file.is_dir else "📄"
            lines.append(f"{i}. {icon} <code>{file.name}</code> ({file.size_human})")

        if listing.total_count > 20:
            lines.append(f"\n... and {listing.total_count - 20} more")

        await processing_msg.edit("\n".join(lines), disable_web_page_preview=True)

        # Auto-download first file if it's small (< 50MB)
        first = listing.files[0]
        if not first.is_dir and first.size < 50 * 1024 * 1024:
            await processing_msg.edit_text("⬇️ Downloading first file...")
            try:
                path = await tb.download(first, "./downloads")
                await message.reply_document(str(path), caption=f"📄 {first.name}")
                await processing_msg.delete()
                # Cleanup
                path.unlink(missing_ok=True)
            except Exception as exc:
                await processing_msg.edit(f"❌ Download failed: {exc}")

    except TeraBoxError as exc:
        logger.error("TeraBox error: %s", exc)
        await processing_msg.edit(f"❌ Error: {exc.message}")
    except Exception as exc:
        logger.exception("Unexpected error")
        await processing_msg.edit(f"❌ Unexpected error: {exc}")


@app.on_message(filters.command("download"))
async def download_command(client: Client, message: Message) -> None:
    """Download specific file by index: /download <url> <index>."""
    parts = message.text.split(maxsplit=2)
    if len(parts) < 2:
        await message.reply("Usage: /download <terabox_url> [file_index]")
        return

    url = parts[1]
    index = int(parts[2]) - 1 if len(parts) > 2 else 0

    processing = await message.reply("⬇️ Downloading...")
    try:
        tb = await get_tb_client()
        listing = await tb.get_files(url)

        if not listing.files or index >= len(listing.files):
            await processing.edit("❌ File not found at that index.")
            return

        target = listing.files[index]
        if target.is_dir:
            await processing.edit("❌ Cannot download a folder directly.")
            return

        path = await tb.download(target, "./downloads")
        await message.reply_document(str(path), caption=f"📄 {target.name}")
        await processing.delete()
        path.unlink(missing_ok=True)

    except TeraBoxError as exc:
        await processing.edit(f"❌ Error: {exc.message}")
    except Exception as exc:
        logger.exception("Download error")
        await processing.edit(f"❌ Error: {exc}")


@app.on_message()
async def fallback_handler(client: Client, message: Message) -> None:
    """Handle non-command text that doesn't match TeraBox links."""
    if message.text and not message.text.startswith("/"):
        if "terabox" not in message.text.lower():
            await message.reply(
                "Send me a TeraBox link like:\n"
                "<code>https://terabox.com/s/1ABCDEF</code>",
                disable_web_page_preview=True,
            )


async def shutdown() -> None:
    """Cleanup on shutdown."""
    global tb_client
    if tb_client:
        await tb_client.close()
        tb_client = None


if __name__ == "__main__":
    try:
        app.run()
    finally:
        # Pyrogram doesn't have async cleanup hooks easily,
        # but in production you'd handle this in a lifespan manager.
        pass
