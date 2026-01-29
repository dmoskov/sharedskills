#!/usr/bin/env python3
import discord
import aiohttp
import os
import sys
import fcntl
import json
import asyncio
import re
import hashlib
import mimetypes
import base64
from pathlib import Path
from collections import defaultdict
from typing import List, Dict, Optional, Union
from io import BytesIO

DEBOUNCE_SECONDS = 10  # Wait this long for more messages before responding

# Letta API configuration
LETTA_TIMEOUT_SECONDS = 60  # Timeout for single Letta API request
LETTA_MAX_RETRIES = 3  # Maximum number of retries for failed requests
LETTA_RETRY_BACKOFF = 2  # Exponential backoff multiplier
LETTA_RETRY_INITIAL_DELAY = 1  # Initial retry delay in seconds

# Chunking configuration
CHUNK_MAX_PARAGRAPHS = 3  # Maximum paragraphs per chunk
CHUNK_MAX_CHARS = 1900  # Maximum characters per chunk (Discord limit is 2000)
CHUNK_DELAY_SECONDS = 1.5  # Delay between chunks for natural reading pace

# Attachment configuration
MAX_ATTACHMENT_SIZE = 100 * 1024 * 1024  # 100MB - match Discord's max (boosted servers)
SUPPORTED_IMAGE_TYPES = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
ATTACHMENT_STORAGE_DIR = os.path.expanduser("~/.discordbot/attachments")


def split_into_paragraphs(text):
    """Split text into paragraphs based on natural breaks."""
    # Split on double newlines (standard paragraph breaks)
    paragraphs = re.split(r"\n\s*\n", text.strip())

    # Filter out empty paragraphs and strip whitespace
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    return paragraphs


def chunk_message(text, max_paragraphs=CHUNK_MAX_PARAGRAPHS, max_chars=CHUNK_MAX_CHARS):
    """
    Chunk a long message into smaller pieces based on natural paragraph breaks.

    Args:
        text: The full text to chunk
        max_paragraphs: Maximum number of paragraphs per chunk
        max_chars: Maximum character count per chunk

    Returns:
        List of text chunks ready to send
    """
    if not text or len(text) <= max_chars:
        # Short enough to send as-is
        return [text] if text else []

    paragraphs = split_into_paragraphs(text)

    if len(paragraphs) <= 1:
        # Single long paragraph - split by sentences as fallback
        sentence_parts = re.split(r"([.!?]+[\s\n]+)", text)
        # Rejoin sentences with their punctuation
        sentences = []
        for i in range(0, len(sentence_parts) - 1, 2):
            sentences.append("".join(sentence_parts[i : i + 2]).strip())
        # Add last part if odd count
        if len(sentence_parts) % 2 == 1 and sentence_parts[-1].strip():
            sentences.append(sentence_parts[-1].strip())
        paragraphs = [s for s in sentences if s]

    chunks = []
    current_chunk = []
    current_length = 0

    for para in paragraphs:
        para_length = len(para)

        # If adding this paragraph would exceed limits, finalize current chunk
        if current_chunk and (
            len(current_chunk) >= max_paragraphs
            or current_length + para_length + 2 > max_chars  # +2 for \n\n
        ):
            chunks.append("\n\n".join(current_chunk))
            current_chunk = []
            current_length = 0

        # If single paragraph is too long, split it further
        if para_length > max_chars:
            # If we have accumulated content, save it first
            if current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = []
                current_length = 0

            # Split long paragraph into chunks by character limit
            words = para.split()
            temp_chunk = []
            temp_length = 0

            for word in words:
                word_length = len(word) + 1  # +1 for space
                if temp_length + word_length > max_chars:
                    if temp_chunk:
                        chunks.append(" ".join(temp_chunk))
                    temp_chunk = [word]
                    temp_length = len(word)
                else:
                    temp_chunk.append(word)
                    temp_length += word_length

            if temp_chunk:
                chunks.append(" ".join(temp_chunk))
        else:
            # Add paragraph to current chunk
            current_chunk.append(para)
            current_length += para_length + 2  # +2 for \n\n separator

    # Add any remaining content
    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    return chunks


def get_file_hash(data: bytes) -> str:
    """Generate SHA256 hash of file data for deduplication."""
    return hashlib.sha256(data).hexdigest()


def is_image(filename: str) -> bool:
    """Check if a file is an image based on extension."""
    ext = Path(filename).suffix.lower()
    return ext in SUPPORTED_IMAGE_TYPES


