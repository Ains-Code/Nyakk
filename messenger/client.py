import aiohttp
import config

GRAPH_URL = "https://graph.facebook.com/v19.0/me/messages"


async def send_message(recipient_id: str, text: str) -> None:
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text},
    }
    params = {"access_token": config.FB_PAGE_TOKEN}

    async with aiohttp.ClientSession() as session:
        async with session.post(GRAPH_URL, params=params, json=payload) as resp:
            if resp.status != 200:
                body = await resp.text()
                print(f"[messenger] Failed to send message: {resp.status} {body}")
