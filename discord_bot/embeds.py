"""
Builds the tracker embed (the live task list per channel) and can parse an
existing embed back into task data on bot restart, since Discord is the
source of truth and nothing is saved to disk.
"""

import discord
from datetime import datetime

DONE_EMOJI = "🟢"
NOT_DONE_EMOJI = "⚪"


def build_tracker_embed(channel_name: str, tasks: dict) -> discord.Embed:
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
            line = f"{emoji} **{task_name}**"
            if info.get("link"):
                line += f" — [link]({info['link']})"
            lines.append(line)
        embed.description = "\n".join(lines)

    now = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    embed.set_footer(text=f"LAST UPDATE | {now}")
    return embed


def parse_embed_to_tasks(embed: discord.Embed) -> dict:
    """Rebuilds task state from an existing tracker embed's description.
    Used on bot startup to recover state without a database."""
    tasks = {}
    if not embed.description or "No tasks yet" in embed.description:
        return tasks

    for line in embed.description.split("\n"):
        line = line.strip()
        if not line:
            continue
        done = line.startswith(DONE_EMOJI)
        # strip emoji, then pull task name out of **bold**
        content = line.replace(DONE_EMOJI, "").replace(NOT_DONE_EMOJI, "").strip()
        if "**" not in content:
            continue
        parts = content.split("**")
        task_name = parts[1] if len(parts) > 1 else content
        link = None
        if "](" in content:
            link = content.split("](")[1].split(")")[0]
        tasks[task_name] = {"done": done, "link": link}
    return tasks
