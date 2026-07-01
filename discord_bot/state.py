"""
In-memory state for the tracker bot.

Structure:
{
    channel_id (int): {
        "name": "reading-manhwa",
        "tracker_message_id": 123456789 or None,
        "tasks": {
            "task_name": {
                "done": False,
                "link": "https://..." or None,
                "display": "One Piece Chapter 1100" or None,
            },
        }
    },
}
"""

from typing import Optional

_state: dict[int, dict] = {}


def register_channel(channel_id: int, name: str) -> None:
    if channel_id not in _state:
        _state[channel_id] = {
            "name": name,
            "tracker_message_id": None,
            "tasks": {},
        }


def is_registered(channel_id: int) -> bool:
    return channel_id in _state


def set_tracker_message_id(channel_id: int, message_id: int) -> None:
    if channel_id in _state:
        _state[channel_id]["tracker_message_id"] = message_id


def get_tracker_message_id(channel_id: int) -> Optional[int]:
    return _state.get(channel_id, {}).get("tracker_message_id")


def add_task(channel_id: int, task_name: str,
             link: Optional[str] = None, display: Optional[str] = None) -> None:
    _state[channel_id]["tasks"][task_name] = {
        "done": False,
        "link": link,
        "display": display,  # fetched page title, shown instead of raw URL
    }


def update_task(channel_id: int, task_name: str,
                link: Optional[str] = None, display: Optional[str] = None) -> bool:
    tasks = _state.get(channel_id, {}).get("tasks", {})
    if task_name not in tasks:
        return False
    if link is not None:
        tasks[task_name]["link"] = link
        tasks[task_name]["display"] = display
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
