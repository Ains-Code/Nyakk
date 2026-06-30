import asyncio

import config
from discord_bot.bot import bot
from messenger.webhook import app as webhook_app


async def main():
    discord_task = asyncio.create_task(bot.start(config.DISCORD_TOKEN))

    webhook_task = asyncio.create_task(
        webhook_app.run_task(host=config.WEBHOOK_HOST, port=config.WEBHOOK_PORT)
    )

    await asyncio.gather(discord_task, webhook_task)


if __name__ == "__main__":
    asyncio.run(main())
