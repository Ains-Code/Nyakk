"""
Quart webhook for receiving WhatsApp messages via Meta Cloud API.

Security layers applied on every request:
  - Meta HMAC-SHA256 signature verification
  - Replay/stale message detection (timestamp check)
  - Per-sender rate limiting
  - Sender whitelist (optional)
  - Input sanitization + suspicious pattern detection
"""
from quart import Quart, request, abort

import config
from shared.command_parser import parse
from shared.security import (
    verify_meta_signature,
    is_message_too_old,
    is_safe_input,
)
from messenger.client import send_message
from discord_bot import state, commands as cmd
from ai_chat import chat as ai_chat
from discord_bot.bot import refresh_tracker_message, log_update

app = Quart(__name__)


@app.route("/webhook", methods=["GET"])
async def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == config.VERIFY_TOKEN:
        return challenge, 200
    return "Verification failed", 403


@app.route("/webhook", methods=["POST"])
async def receive():
    # ── Layer 1: Meta signature verification ──────────────────────────────
    raw_body = await request.get_data()
    signature = request.headers.get("X-Hub-Signature-256")
    if not verify_meta_signature(raw_body, signature):
        abort(401)  # Unauthorized — not from Meta

    # ── Parse JSON ────────────────────────────────────────────────────────
    body = await request.get_json(force=True, silent=True)
    if not body or body.get("object") != "whatsapp_business_account":
        return "Not a WhatsApp event", 404

    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for message in value.get("messages", []):
                if message.get("type") != "text":
                    continue

                sender = message.get("from", "")
                text = message.get("text", {}).get("body", "")
                timestamp = message.get("timestamp")

                # ── Layer 2: Replay / stale message protection ────────────
                if is_message_too_old(timestamp):
                    continue  # silently drop old messages

                # ── Layers 3–6: Rate limit, whitelist, sanitize, patterns ─
                safe, clean_text = is_safe_input(sender, text)
                if not safe:
                    continue  # silently drop — never reveal reason to sender

                await handle_text_command(sender, clean_text)

    return "EVENT_RECEIVED", 200


async def handle_text_command(sender: str, text: str):
    parsed = parse(text)
    if parsed is None:
        await send_message(
            sender,
            "Hindi ko naintindihan yan. Subukan mo:\n"
            "/add_channel <name>\n"
            "/add <channel> <link> [progress]\n"
            "/update <channel> <task> [link]\n"
            "/done <channel> <task>\n"
            "/undone <channel> <task>\n"
            "/recommend <channel>\n"
            "/ask <channel> <question>",
        )
        return

    channel_id = state.find_channel_id_by_name(parsed.channel_name)

    if parsed.command == "add_channel":
        await send_message(
            sender,
            "Ang /add_channel ay kailangan gawin sa loob ng Discord mismo.",
        )
        return

    if channel_id is None:
        await send_message(sender, f"Walang tracker channel na '{parsed.channel_name}'.")
        return

    if parsed.command == "add":
        ok, reply = await cmd.add_task(channel_id, parsed.link, parsed.progress)
    elif parsed.command == "update":
        ok, reply = await cmd.update_task(channel_id, parsed.task_name, parsed.link)
    elif parsed.command == "done":
        ok, reply = await cmd.mark_done(channel_id, parsed.task_name, True)
    elif parsed.command == "undone":
        ok, reply = await cmd.mark_done(channel_id, parsed.task_name, False)
    elif parsed.command == "recommend":
        ok, reply = True, await ai_chat.get_recommendations(channel_id)
    elif parsed.command == "ask":
        ok, reply = True, await ai_chat.chat(int(sender) if sender.isdigit() else hash(sender), channel_id, parsed.message or "")
    else:
        ok, reply = False, "Unknown command."

    await send_message(sender, ("✅ " if ok else "❌ ") + reply)

    if ok:
        if parsed.command not in ("ask", "recommend"):
            await refresh_tracker_message(channel_id)
            await log_update(f"📩 (via WhatsApp) {reply}")