async def download_attachment(attachment: discord.Attachment) -> Optional[Dict]:
    """
    Download and process a Discord attachment.

    Args:
        attachment: Discord attachment object

    Returns:
        Dict with attachment metadata, or None if processing failed
    """
    if attachment.size > MAX_ATTACHMENT_SIZE:
        print(f"Attachment {attachment.filename} too large ({attachment.size} bytes)")
        return {
            "filename": attachment.filename,
            "size": attachment.size,
            "content_type": attachment.content_type,
            "url": attachment.url,
            "error": "File too large to process",
        }

    try:
        # Download the file
        data = await attachment.read()
        file_hash = get_file_hash(data)

        # Determine content type
        content_type = (
            attachment.content_type or mimetypes.guess_type(attachment.filename)[0]
        )

        metadata = {
            "filename": attachment.filename,
            "size": attachment.size,
            "content_type": content_type,
            "url": attachment.url,
            "hash": file_hash,
        }

        # For images, include base64 data for sending to Letta
        if is_image(attachment.filename):
            # Store base64-encoded image data for multimodal API
            metadata["base64_data"] = base64.standard_b64encode(data).decode("utf-8")
            metadata["is_image"] = True

            try:
                from PIL import Image

                img = Image.open(BytesIO(data))
                metadata["image"] = {
                    "width": img.width,
                    "height": img.height,
                    "format": img.format,
                    "mode": img.mode,
                }
            except ImportError:
                # PIL not available, just include basic info
                metadata["image"] = {"format": "unknown"}
            except Exception as e:
                print(f"Error processing image {attachment.filename}: {e}")
                metadata["image"] = {"error": str(e)}

        # Optionally save file to storage
        storage_path = Path(ATTACHMENT_STORAGE_DIR) / file_hash[:2] / file_hash
        storage_path.parent.mkdir(parents=True, exist_ok=True)

        if not storage_path.exists():
            storage_path.write_bytes(data)
            metadata["stored_path"] = str(storage_path)

        return metadata

    except Exception as e:
        print(f"Error downloading attachment {attachment.filename}: {e}")
        return {
            "filename": attachment.filename,
            "url": attachment.url,
            "error": str(e),
        }


async def process_attachments(
    attachments: List[discord.Attachment], bot_config: Dict
) -> List[Dict]:
    """
    Process all attachments from a message.

    Args:
        attachments: List of Discord attachments
        bot_config: Bot configuration dict

    Returns:
        List of processed attachment metadata
    """
    # Check if attachments are enabled for this bot
    if not bot_config.get("enable_attachments", True):
        return []

    if not attachments:
        return []

    print(f"Processing {len(attachments)} attachment(s)...")
    results = []

    for attachment in attachments:
        metadata = await download_attachment(attachment)
        if metadata:
            results.append(metadata)

    return results


def format_attachments_for_message(attachments: List[Dict]) -> str:
    """
    Format attachment metadata for inclusion in Letta message.

    Args:
        attachments: List of attachment metadata dicts

    Returns:
        Formatted string describing the attachments
    """
    if not attachments:
        return ""

    lines = ["\n[Attachments:]"]
    for i, att in enumerate(attachments, 1):
        if "error" in att:
            lines.append(f"  {i}. {att['filename']} - Error: {att['error']}")
        else:
            size_kb = att["size"] / 1024
            line = f"  {i}. {att['filename']} ({size_kb:.1f} KB, {att.get('content_type', 'unknown')})"

            # Add image dimensions if available
            if "image" in att and "width" in att["image"]:
                img = att["image"]
                line += f" - {img['width']}x{img['height']} {img.get('format', '')}"

            lines.append(line)

    return "\n".join(lines)


async def extract_image_urls(text: str) -> List[str]:
    """
    Extract image URLs from text.

    Looks for:
    - Markdown image syntax: ![alt](url)
    - Plain URLs ending in image extensions
    - URLs with image MIME types

    Returns list of URLs found.
    """
    urls = []

    # Extract markdown image syntax: ![alt](url)
    markdown_pattern = r"!\[([^\]]*)\]\(([^\)]+)\)"
    for match in re.finditer(markdown_pattern, text):
        url = match.group(2)
        urls.append(url)

    # Extract plain URLs that look like images
    url_pattern = r"https?://[^\s<>\"]+\.(?:jpg|jpeg|png|gif|webp|bmp)"
    for match in re.finditer(url_pattern, text, re.IGNORECASE):
        url = match.group(0)
        if url not in urls:
            urls.append(url)

    return urls


