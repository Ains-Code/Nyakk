"""
Turns raw Messenger text like:
    /update reading-manhwa chapter-12 https://example.com/ch12
into a structured command the Discord-side functions understand.

Expected formats (channel_name is now always required first, since Messenger
has no concept of "current channel" the way Discord slash commands do):
    /add_channel <channel_name>
    /add <channel_name> <task_name> [link]
    /update <channel_name> <task_name> [link]
    /done <channel_name> <task_name>
    /undone <channel_name> <task_name>
"""

from typing import Optional


class ParsedCommand:
    def __init__(self, command: str, channel_name: str,
                 task_name: Optional[str] = None, link: Optional[str] = None):
        self.command = command
        self.channel_name = channel_name
        self.task_name = task_name
        self.link = link


def parse(text: str) -> Optional[ParsedCommand]:
    text = text.strip()
    if not text.startswith("/"):
        return None

    parts = text[1:].split()
    if not parts:
        return None

    command = parts[0].lower()
    args = parts[1:]

    if command == "add_channel":
        if len(args) < 1:
            return None
        return ParsedCommand(command, channel_name=args[0])

    if command in ("add", "update"):
        if len(args) < 2:
            return None
        channel_name, task_name = args[0], args[1]
        link = args[2] if len(args) > 2 else None
        return ParsedCommand(command, channel_name, task_name, link)

    if command in ("done", "undone"):
        if len(args) < 2:
            return None
        channel_name, task_name = args[0], args[1]
        return ParsedCommand(command, channel_name, task_name)

    return None
