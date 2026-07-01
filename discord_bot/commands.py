"""
Core command logic. Both Discord slash commands and WhatsApp text commands
call into these functions.
"""

from typing import Optional
from discord_bot import state
from shared.link_title import fetch_title


async def add_task(channel_id: int, link: str, progress: int = 0) -> tuple[bool, str]:
    if not state.is_registered(channel_id):
        return False, "That channel isn't registered as a tracker yet."
    
    title = None
    if link:
        title = await fetch_title(link)
        if not title:
            title = link
    
    # Use title as task name
    task_name = title or link
    state.add_task(channel_id, task_name, link=link, display=title, progress=progress)
    label = state.get_progress_label(channel_id)
    progress_info = f" ({label} {progress})" if progress > 0 else ""
    return True, f"Added task **{task_name}**{progress_info} (not done)."


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
        return False, f"Task **{task_name}** not found."
    return True, f"Updated task **{task_name}**."


async def remove_task(channel_id: int, task_name: str) -> tuple[bool, str]:
    if not state.is_registered(channel_id):
        return False, "That channel isn't registered as a tracker yet."
    ok = state.remove_task(channel_id, task_name)
    if not ok:
        return False, f"Task **{task_name}** not found."
    return True, f"Removed task **{task_name}**."


async def edit_task(channel_id: int, task_name: str,
                    new_name: Optional[str] = None,
                    new_link: Optional[str] = None,
                    new_progress: Optional[int] = None) -> tuple[bool, str]:
    if not state.is_registered(channel_id):
        return False, "That channel isn't registered as a tracker yet."

    changes = []

    if new_name:
        ok = state.edit_task_name(channel_id, task_name, new_name)
        if not ok:
            return False, f"Task **{task_name}** not found."
        changes.append(f"name → **{new_name}**")
        task_name = new_name  # use new name for subsequent edits

    if new_link:
        title = await fetch_title(new_link) or new_link
        ok = state.edit_task_link(channel_id, task_name, new_link, title)
        if not ok:
            return False, f"Task **{task_name}** not found."
        changes.append(f"link → [{title}]({new_link})")

    if new_progress is not None:
        ok = state.edit_task_progress(channel_id, task_name, new_progress)
        if not ok:
            return False, f"Task **{task_name}** not found."
        label = state.get_progress_label(channel_id)
        changes.append(f"{label} → **{new_progress}**")

    if not changes:
        return False, "Nothing to edit — provide at least one of: name, link, or progress."

    return True, f"Edited **{task_name}**: {', '.join(changes)}."


async def mark_done(channel_id: int, task_name: str, done: bool) -> tuple[bool, str]:
    if not state.is_registered(channel_id):
        return False, "That channel isn't registered as a tracker yet."
    ok = state.set_task_done(channel_id, task_name, done)
    if not ok:
        return False, f"Task **{task_name}** not found."
    status = "done" if done else "not done"
    return True, f"Marked **{task_name}** as {status}."
