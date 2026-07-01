"""
Core logic for add/update/done/undone. Both Discord slash commands and
WhatsApp text commands call into these functions.

When a link is provided, we automatically fetch its page title so the
embed shows "One Piece Chapter 1100" instead of a raw URL.
"""

from typing import Optional
from discord_bot import state
from shared.link_title import fetch_title


async def add_task(channel_id: int, task_name: str, link: Optional[str] = None) -> tuple[bool, str]:
    if not state.is_registered(channel_id):
        return False, "That channel isn't registered as a tracker yet."

    title = None
    if link:
        title = await fetch_title(link)
        if not title:
            title = link  # fallback to raw link if fetch fails

    state.add_task(channel_id, task_name, link=link, display=title)
    display_info = f' — "{title}"' if title and title != link else ""
    return True, f"Added task **{task_name}**{display_info} (not done)."


async def update_task(channel_id: int, task_name: str, link: Optional[str] = None) -> tuple[bool, str]:
    if not state.is_registered(channel_id):
        return False, "That channel isn't registered as a tracker yet."

    title = None
    if link:
        title = await fetch_title(link)
        if not title:
            title = link

    ok = state.update_task(channel_id, task_name, link=link, display=title)
    if not ok:
        return False, f"Task **{task_name}** not found in this tracker."
    return True, f"Updated task **{task_name}**."


async def mark_done(channel_id: int, task_name: str, done: bool) -> tuple[bool, str]:
    if not state.is_registered(channel_id):
        return False, "That channel isn't registered as a tracker yet."
    ok = state.set_task_done(channel_id, task_name, done)
    if not ok:
        return False, f"Task **{task_name}** not found in this tracker."
    status = "done" if done else "not done"
    return True, f"Marked **{task_name}** as {status}."
