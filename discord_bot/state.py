"""
In-memory state for the tracker bot.

Task structure:
{
    "task_name": {
        "done": False,
        "link": "https://..." or None,
        "display": "Page Title" or None,
        "progress": 0,          # chapter/episode number
        "progress_label": "Chapter" | "Episode" | "Progress"
    }
}
"""

from typing import Optional

_state: dict[int, dict] = {}


def _detect_progress_label(channel_name: str) -> str:
    name = channel_name.lower()
    if any(k in name for k in ("manga", "manhwa", "manhua", "comic", "reading")):
        return "Chapter"
    if any(k in name for k in ("kdrama", "drama", "anime", "watching", "series", "show")):
        return "Episode"
    return "Progress"


def register_channel(channel_id: int, name: str) -> None:
    if channel_id not in _state:
        _state[channel_id] = {
            "name": name,
            "tracker_message_id": None,
            "progress_label": _detect_progress_label(name),
            "tasks": {},
        }


def is_registered(channel_id: int) -> bool:
    return channel_id in _state


def set_tracker_message_id(channel_id: int, message_id: int) -> None:
    if channel_id in _state:
        _state[channel_id]["tracker_message_id"] = message_id


def get_tracker_message_id(channel_id: int) -> Optional[int]:
    return _state.get(channel_id, {}).get("tracker_message_id")


def get_progress_label(channel_id: int) -> str:
    return _state.get(channel_id, {}).get("progress_label", "Progress")


def task_exists(channel_id: int, task_name: str) -> bool:
    tasks = _state.get(channel_id, {}).get("tasks", {})
    return task_name in tasks


def add_task(channel_id: int, task_name: str,
             link: Optional[str] = None, display: Optional[str] = None, progress: int = 0) -> bool:
    if task_exists(channel_id, task_name):
        return False
    _state[channel_id]["tasks"][task_name] = {
        "done": False,
        "link": link,
        "display": display,
        "progress": progress,
    }
    return True


def remove_task(channel_id: int, task_name: str) -> bool:
    tasks = _state.get(channel_id, {}).get("tasks", {})
    if task_name not in tasks:
        return False
    del tasks[task_name]
    return True


def update_task(channel_id: int, task_name: str,
                link: Optional[str] = None, display: Optional[str] = None) -> bool:
    tasks = _state.get(channel_id, {}).get("tasks", {})
    if task_name not in tasks:
        return False
    if link is not None:
        tasks[task_name]["link"] = link
        tasks[task_name]["display"] = display
    return True


def edit_task_name(channel_id: int, old_name: str, new_name: str) -> bool:
    tasks = _state.get(channel_id, {}).get("tasks", {})
    if old_name not in tasks or (new_name != old_name and new_name in tasks):
        return False
    tasks[new_name] = tasks.pop(old_name)
    return True


def edit_task_link(channel_id: int, task_name: str,
                   link: str, display: Optional[str] = None) -> bool:
    tasks = _state.get(channel_id, {}).get("tasks", {})
    if task_name not in tasks:
        return False
    tasks[task_name]["link"] = link
    tasks[task_name]["display"] = display
    return True


def edit_task_progress(channel_id: int, task_name: str, progress: int) -> bool:
    tasks = _state.get(channel_id, {}).get("tasks", {})
    if task_name not in tasks:
        return False
    tasks[task_name]["progress"] = progress
    return True


def set_task_done(channel_id: int, task_name: str, done: bool) -> bool:
    tasks = _state.get(channel_id, {}).get("tasks", {})
    if task_name not in tasks:
        return False
    tasks[task_name]["done"] = done
    return True


def get_channel_state(channel_id: int) -> Optional[dict]:
    return _state.get(channel_id)


def find_channel_id_by_name(name: str) -> Optional[int]:
    for cid, data in _state.items():
        if data["name"] == name:
            return cid
    return None


def all_registered_channels() -> dict[int, dict]:
    return _state
