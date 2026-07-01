"""
Builds the tracker embed shown in each channel.
Shows chapter/episode progress and clickable page titles.
"""

import discord
from datetime import datetime

DONE_EMOJI = "🟢"
NOT_DONE_EMOJI = "⚪"


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
            display = info.get("display")
            progress = info.get("progress", 0)

            # Build task line - display title first, then task name as subtitle
            if link and display:
                line = f"{emoji} **{display}** — {task_name}"
            elif link:
                line = f"{emoji} **{task_name}** — [link]({link})"
            else:
                line = f"{emoji} **{task_name}**"

            # Append progress if set
            if progress and progress > 0:
                line += f" `{progress_label} {progress}`"

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

    import re
    PROGRESS_RE = re.compile(r"`(?:Chapter|Episode|Progress)\s+(\d+)`")

    for line in embed.description.split("\n"):
        line = line.strip()
        if not line:
            continue
        done = line.startswith(DONE_EMOJI)
        content = line.replace(DONE_EMOJI, "").replace(NOT_DONE_EMOJI, "").strip()
        if "**" not in content:
            continue

        parts = content.split("**")
        task_name = parts[1] if len(parts) > 1 else content

        link = None
        display = None
        progress = 0

        if "](" in content:
            bracket_content = content.split("[")[1] if "[" in content else ""
            display = bracket_content.split("]")[0] if "]" in bracket_content else None
            link = content.split("](")[1].split(")")[0] if "](" in content else None

        match = PROGRESS_RE.search(content)
        if match:
            progress = int(match.group(1))

        tasks[task_name] = {"done": done, "link": link, "display": display, "progress": progress}
    return tasks
