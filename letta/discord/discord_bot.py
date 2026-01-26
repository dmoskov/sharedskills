#!/usr/bin/env python3
import discord, aiohttp, os, sys, fcntl, json, asyncio
from collections import defaultdict

DEBOUNCE_SECONDS = 10  # Wait this long for more messages before responding

def load_config():
    """Load config from AWS Secrets Manager or local bots.json"""
    secret_name = os.environ.get("AWS_SECRET_NAME")

    if secret_name:
        import boto3
        client = boto3.client("secretsmanager", region_name=os.environ.get("AWS_REGION", "us-east-1"))
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
        lf = open(LOCK, 'w')
        fcntl.flock(lf, fcntl.LOCK_EX | fcntl.LOCK_NB)
        lf.write(str(os.getpid()))
        lf.flush()
    except:
        print(f"LOCKED - {bot_name} already running, exiting")
        sys.exit(0)

    # Thread-safe seen tracking with exact match
    seen_ids = set()
    seen_lock = __import__('threading').Lock()

    def load_seen():
        try:
            with open(SEEN_FILE) as f:
                return set(line.strip() for line in f if line.strip())
        except FileNotFoundError:
            return set()

    def save_seen():
        # Keep only most recent IDs to prevent unbounded growth
        recent = sorted(seen_ids, key=int, reverse=True)[:MAX_SEEN]
        with open(SEEN_FILE, 'w') as f:
            f.write('\n'.join(recent) + '\n')

    seen_ids = load_seen()

    def seen_and_mark(mid):
        """Atomic check-and-mark to prevent race conditions"""
        mid_str = str(mid)
        with seen_lock:
            if mid_str in seen_ids:
                return True
            seen_ids.add(mid_str)
            # Append immediately for crash safety
            with open(SEEN_FILE, 'a') as f:
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

    async def call_letta_and_reply(combined_content, reply_to_msg):
        """Send message to Letta and reply with response"""
        print(f"[{bot_name}] Calling Letta with {len(combined_content)} chars...")
        try:
            timeout = aiohttp.ClientTimeout(total=300, connect=60, sock_read=300)
            async with aiohttp.ClientSession(timeout=timeout) as s:
                async with s.post(f"{LETTA}/v1/agents/{AGENT}/messages",
                    json={"messages":[{"role":"user","content": combined_content}]}) as r:
                    print(f"[{bot_name}] Status: {r.status}")
                    data = await r.json()
                    for m in (data.get("messages",[]) if isinstance(data,dict) else data):
                        # Handle direct assistant_message responses
                        if m.get("message_type") == "assistant_message":
                            text = m.get("content","")[:1900]
                            print(f"[{bot_name}] Reply (assistant): {text[:60]}...")
                            await reply_to_msg.reply(text)
                            return
                        # Handle send_message tool calls (some agents use this)
                        if m.get("message_type") == "tool_call_message":
                            tool_call = m.get("tool_call", {})
                            if tool_call.get("name") == "send_message":
                                try:
                                    args = json.loads(tool_call.get("arguments", "{}"))
                                    text = args.get("message", "")[:1900]
                                    if text:
                                        print(f"[{bot_name}] Reply (tool): {text[:60]}...")
                                        await reply_to_msg.reply(text)
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
            combined = f"[Discord messages - {len(messages)} messages in quick succession]:\n" + "\n".join(lines)

        last_msg = messages[-1][2]  # Reply to the last message
        print(f"[{bot_name}] Flushing {len(messages)} message(s) from channel {channel_id}")

        await call_letta_and_reply(combined, last_msg)

    async def debounce_then_flush(channel_id):
        """Wait for debounce period then flush the buffer"""
        await asyncio.sleep(DEBOUNCE_SECONDS)
        await flush_buffer(channel_id)

    @client.event
    async def on_ready():
        print(f"READY [{bot_name}] {client.user} PID={os.getpid()} (debounce={DEBOUNCE_SECONDS}s)")

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
