# Tracker Bot (Discord + Messenger)

Discord is the main system — every task list lives as a live, edited embed
in a Discord channel. Facebook Messenger is just a remote control: typing
slash-style commands there relays the same actions into Discord.

## How it works

- `/add_channel <name>` (Discord only) creates a new text channel and
  registers it as a tracker. Posts an empty tracker embed.
- `/add <channel> <link> [progress]` adds a task from a link, default **not done**. Duplicate task names are rejected instead of overwritten.
- `/update <channel> <task> [link]` updates a task's link/details.
- `/done <channel> <task>` / `/undone <channel> <task>` toggle completion.
- `/ask <channel> <question>` and `/recommend <channel>` use AI with tracker context.
- Every successful change **edits the same tracker message in place**
  (never spams new messages) and logs a line to the `UPDATED` channel.
- From Messenger, type the same commands as plain text, e.g.:
  `/add reading-manhwa https://example.com/ch12 12`
  The bot replies in Messenger and applies the same change to Discord.

State is kept in memory only — no database. Discord's existing messages
are the source of truth (see `discord_bot/state.py` for caveats around
restarts, since rebuilding from message history isn't fully implemented yet).

## Setup

1. `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and fill in:
   - `DISCORD_TOKEN`, `DISCORD_GUILD_ID`, `UPDATED_CHANNEL_ID`
   - `FB_PAGE_TOKEN`, `FB_VERIFY_TOKEN`
   - `OPENAI_API_KEY` for AI chat/recommendations; optionally `OPENAI_MODEL`
3. In the Discord Developer Portal, enable the bot's `applications.commands`
   scope and invite it to your server with channel-management permissions.
4. In the Facebook App dashboard, set your webhook callback URL to
   `https://<your-host>/webhook` and the verify token to match
   `FB_VERIFY_TOKEN`. Subscribe the page to `messages` events.
5. Run: `python main.py`

## Known gaps to revisit

- State rebuild from existing Discord messages on restart is stubbed —
  currently assumes a fresh boot. Worth finishing if uptime/restarts matter.
- `/add_channel` from Messenger is intentionally blocked (needs a Discord
  guild context to create a channel safely) — must be run from Discord.
- No multi-page/multi-guild mapping yet; assumes one Page → one Discord server.
