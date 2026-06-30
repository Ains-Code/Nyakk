"""
Core logic for add/update/done/undone/add-channel. Both the Discord slash
commands and the Messenger text-command parser call into these so behavior
stays identical regardless of where the command came from.

Each function returns a (success: bool, reply_text: str) tuple. Discord-side
callers additionally need to refresh the embed in the channel after a
successful change (the bot.py wrapper handles that part, since it has
the discord.Client).
"""

from typing import Optional
from discord_bot import state


def add_task(channel_id: int, task_name: str, link: Optional[str] = None) -> tuple[bool, str]:
    if not state.is_registered(channel_id):
        return False, "That channel isn't registered as a tracker yet."
    state.add_task(channel_id, task_name, link)
    return True, f"Added task **{task_name}** (not done)."


def update_task(channel_id: int, task_name: str, link: Optional[str] = None) -> tuple[bool, str]:
    if not state.is_registered(channel_id):
        return False, "That channel isn't registered as a tracker yet."
    ok = state.update_task(channel_id, task_name, link)
    if not ok:
        return False, f"Task **{task_name}** not found in this tracker."
    return True, f"Updated task **{task_name}**."


def mark_done(channel_id: int, task_name: str, done: bool) -> tuple[bool, str]:
    if not state.is_registered(channel_id):
        return False, "That channel isn't registered as a tracker yet."
    ok = state.set_task_done(channel_id, task_name, done)
    if not ok:
        return False, f"Task **{task_name}** not found in this tracker."
    status = "done" if done else "not done"
    return True, f"Marked **{task_name}** as {status}."
