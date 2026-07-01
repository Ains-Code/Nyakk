"""
AI-powered conversational chat with anime/manga recommendations.
Integrates with tracker to provide personalized suggestions.
"""

from typing import Optional
from openai import AsyncOpenAI
from discord_bot import state

client = AsyncOpenAI()

# Store conversation history per user
_conversations: dict[int, list[dict]] = {}

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
    for task_name, info in list(tasks.items())[:5]:  # Show first 5
        status = "✓" if info["done"] else "○"
        progress = f" (Ch {info['progress']})" if info.get("progress") else ""
        summary += f"{status} {task_name}{progress}\n"
    if len(tasks) > 5:
        summary += f"... and {len(tasks) - 5} more"
    return summary


async def chat(user_id: int, channel_id: int, message: str) -> str:
    """Send a message and get AI response with context."""
    if user_id not in _conversations:
        _conversations[user_id] = []
    
    conversation = _conversations[user_id]
    
    # Get tracker context
    tracker_context = _get_tracker_summary(channel_id)
    
    # Add user message
    conversation.append({
        "role": "user",
        "content": message
    })
    
    # Keep last 10 messages for context (prevent token overflow)
    if len(conversation) > 10:
        conversation = conversation[-10:]
    
    try:
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT + f"\n\nUser's tracker: {tracker_context}"},
                *conversation
            ],
            max_tokens=500,
            temperature=0.7,
        )
        
        assistant_response = response.choices[0].message.content
        
        # Store assistant response
        conversation.append({
            "role": "assistant",
            "content": assistant_response
        })
        
        return assistant_response
    
    except Exception as e:
        print(f"[ai_chat] Error: {e}")
        return "❌ Sorry, I had trouble processing that. Please try again."


async def get_recommendations(channel_id: int) -> str:
    """Get anime/manga recommendations based on tracker."""
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
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.7,
        )
        return response.choices[0].message.content
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
