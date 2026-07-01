"""
Turns raw Messenger text like:
    /update reading-manhwa chapter-12 https://example.com/ch12
into a structured command the Discord-side functions understand.

Expected formats (channel_name is always required first, since Messenger has
no concept of "current channel" the way Discord slash commands do):
    /add_channel <channel_name>
    /add <channel_name> <link> [progress]
    /update <channel_name> <task_name> [link]
    /done <channel_name> <task_name>
    /undone <channel_name> <task_name>
    /recommend <channel_name>
    /ask <channel_name> <question>
"""

import shlex
from typing import Optional


class ParsedCommand:
    def __init__(self, command: str, channel_name: str,
                 task_name: Optional[str] = None, link: Optional[str] = None,
                 progress: int = 0, message: Optional[str] = None):
        self.command = command
        self.channel_name = channel_name
        self.task_name = task_name
        self.link = link
        self.progress = progress
        self.message = message


def parse(text: str) -> Optional[ParsedCommand]:
    text = text.strip()
    if not text.startswith("/"):
        return None

    try:
        parts = shlex.split(text[1:])
    except ValueError:
        return None
    if not parts:
        return None

    command = parts[0].lower()
    args = parts[1:]

    if command == "add_channel":
        if len(args) < 1:
            return None
        return ParsedCommand(command, channel_name=args[0])

    if command == "add":
        if len(args) < 2:
            return None
        progress = 0
        if len(args) > 2 and args[2].isdigit():
            progress = int(args[2])
        return ParsedCommand(command, channel_name=args[0], link=args[1], progress=progress)

    if command == "update":
        if len(args) < 2:
            return None
        progress = 0
        if len(args) > 2 and args[2].isdigit():
            progress = int(args[2])
        return ParsedCommand(command, channel_name=args[0], link=args[1], progress=progress)

    if command == "update":
        if len(args) < 2:
            return None
        channel_name = args[0]
        progress = 0
        if args[-1].isdigit():
            progress = int(args[-1])
            args = args[:-1]

        # Convenience form: /update <channel> <link> [progress]. The command
        # handler will infer the task from the cleaned page title.
        if args[1].startswith(("http://", "https://")):
            return ParsedCommand(command, channel_name, task_name=args[1], link=args[1], progress=progress)

        task_name = args[1]
        link = args[2] if len(args) > 2 else None
        return ParsedCommand(command, channel_name, task_name, link, progress=progress)

    if command in ("done", "undone"):
        if len(args) < 2:
            return None
        channel_name, task_name = args[0], args[1]
        return ParsedCommand(command, channel_name, task_name)

    if command == "recommend":
        if len(args) < 1:
            return None
        return ParsedCommand(command, channel_name=args[0])

    if command == "ask":
        if len(args) < 2:
            return None
        return ParsedCommand(command, channel_name=args[0], message=" ".join(args[1:]))

    return None
