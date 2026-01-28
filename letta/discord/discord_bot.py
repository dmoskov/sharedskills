#!/usr/bin/env python3
import discord
import aiohttp
import os
import sys
import fcntl
import json
import asyncio
import re
from collections import defaultdict

DEBOUNCE_SECONDS = 10  # Wait this long for more messages before responding

# Chunking configuration
CHUNK_MAX_PARAGRAPHS = 3  # Maximum paragraphs per chunk
CHUNK_MAX_CHARS = 1900  # Maximum characters per chunk (Discord limit is 2000)
CHUNK_DELAY_SECONDS = 1.5  # Delay between chunks for natural reading pace


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


def load_config():
    """Load config from AWS Secrets Manager or local bots.json"""
    secret_name = os.environ.get("AWS_SECRET_NAME")

    if secret_name:
        import boto3

        client = boto3.client(
            "secretsmanager", region_name=os.environ.get("AWS_REGION", "us-east-1")
        )
        response = client.get_secret_value(SecretId=secret_name)
        return json.loads(response["SecretString"])

    # Fall back to local config file
    config_path = os.environ.get("CONFIG_FILE", "bots.json")
    with open(config_path) as f:
        return json.load(f)


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

    # Message buffer for debouncing: {channel_id: [(author, content, msg_obj), ...]}
    message_buffer = defaultdict(list)
    buffer_timers = {}

    async def send_chunked_reply(text, reply_to_msg):
        """Send a potentially long message as multiple chunks with delays."""
        chunks = chunk_message(text)

        if not chunks:
            return

        print(f"[{bot_name}] Sending {len(chunks)} chunk(s) (total: {len(text)} chars)")

        # Send first chunk as a reply
        first_chunk = chunks[0]
        print(f"[{bot_name}] Chunk 1/{len(chunks)}: {first_chunk[:60]}...")
        sent_msg = await reply_to_msg.reply(first_chunk)

        # Send remaining chunks as follow-ups with delays
        for i, chunk in enumerate(chunks[1:], start=2):
            await asyncio.sleep(CHUNK_DELAY_SECONDS)
            print(f"[{bot_name}] Chunk {i}/{len(chunks)}: {chunk[:60]}...")
            await sent_msg.channel.send(chunk)

    async def call_letta_and_reply(combined_content, reply_to_msg):
        """Send message to Letta and reply with response"""
        print(f"[{bot_name}] Calling Letta with {len(combined_content)} chars...")
        try:
            timeout = aiohttp.ClientTimeout(total=300, connect=60, sock_read=300)
            async with aiohttp.ClientSession(timeout=timeout) as s:
                async with s.post(
                    f"{LETTA}/v1/agents/{AGENT}/messages",
                    json={"messages": [{"role": "user", "content": combined_content}]},
                ) as r:
                    print(f"[{bot_name}] Status: {r.status}")
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
        except Exception as e:
            print(f"[{bot_name}] Error: {type(e).__name__}: {e}")

    async def flush_buffer(channel_id):
        """Send buffered messages to Letta after debounce period"""
        if channel_id not in message_buffer or not message_buffer[channel_id]:
            return

        messages = message_buffer.pop(channel_id)
        buffer_timers.pop(channel_id, None)

        if not messages:
            return

        # Combine messages from same channel
        if len(messages) == 1:
            author, content, msg_obj = messages[0]
            combined = f"[Discord message from {author}]: {content}"
        else:
            # Multiple messages - format as a batch
            lines = [f"[{author}]: {content}" for author, content, _ in messages]
            combined = (
                f"[Discord messages - {len(messages)} messages in quick succession]:\n"
                + "\n".join(lines)
            )

        last_msg = messages[-1][2]  # Reply to the last message
        print(
            f"[{bot_name}] Flushing {len(messages)} message(s) from channel {channel_id}"
        )

        await call_letta_and_reply(combined, last_msg)

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

        # Add to buffer
        message_buffer[channel_id].append((msg.author.display_name, c, msg))

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
