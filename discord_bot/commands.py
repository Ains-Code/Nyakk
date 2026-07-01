"""
Core command logic. Both Discord slash commands and WhatsApp text commands
call into these functions.
"""

from typing import Optional

from discord_bot import state
from shared.link_title import clean_page_title, extract_progress, fetch_title


def _fallback_title(link: str | None) -> str | None:
    return clean_page_title(link, link) if link else None


async def _title_and_progress(link: str | None, progress: int = 0) -> tuple[str | None, int]:
    if not link:
        return None, progress

    title = await fetch_title(link)
    if not title:
        title = _fallback_title(link) or link

    if progress <= 0:
        progress = extract_progress(title, link)

    return title, progress


async def add_task(channel_id: int, link: str, progress: int = 0) -> tuple[bool, str]:
    if not state.is_registered(channel_id):
        return False, "That channel isn't registered as a tracker yet."

    title, progress = await _title_and_progress(link, progress)
    task_name = title or link
    if not state.add_task(channel_id, task_name, link=link, display=title, progress=progress):
        return False, f"Task **{task_name}** already exists. Use `/update` or `/edit` instead."
    label = state.get_progress_label(channel_id)
    progress_info = f" ({label} {progress})" if progress > 0 else ""
    return True, f"Added **{task_name}**{progress_info}."


async def update_task(channel_id: int, task_name: str, link: Optional[str] = None,
                      progress: Optional[int] = None) -> tuple[bool, str]:
    if not state.is_registered(channel_id):
        return False, "That channel isn't registered as a tracker yet."

    title = None
    detected_progress = progress or 0
    if link:
        title, detected_progress = await _title_and_progress(link, detected_progress)

    matched_task = state.find_task_name(channel_id, task_name)
    if matched_task is None and title:
        matched_task = state.find_task_name(channel_id, title)

    if matched_task is None:
        return False, f"Task **{task_name}** not found."

    changes = []
    if link is not None:
        state.update_task(channel_id, matched_task, link=link, display=title)
        changes.append(f"link/title → **{title or link}**")

    if detected_progress > 0:
        state.edit_task_progress(channel_id, matched_task, detected_progress)
        label = state.get_progress_label(channel_id)
        changes.append(f"{label} → **{detected_progress}**")

    if not changes:
        return False, "Nothing to update — provide a link or progress."

    return True, f"Updated **{matched_task}**: {', '.join(changes)}."


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
            if state.task_exists(channel_id, new_name):
                return False, f"Task **{new_name}** already exists. Choose a different name."
            return False, f"Task **{task_name}** not found."
        changes.append(f"name → **{new_name}**")
        task_name = new_name  # use new name for subsequent edits

    if new_link:
        title, detected_progress = await _title_and_progress(new_link, new_progress or 0)
        ok = state.edit_task_link(channel_id, task_name, new_link, title)
        if not ok:
            return False, f"Task **{task_name}** not found."
        changes.append(f"link/title → **{title or new_link}**")
        if new_progress is None and detected_progress > 0:
            new_progress = detected_progress

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