async def download_image_from_url(
    url: str, session: aiohttp.ClientSession
) -> Optional[Dict]:
    """
    Download an image from a URL.

    Returns dict with:
    - data: bytes of the image
    - filename: suggested filename
    - content_type: MIME type
    Or None if download fails.
    """
    try:
        async with session.get(
            url, timeout=aiohttp.ClientTimeout(total=30)
        ) as response:
            if response.status != 200:
                print(f"Failed to download image from {url}: HTTP {response.status}")
                return None

            content_type = response.headers.get("content-type", "")

            # Check if it's an image
            if not content_type.startswith("image/"):
                print(f"URL {url} is not an image (content-type: {content_type})")
                return None

            # Download the data
            data = await response.read()

            # Check size (use same limit as attachments)
            if len(data) > MAX_ATTACHMENT_SIZE:
                print(f"Image from {url} too large: {len(data)} bytes")
                return None

            # Extract filename from URL or generate one
            filename = url.split("/")[-1].split("?")[0]  # Remove query params
            if not filename or "." not in filename:
                # Generate filename from content type
                ext = mimetypes.guess_extension(content_type) or ".png"
                filename = f"image{ext}"

            return {
                "data": data,
                "filename": filename,
                "content_type": content_type,
            }

    except Exception as e:
        print(f"Error downloading image from {url}: {type(e).__name__}: {e}")
        return None


async def extract_and_download_images(text: str) -> List[Dict]:
    """
    Extract image URLs from text and download them.

    Returns list of dicts with:
    - data: image bytes
    - filename: suggested filename
    - content_type: MIME type
    """
    urls = await extract_image_urls(text)

    if not urls:
        return []

    print(f"Found {len(urls)} image URL(s) in message")

    images = []
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        for url in urls:
            print(f"Downloading image from: {url}")
            image_data = await download_image_from_url(url, session)
            if image_data:
                images.append(image_data)
                print(f"Successfully downloaded: {image_data['filename']}")
            else:
                print(f"Failed to download: {url}")

    return images


def load_config():
    """Load and validate config from AWS Secrets Manager or local bots.json"""
    from config_loader import load_config as _load_config
    return _load_config()


