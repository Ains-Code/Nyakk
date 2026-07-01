"""
AI-powered conversational chat with anime/manga recommendations.
Integrates with tracker to provide personalized suggestions.
"""

from openai import AsyncOpenAI, OpenAIError

import config
from discord_bot import state

client = AsyncOpenAI(api_key=config.OPENAI_API_KEY) if config.OPENAI_API_KEY else None
MODEL = getattr(config, "OPENAI_MODEL", None) or "gpt-4o-mini"

# Store conversation history per user
_conversations: dict[int, list[dict[str, str]]] = {}

SYSTEM_PROMPT = """
You are a helpful anime/manga tracker bot assistant. You:
- Help users track their anime/manga watching and reading progress
- Provide personalized recommendations based on their tracker
- Discuss anime/manga plots, characters, and recommendations
- Keep responses concise (under 2000 chars for Discord)
- Are friendly and enthusiastic about anime/manga
- Remember context from previous messages

When making recommendations, suggest titles that match the user's interests based on what they're tracking.
"""


def _get_tracker_summary(channel_id: int) -> str:
    """Get a summary of tasks in the channel for context."""
    ch_state = state.get_channel_state(channel_id)
    if not ch_state or not ch_state.get("tasks"):
        return "(No tasks tracked yet)"

    tasks = ch_state["tasks"]
    summary = f"Current tracker for #{ch_state['name']}:\n"
    for task_name, info in list(tasks.items())[:10]:
        status = "✓" if info["done"] else "○"
        progress = f" (Ch/Ep {info['progress']})" if info.get("progress") else ""
        summary += f"{status} {task_name}{progress}\n"
    if len(tasks) > 10:
        summary += f"... and {len(tasks) - 10} more"
    return summary


def _missing_ai_message() -> str:
    return "❌ AI chat is not configured yet. Set `OPENAI_API_KEY` and restart the bot."


def _trim_for_discord(text: str) -> str:
    if len(text) <= 1900:
        return text
    return text[:1897].rstrip() + "..."


async def chat(user_id: int, channel_id: int, message: str) -> str:
    """Send a message and get AI response with tracker context."""
    if client is None:
        return _missing_ai_message()

    conversation = _conversations.setdefault(user_id, [])

    # Add user message and persist the trimmed history back into the dictionary.
    conversation.append({"role": "user", "content": message})
    conversation = conversation[-10:]
    _conversations[user_id] = conversation

    tracker_context = _get_tracker_summary(channel_id)

    try:
        response = await client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT + f"\n\nUser's tracker: {tracker_context}"},
                *conversation,
            ],
            max_tokens=500,
            temperature=0.7,
        )

        assistant_response = response.choices[0].message.content or "I couldn't generate a response."
        assistant_response = _trim_for_discord(assistant_response)

        conversation.append({"role": "assistant", "content": assistant_response})
        _conversations[user_id] = conversation[-10:]

        return assistant_response

    except OpenAIError as e:
        print(f"[ai_chat] OpenAI error: {e}")
        return "❌ Sorry, the AI service had trouble processing that. Please try again."
    except Exception as e:
        print(f"[ai_chat] Error: {e}")
        return "❌ Sorry, I had trouble processing that. Please try again."


async def get_recommendations(channel_id: int) -> str:
    """Get anime/manga recommendations based on tracker."""
    if client is None:
        return _missing_ai_message()

    ch_state = state.get_channel_state(channel_id)
    if not ch_state or not ch_state.get("tasks"):
        return "No tasks tracked yet. Start tracking something and I can make recommendations!"

    tasks = ch_state["tasks"]
    task_list = "\n".join([f"- {name}" for name in list(tasks.keys())[:10]])

    prompt = f"""Based on these anime/manga titles the user is watching/reading:
{task_list}

Suggest 3-5 similar titles they might enjoy. Be brief and explain why."""

    try:
        response = await client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=300,
            temperature=0.7,
        )
        return _trim_for_discord(response.choices[0].message.content or "I couldn't generate recommendations.")
    except OpenAIError as e:
        print(f"[ai_chat] Recommendation OpenAI error: {e}")
        return "❌ Couldn't generate recommendations right now."
    except Exception as e:
        print(f"[ai_chat] Recommendation error: {e}")
        return "❌ Couldn't generate recommendations right now."


def clear_conversation(user_id: int):
    """Clear conversation history for a user."""
    if user_id in _conversations:
        del _conversations[user_id]


def get_conversation_length(user_id: int) -> int:
    """Get current conversation length."""
    return len(_conversations.get(user_id, []))
