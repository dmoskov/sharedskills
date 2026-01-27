#!/usr/bin/env python3
"""Test the message metadata formatting"""
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock

# Mock Discord channel types
class MockDMChannel:
    pass

class MockGroupChannel:
    def __init__(self, name=None):
        self.name = name

class MockServerChannel:
    def __init__(self, name):
        self.name = name


def make_mock_message(content, author_name, channel_type="server", attachments=None,
                      server_name="Test Server", channel_name="general"):
    msg = Mock()
    msg.content = content
    msg.author = Mock()
    msg.author.display_name = author_name
    msg.created_at = datetime(2025, 1, 27, 15, 30, 0, tzinfo=timezone.utc)
    msg.attachments = []

    if attachments:
        for filename, content_type in attachments:
            att = Mock()
            att.filename = filename
            att.content_type = content_type
            msg.attachments.append(att)

    if channel_type == "dm":
        msg.channel = MockDMChannel()
        msg.guild = None
    elif channel_type == "group":
        msg.channel = MockGroupChannel(name="Group Chat")
        msg.guild = None
    else:
        msg.channel = MockServerChannel(name=channel_name)
        msg.guild = Mock()
        msg.guild.name = server_name

    return msg


def format_message_metadata(msg):
    """Extract rich metadata from a Discord message - mirrors discord_bot.py"""
    # Channel type and location
    if isinstance(msg.channel, MockDMChannel):
        location = "DM"
    elif isinstance(msg.channel, MockGroupChannel):
        location = f"Group DM ({msg.channel.name or 'unnamed'})"
    else:
        server = msg.guild.name if msg.guild else "Unknown Server"
        channel = msg.channel.name if hasattr(msg.channel, 'name') else "unknown"
        location = f"#{channel} in {server}"

    # Timestamp
    ts = msg.created_at.strftime("%Y-%m-%d %H:%M UTC")

    # Attachments
    attachments = []
    for att in msg.attachments:
        if att.content_type and att.content_type.startswith("image/"):
            attachments.append(f"[image: {att.filename}]")
        elif att.content_type and att.content_type.startswith("video/"):
            attachments.append(f"[video: {att.filename}]")
        elif att.content_type and att.content_type.startswith("audio/"):
            attachments.append(f"[audio: {att.filename}]")
        else:
            attachments.append(f"[file: {att.filename}]")

    return {
        "location": location,
        "timestamp": ts,
        "attachments": attachments,
        "author": msg.author.display_name,
    }


def format_single(metadata, content):
    parts = [f"[{metadata['timestamp']}] {metadata['author']}: {content}"]
    if metadata["attachments"]:
        parts.append(" ".join(metadata["attachments"]))
    return " ".join(parts)


def test_dm():
    msg = make_mock_message("hey there", "Alice", channel_type="dm")
    meta = format_message_metadata(msg)
    assert meta["location"] == "DM", f"Expected 'DM', got '{meta['location']}'"
    assert meta["author"] == "Alice"
    assert meta["timestamp"] == "2025-01-27 15:30 UTC"
    print(f"✓ DM test passed: {meta['location']}")

    formatted = format_single(meta, "hey there")
    print(f"  Output: {formatted}")


def test_server_channel():
    msg = make_mock_message("hello world", "Bob", channel_type="server",
                           server_name="My Server", channel_name="random")
    meta = format_message_metadata(msg)
    assert meta["location"] == "#random in My Server", f"Got: {meta['location']}"
    print(f"✓ Server channel test passed: {meta['location']}")

    formatted = format_single(meta, "hello world")
    print(f"  Output: {formatted}")


def test_with_attachments():
    msg = make_mock_message("check this out", "Carol", channel_type="server",
                           attachments=[
                               ("photo.jpg", "image/jpeg"),
                               ("doc.pdf", "application/pdf"),
                               ("song.mp3", "audio/mpeg"),
                           ])
    meta = format_message_metadata(msg)
    assert len(meta["attachments"]) == 3
    assert "[image: photo.jpg]" in meta["attachments"]
    assert "[file: doc.pdf]" in meta["attachments"]
    assert "[audio: song.mp3]" in meta["attachments"]
    print(f"✓ Attachments test passed: {meta['attachments']}")

    formatted = format_single(meta, "check this out")
    print(f"  Output: {formatted}")


def test_full_format():
    """Test the full message format as sent to Letta"""
    msg = make_mock_message("look at this", "Dave", channel_type="server",
                           server_name="Cool Server", channel_name="general",
                           attachments=[("screenshot.png", "image/png")])
    meta = format_message_metadata(msg)

    # Single message format
    msg_line = format_single(meta, "look at this")
    combined = f"[Discord - {meta['location']}]\n{msg_line}"

    print(f"✓ Full format test:")
    print(f"---\n{combined}\n---")


if __name__ == "__main__":
    test_dm()
    test_server_channel()
    test_with_attachments()
    test_full_format()
    print("\n✓ All tests passed!")