def main(bot_name):
    config = load_config()

    if bot_name not in config["bots"]:
        print(f"Error: Bot '{bot_name}' not found in config")
        print(f"Available bots: {', '.join(config['bots'].keys())}")
        sys.exit(1)

    bot_config = config["bots"][bot_name]
    TOKEN = bot_config["discord_token"]
    LETTA = config.get("letta_url", "https://letta.cruciblegroup.io")
    AGENT = bot_config["agent_id"]

    # Per-bot lock and seen files (persistent across reboots)
    data_dir = os.path.expanduser(f"~/.discordbot/{bot_name}")
    os.makedirs(data_dir, exist_ok=True)
    LOCK = f"{data_dir}/bot.lock"
    SEEN_FILE = f"{data_dir}/seen.txt"
    MAX_SEEN = 10000  # Keep last N message IDs

    # Single instance lock
    try:
        lf = open(LOCK, "w")
        fcntl.flock(lf, fcntl.LOCK_EX | fcntl.LOCK_NB)
        lf.write(str(os.getpid()))
        lf.flush()
    except (IOError, OSError):
        print(f"LOCKED - {bot_name} already running, exiting")
        sys.exit(0)

    # Thread-safe seen tracking with exact match
    seen_ids = set()
    seen_lock = __import__("threading").Lock()

    def load_seen():
        try:
            with open(SEEN_FILE) as f:
                return set(line.strip() for line in f if line.strip())
        except FileNotFoundError:
            return set()

    def save_seen():
        # Keep only most recent IDs to prevent unbounded growth
        recent = sorted(seen_ids, key=int, reverse=True)[:MAX_SEEN]
        with open(SEEN_FILE, "w") as f:
            f.write("\n".join(recent) + "\n")

    seen_ids = load_seen()

    def seen_and_mark(mid):
        """Atomic check-and-mark to prevent race conditions"""
        mid_str = str(mid)
        with seen_lock:
            if mid_str in seen_ids:
                return True
            seen_ids.add(mid_str)
            # Append immediately for crash safety
            with open(SEEN_FILE, "a") as f:
                f.write(f"{mid_str}\n")
            # Periodic cleanup
            if len(seen_ids) > MAX_SEEN * 1.5:
                save_seen()
            return False

    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)

    # Message buffer for debouncing: {channel_id: [(author, content, attachments, msg_obj), ...]}
    message_buffer = defaultdict(list)
    buffer_timers = {}

    async def send_chunked_reply(text, reply_to_msg, images=None):
        """Send a potentially long message as multiple chunks with delays.

        Args:
            text: Message text to send
            reply_to_msg: Discord message to reply to
            images: Optional list of image dicts with 'data', 'filename', 'content_type'
        """
        # Extract and download any images from URLs in the text
        if images is None:
            images = await extract_and_download_images(text)

        chunks = chunk_message(text)

        if not chunks:
            return

        print(f"[{bot_name}] Sending {len(chunks)} chunk(s) (total: {len(text)} chars)")
        if images:
            print(f"[{bot_name}] Sending {len(images)} image(s)")

        # Send first chunk as a reply, with images if present
        first_chunk = chunks[0]
        print(f"[{bot_name}] Chunk 1/{len(chunks)}: {first_chunk[:60]}...")

        # Prepare files for Discord
        files = []
        if images:
            for img in images:
                file_obj = BytesIO(img["data"])
                files.append(discord.File(file_obj, filename=img["filename"]))

        if files:
            sent_msg = await reply_to_msg.reply(content=first_chunk, files=files)
        else:
            sent_msg = await reply_to_msg.reply(first_chunk)

        # Send remaining chunks as follow-ups with delays
        for i, chunk in enumerate(chunks[1:], start=2):
            await asyncio.sleep(CHUNK_DELAY_SECONDS)
            print(f"[{bot_name}] Chunk {i}/{len(chunks)}: {chunk[:60]}...")
            await sent_msg.channel.send(chunk)

    async def call_letta_and_reply(combined_content, reply_to_msg, images=None):
        """Send message to Letta and reply with response.

        Args:
            combined_content: Text content of the message
            reply_to_msg: Discord message to reply to
            images: Optional list of image dicts with 'base64_data' and 'content_type'
        """
        # Build multimodal content if images are present
        if images:
            # Letta multimodal format: content is an array of content blocks
            content = [{"type": "text", "text": combined_content}]
            for img in images:
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": img.get("content_type", "image/jpeg"),
                        "data": img["base64_data"],
                        "detail": "auto"
                    }
                })
            print(f"[{bot_name}] Calling Letta with {len(combined_content)} chars + {len(images)} image(s)...")
        else:
            content = combined_content
            print(f"[{bot_name}] Calling Letta with {len(combined_content)} chars...")

        # Retry loop with exponential backoff
        last_error = None
        for attempt in range(LETTA_MAX_RETRIES):
            if attempt > 0:
                delay = LETTA_RETRY_INITIAL_DELAY * (LETTA_RETRY_BACKOFF ** (attempt - 1))
                print(f"[{bot_name}] Retry {attempt}/{LETTA_MAX_RETRIES-1} after {delay}s delay...")
                await asyncio.sleep(delay)

            try:
                timeout = aiohttp.ClientTimeout(
                    total=LETTA_TIMEOUT_SECONDS,
                    connect=30,
                    sock_read=LETTA_TIMEOUT_SECONDS
                )
                async with aiohttp.ClientSession(timeout=timeout) as s:
                    async with s.post(
                        f"{LETTA}/v1/agents/{AGENT}/messages",
                        json={"messages": [{"role": "user", "content": content}]},
                    ) as r:
                        print(f"[{bot_name}] Status: {r.status}")

                        # Retry on 5xx server errors
                        if r.status >= 500:
                            last_error = f"Server error: {r.status}"
                            print(f"[{bot_name}] {last_error}, will retry...")
                            continue

                        # Don't retry on client errors (4xx)
                        if r.status >= 400:
                            print(f"[{bot_name}] Client error: {r.status}, not retrying")
                            return

                        data = await r.json()
                        for m in (
                            data.get("messages", []) if isinstance(data, dict) else data
                        ):
                            # Handle direct assistant_message responses
                            if m.get("message_type") == "assistant_message":
                                text = m.get("content", "")
                                print(f"[{bot_name}] Reply (assistant): {text[:60]}...")
                                await send_chunked_reply(text, reply_to_msg)
                                return
                            # Handle send_message tool calls (some agents use this)
                            if m.get("message_type") == "tool_call_message":
                                tool_call = m.get("tool_call", {})
                                if tool_call.get("name") == "send_message":
                                    try:
                                        args = json.loads(tool_call.get("arguments", "{}"))
                                        text = args.get("message", "")
                                        if text:
                                            print(
                                                f"[{bot_name}] Reply (tool): {text[:60]}..."
                                            )
                                            await send_chunked_reply(text, reply_to_msg)
                                            return
                                    except json.JSONDecodeError:
                                        pass
                        # Success - no retry needed
                        return

            except asyncio.TimeoutError:
                last_error = f"Request timed out after {LETTA_TIMEOUT_SECONDS}s"
                print(f"[{bot_name}] {last_error}, will retry...")
            except aiohttp.ClientError as e:
                last_error = f"Network error: {type(e).__name__}: {e}"
                print(f"[{bot_name}] {last_error}, will retry...")
            except Exception as e:
                # Unexpected error - log but don't retry
                print(f"[{bot_name}] Unexpected error: {type(e).__name__}: {e}")
                return

        # All retries exhausted
        print(f"[{bot_name}] All {LETTA_MAX_RETRIES} attempts failed. Last error: {last_error}")

    async def flush_buffer(channel_id):
        """Send buffered messages to Letta after debounce period"""
        if channel_id not in message_buffer or not message_buffer[channel_id]:
            return

        messages = message_buffer.pop(channel_id)
        buffer_timers.pop(channel_id, None)

        if not messages:
            return

        # Combine messages from same channel
        all_attachments = []
        if len(messages) == 1:
            author, content, attachments, msg_obj = messages[0]
            combined = f"[Discord message from {author}]: {content}"
            all_attachments = attachments
        else:
            # Multiple messages - format as a batch
            lines = []
            for author, content, attachments, _ in messages:
                lines.append(f"[{author}]: {content}")
                all_attachments.extend(attachments)
            combined = (
                f"[Discord messages - {len(messages)} messages in quick succession]:\n"
                + "\n".join(lines)
            )

        # Extract images for multimodal API and add text info for non-images
        image_attachments = [att for att in all_attachments if att.get("is_image") and att.get("base64_data")]
        non_image_attachments = [att for att in all_attachments if not att.get("is_image")]

        # Add text description for non-image attachments only
        if non_image_attachments:
            attachment_info = format_attachments_for_message(non_image_attachments)
            combined += attachment_info

        last_msg = messages[-1][3]  # Reply to the last message (now index 3)
        print(
            f"[{bot_name}] Flushing {len(messages)} message(s) from channel {channel_id}"
        )
        if image_attachments:
            print(f"[{bot_name}] Including {len(image_attachments)} image(s) for vision processing")

        await call_letta_and_reply(combined, last_msg, images=image_attachments if image_attachments else None)

    async def debounce_then_flush(channel_id):
        """Wait for debounce period then flush the buffer"""
        await asyncio.sleep(DEBOUNCE_SECONDS)
        await flush_buffer(channel_id)

    @client.event
    async def on_ready():
        print(
            f"READY [{bot_name}] {client.user} PID={os.getpid()} (debounce={DEBOUNCE_SECONDS}s)"
        )

    @client.event
    async def on_message(msg):
        if msg.author.id == client.user.id:
            return
        if seen_and_mark(msg.id):  # Atomic check-and-mark
            return

        # Strip mentions from content
        c = msg.content
        for m in msg.mentions:
            c = c.replace(f"<@{m.id}>", "").replace(f"<@!{m.id}>", "")
        c = c.strip() or "hi"

        channel_id = msg.channel.id
        print(f"[{bot_name}] MSG {msg.id} (ch={channel_id}): {c[:50]}...")

        # Process attachments if present
        attachments = []
        if msg.attachments:
            print(f"[{bot_name}] Message has {len(msg.attachments)} attachment(s)")
            attachments = await process_attachments(msg.attachments, bot_config)

        # Add to buffer
        message_buffer[channel_id].append(
            (msg.author.display_name, c, attachments, msg)
        )

        # Cancel existing timer if any
        if channel_id in buffer_timers:
            buffer_timers[channel_id].cancel()

        # Start new timer - will flush after DEBOUNCE_SECONDS of no new messages
        buffer_timers[channel_id] = asyncio.create_task(debounce_then_flush(channel_id))

    client.run(TOKEN)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python discord_bot.py <bot_name>")
        print("  bot_name: Name of bot from bots.json or AWS secret")
        print("")
        print("Config sources (in order):")
        print("  1. AWS_SECRET_NAME env var -> fetches from Secrets Manager")
        print("  2. CONFIG_FILE env var -> local JSON file path")
        print("  3. ./bots.json (default)")
        sys.exit(1)

    main(sys.argv[1])
