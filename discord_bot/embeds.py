"""
Builds the tracker embed shown in each channel.
Shows chapter/episode progress and clickable page titles.
"""

import re
from datetime import datetime

import discord

DONE_EMOJI = "🟢"
NOT_DONE_EMOJI = "⚪"
PROGRESS_RE = re.compile(r"`(?P<label>Chapter|Episode|Progress)\s+(?P<value>\d+)`")
LINK_RE = re.compile(r"\[(?P<title>[^\]]+)\]\((?P<link>[^)]+)\)")


def _progress_text(progress_label: str, progress: int) -> str:
    return f"`{progress_label} {progress}`" if progress and progress > 0 else ""


def _display_text(task_name: str, display: str | None) -> str:
    return display or task_name


def build_tracker_embed(channel_name: str, tasks: dict, progress_label: str = "Progress") -> discord.Embed:
    embed = discord.Embed(
        title=f"{channel_name} — Task Tracker",
        color=discord.Color.dark_grey(),
    )

    if not tasks:
        embed.description = "No tasks yet. Use `/add` to create one."
    else:
        lines = []
        for task_name, info in tasks.items():
            emoji = DONE_EMOJI if info["done"] else NOT_DONE_EMOJI
            link = info.get("link")
            display = _display_text(task_name, info.get("display"))
            progress = info.get("progress", 0)
            progress_prefix = _progress_text(progress_label, progress)

            # Requested display order: [PROGRESS] - [PAGE_TITLE]. Keep the page title
            # clickable when a source link is available, and avoid repeating the same
            # long title as both display text and subtitle.
            if link:
                title_text = f"**[{display}]({link})**"
            else:
                title_text = f"**{display}**"

            if progress_prefix:
                line = f"{emoji} {progress_prefix} - {title_text}"
            else:
                line = f"{emoji} {title_text}"

            lines.append(line)

        embed.description = "\n".join(lines)

    now = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    embed.set_footer(text=f"LAST UPDATE | {now}")
    return embed


def parse_embed_to_tasks(embed: discord.Embed) -> dict:
    """Rebuilds task state from an existing tracker embed on bot restart."""
    tasks = {}
    if not embed.description or "No tasks yet" in embed.description:
        return tasks

    for line in embed.description.split("\n"):
        line = line.strip()
        if not line:
            continue
        done = line.startswith(DONE_EMOJI)
        content = line.replace(DONE_EMOJI, "").replace(NOT_DONE_EMOJI, "").strip()
        if "**" not in content:
            continue

        progress = 0
        match = PROGRESS_RE.search(content)
        if match:
            progress = int(match.group("value"))
            content = PROGRESS_RE.sub("", content, count=1).strip()
            if content.startswith("-"):
                content = content[1:].strip()

        parts = content.split("**")
        display_markup = parts[1] if len(parts) > 1 else None
        if not display_markup:
            continue

        link = None
        display = display_markup
        link_match = LINK_RE.search(display_markup)
        if link_match:
            display = link_match.group("title")
            link = link_match.group("link")

        # Backward compatibility with the old format:
        # **Display** — task_name `Progress X`
        if " — " in content:
            after_display = content.split(" — ", 1)[1]
            task_name = PROGRESS_RE.sub("", after_display).strip()
        else:
            task_name = display

        tasks[task_name] = {"done": done, "link": link, "display": display, "progress": progress}
    return tasks
