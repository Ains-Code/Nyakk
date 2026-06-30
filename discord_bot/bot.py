import discord
from discord import app_commands
from discord.ext import commands

from discord_bot import state, embeds, commands as cmd
import config

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


async def refresh_tracker_message(channel_id: int):
    """Edits the existing tracker embed in place, or posts a new one if
    none exists yet for this channel."""
    channel = bot.get_channel(channel_id)
    if channel is None:
        return

    ch_state = state.get_channel_state(channel_id)
    if ch_state is None:
        return

    embed = embeds.build_tracker_embed(ch_state["name"], ch_state["tasks"])
    msg_id = state.get_tracker_message_id(channel_id)

    if msg_id:
        try:
            msg = await channel.fetch_message(msg_id)
            await msg.edit(embed=embed)
            return
        except discord.NotFound:
            pass  # message got deleted somehow, fall through to repost

    new_msg = await channel.send(embed=embed)
    state.set_tracker_message_id(channel_id, new_msg.id)


async def log_update(text: str):
    if not config.UPDATED_CHANNEL_ID:
        return
    log_channel = bot.get_channel(int(config.UPDATED_CHANNEL_ID))
    if log_channel:
        await log_channel.send(text)


@bot.event
async def on_ready():
    print(f"[discord] Logged in as {bot.user}")
    await rebuild_state_from_discord()
    await bot.tree.sync()
    print("[discord] Slash commands synced.")


async def rebuild_state_from_discord():
    """On startup, re-derive all task state from existing tracker messages
    in already-registered channels, since nothing is persisted to disk.
    NOTE: this requires the bot to already know which channels are
    trackers. For a first run with zero history, channels are registered
    the moment /add channel is used, so there's nothing to rebuild yet."""
    print("[discord] State rebuild: nothing to recover on a fresh boot "
          "(channel registry is in-memory and starts empty).")


# ---------- Slash commands ----------

@bot.tree.command(name="add_channel", description="Create and register a new tracker channel")
@app_commands.describe(task_category_name="Name for the new tracker channel")
async def add_channel(interaction: discord.Interaction, task_category_name: str):
    guild = interaction.guild
    new_channel = await guild.create_text_channel(task_category_name)
    state.register_channel(new_channel.id, task_category_name)

    embed = embeds.build_tracker_embed(task_category_name, {})
    msg = await new_channel.send(embed=embed)
    state.set_tracker_message_id(new_channel.id, msg.id)

    await interaction.response.send_message(
        f"✅ Created and registered {new_channel.mention} as a tracker channel."
    )
    await log_update(f"📁 New tracker channel created: **{task_category_name}**")


@bot.tree.command(name="add", description="Add a new task to a tracker channel")
@app_commands.describe(channel_name="Tracker channel name", task="Task name", link="Optional link")
async def add(interaction: discord.Interaction, channel_name: str, task: str, link: str = None):
    channel_id = state.find_channel_id_by_name(channel_name)
    if channel_id is None:
        await interaction.response.send_message("❌ That tracker channel doesn't exist.", ephemeral=True)
        return

    ok, msg = cmd.add_task(channel_id, task, link)
    await interaction.response.send_message(("✅ " if ok else "❌ ") + msg, ephemeral=not ok)
    if ok:
        await refresh_tracker_message(channel_id)
        await log_update(f"➕ **{task}** added to #{channel_name}")


@bot.tree.command(name="update", description="Update an existing task")
@app_commands.describe(channel_name="Tracker channel name", task_name="Task to update", link="Optional new link")
async def update(interaction: discord.Interaction, channel_name: str, task_name: str, link: str = None):
    channel_id = state.find_channel_id_by_name(channel_name)
    if channel_id is None:
        await interaction.response.send_message("❌ That tracker channel doesn't exist.", ephemeral=True)
        return

    ok, msg = cmd.update_task(channel_id, task_name, link)
    await interaction.response.send_message(("✅ " if ok else "❌ ") + msg, ephemeral=not ok)
    if ok:
        await refresh_tracker_message(channel_id)
        await log_update(f"✏️ **{task_name}** updated in #{channel_name}")


@bot.tree.command(name="done", description="Mark a task as done")
@app_commands.describe(channel_name="Tracker channel name", task_name="Task to mark done")
async def done(interaction: discord.Interaction, channel_name: str, task_name: str):
    channel_id = state.find_channel_id_by_name(channel_name)
    if channel_id is None:
        await interaction.response.send_message("❌ That tracker channel doesn't exist.", ephemeral=True)
        return

    ok, msg = cmd.mark_done(channel_id, task_name, True)
    await interaction.response.send_message(("✅ " if ok else "❌ ") + msg, ephemeral=not ok)
    if ok:
        await refresh_tracker_message(channel_id)
        await log_update(f"🟢 **{task_name}** marked done in #{channel_name}")


@bot.tree.command(name="undone", description="Mark a task as not done")
@app_commands.describe(channel_name="Tracker channel name", task_name="Task to mark not done")
async def undone(interaction: discord.Interaction, channel_name: str, task_name: str):
    channel_id = state.find_channel_id_by_name(channel_name)
    if channel_id is None:
        await interaction.response.send_message("❌ That tracker channel doesn't exist.", ephemeral=True)
        return

    ok, msg = cmd.mark_done(channel_id, task_name, False)
    await interaction.response.send_message(("✅ " if ok else "❌ ") + msg, ephemeral=not ok)
    if ok:
        await refresh_tracker_message(channel_id)
        await log_update(f"⚪ **{task_name}** marked not done in #{channel_name}")
