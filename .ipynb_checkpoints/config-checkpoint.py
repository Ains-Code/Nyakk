import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_GUILD_ID = os.getenv("DISCORD_GUILD_ID")  # server where channels get created
UPDATED_CHANNEL_ID = os.getenv("UPDATED_CHANNEL_ID")  # the audit-log channel ("UPDATED")

FB_PAGE_TOKEN = os.getenv("FB_PAGE_TOKEN")
FB_VERIFY_TOKEN = os.getenv("FB_VERIFY_TOKEN")

WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "0.0.0.0")
# Railway (and most PaaS hosts) inject PORT automatically -- fall back to
# WEBHOOK_PORT/8000 for local runs.
WEBHOOK_PORT = int(os.getenv("PORT", os.getenv("WEBHOOK_PORT", "8000")))

missing = [
    name for name, val in [
        ("DISCORD_TOKEN", DISCORD_TOKEN),
        ("DISCORD_GUILD_ID", DISCORD_GUILD_ID),
        ("FB_PAGE_TOKEN", FB_PAGE_TOKEN),
        ("FB_VERIFY_TOKEN", FB_VERIFY_TOKEN),
    ] if not val
]
if missing:
    print(f"[config] Warning: missing env vars: {', '.join(missing)}")
