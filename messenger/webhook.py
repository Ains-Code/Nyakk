from quart import Quart, request

import config
from shared.command_parser import parse
from messenger.client import send_message
from discord_bot import state, commands as cmd
from discord_bot.bot import refresh_tracker_message, log_update

app = Quart(__name__)


@app.route("/webhook", methods=["GET"])
async def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == config.FB_VERIFY_TOKEN:
        return challenge, 200
    return "Verification failed", 403


@app.route("/webhook", methods=["POST"])
async def receive():
    body = await request.get_json()

    if body.get("object") != "page":
        return "Not a page event", 404

    for entry in body.get("entry", []):
        for event in entry.get("messaging", []):
            sender_id = event["sender"]["id"]
            message = event.get("message", {})
            text = message.get("text")
            if not text:
                continue
            await handle_text_command(sender_id, text)

    return "EVENT_RECEIVED", 200


async def handle_text_command(sender_id: str, text: str):
    parsed = parse(text)
    if parsed is None:
        await send_message(
            sender_id,
            "Sorry, I didn't understand that. Try:\n"
            "/add_channel <name>\n"
            "/add <channel> <task> [link]\n"
            "/update <channel> <task> [link]\n"
            "/done <channel> <task>\n"
            "/undone <channel> <task>",
        )
        return

    channel_id = state.find_channel_id_by_name(parsed.channel_name)

    # add_channel can't be created from Messenger (no guild context to
    # create a Discord channel in safely) -- ask the user to do it in Discord.
    if parsed.command == "add_channel":
        await send_message(
            sender_id,
            "Creating new tracker channels must be done from inside Discord "
            "using /add_channel there, so it's created in the right server.",
        )
        return

    if channel_id is None:
        await send_message(sender_id, f"No tracker channel named '{parsed.channel_name}' found.")
        return

    if parsed.command == "add":
        ok, reply = cmd.add_task(channel_id, parsed.task_name, parsed.link)
    elif parsed.command == "update":
        ok, reply = cmd.update_task(channel_id, parsed.task_name, parsed.link)
    elif parsed.command == "done":
        ok, reply = cmd.mark_done(channel_id, parsed.task_name, True)
    elif parsed.command == "undone":
        ok, reply = cmd.mark_done(channel_id, parsed.task_name, False)
    else:
        ok, reply = False, "Unknown command."

    await send_message(sender_id, ("✅ " if ok else "❌ ") + reply)

    if ok:
        await refresh_tracker_message(channel_id)
        await log_update(f"📩 (via Messenger) {reply}")
