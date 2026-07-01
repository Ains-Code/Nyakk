import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_GUILD_ID = os.getenv("DISCORD_GUILD_ID")
UPDATED_CHANNEL_ID = os.getenv("UPDATED_CHANNEL_ID")

# WhatsApp Business API (Meta Cloud API)
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")           # System user / temp access token
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")  # Phone number ID (not the number itself)
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")               # Any string you choose, same as what you set in Meta webhook settings

WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "0.0.0.0")
WEBHOOK_PORT = int(os.getenv("PORT", os.getenv("WEBHOOK_PORT", "8000")))

missing = [
    name for name, val in [
        ("DISCORD_TOKEN", DISCORD_TOKEN),
        ("DISCORD_GUILD_ID", DISCORD_GUILD_ID),
        ("WHATSAPP_TOKEN", WHATSAPP_TOKEN),
        ("WHATSAPP_PHONE_NUMBER_ID", WHATSAPP_PHONE_NUMBER_ID),
        ("VERIFY_TOKEN", VERIFY_TOKEN),
    ] if not val
]
if missing:
    print(f"[config] Warning: missing env vars: {', '.join(missing)}")
