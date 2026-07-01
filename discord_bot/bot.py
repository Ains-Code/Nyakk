import discord
from discord import app_commands
from discord.ext import commands

from discord_bot import state, embeds, commands as cmd
import config

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


# ── Autocomplete helpers ─────────────────────────────────────────────────────

async def channel_name_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    all_channels = state.all_registered_channels()
    return [
        app_commands.Choice(name=data["name"], value=data["name"])
        for data in all_channels.values()
        if current.lower() in data["name"].lower()
    ][:25]


async def task_name_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    channel_name = interaction.namespace.channel_name
    if not channel_name:
        return []
    channel_id = state.find_channel_id_by_name(channel_name)
    if not channel_id:
        return []
    tasks = state.get_channel_state(channel_id).get("tasks", {})
    return [
        app_commands.Choice(name=name, value=name)
        for name in tasks
        if current.lower() in name.lower()
    ][:25]


# ── Refresh + log helpers ────────────────────────────────────────────────────

async def refresh_tracker_message(channel_id: int):
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
            pass
    new_msg = await channel.send(embed=embed)
    state.set_tracker_message_id(channel_id, new_msg.id)


async def log_update(text: str):
    if not config.UPDATED_CHANNEL_ID:
        return
    log_channel = bot.get_channel(int(config.UPDATED_CHANNEL_ID))
    if log_channel:
        await log_channel.send(text)


# ── State rebuild on startup ─────────────────────────────────────────────────

async def rebuild_state_from_discord():
    """
    On startup, scan all text channels in the guild and look for the bot's
    own tracker embeds (identified by '— Task Tracker' in the embed title).
    Rebuilds in-memory state from those embeds so a Railway restart doesn't
    lose all registered channels and tasks.
    """
    if not config.DISCORD_GUILD_ID:
        print("[discord] No DISCORD_GUILD_ID set — skipping state rebuild.")
        return

    guild = bot.get_guild(int(config.DISCORD_GUILD_ID))
    if not guild:
        print("[discord] Guild not found — skipping state rebuild.")
        return

    recovered = 0
    for channel in guild.text_channels:
        try:
            # Only look at the last 20 messages — tracker embed is always near top
            async for message in channel.history(limit=20, oldest_first=True):
                if message.author != bot.user:
                    continue
                if not message.embeds:
                    continue
                embed = message.embeds[0]
                if not embed.title or "— Task Tracker" not in embed.title:
                    continue

                # Found a tracker embed — register this channel
                channel_name = channel.name
                state.register_channel(channel.id, channel_name)
                state.set_tracker_message_id(channel.id, message.id)

                # Rebuild tasks from embed description
                tasks = embeds.parse_embed_to_tasks(embed)
                for task_name, info in tasks.items():
                    state.add_task(
                        channel.id,
                        task_name,
                        link=info.get("link"),
                        display=info.get("display"),
                    )
                    if info.get("done"):
                        state.set_task_done(channel.id, task_name, True)

                print(f"[discord] Recovered #{channel_name} with {len(tasks)} task(s).")
                recovered += 1
                break  # one tracker embed per channel

        except discord.Forbidden:
            # Bot doesn't have permission to read this channel — skip
            pass
        except Exception as e:
            print(f"[discord] Error scanning #{channel.name}: {e}")

    print(f"[discord] State rebuild complete — {recovered} channel(s) recovered.")


# ── Events ───────────────────────────────────────────────────────────────────

@bot.event
async def on_ready():
    print(f"[discord] Logged in as {bot.user}")
    await rebuild_state_from_discord()
    await bot.tree.sync()
    print("[discord] Slash commands synced.")


# ── Slash commands ───────────────────────────────────────────────────────────

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
@app_commands.describe(channel_name="Tracker channel", task="Task name", link="Optional link")
@app_commands.autocomplete(channel_name=channel_name_autocomplete)
async def add(interaction: discord.Interaction, channel_name: str, task: str, link: str = None):
    channel_id = state.find_channel_id_by_name(channel_name)
    if channel_id is None:
        await interaction.response.send_message("❌ That tracker channel doesn't exist.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    ok, msg = await cmd.add_task(channel_id, task, link)
    await interaction.followup.send(("✅ " if ok else "❌ ") + msg)
    if ok:
        await refresh_tracker_message(channel_id)
        await log_update(f"➕ **{task}** added to #{channel_name}")


@bot.tree.command(name="update", description="Update an existing task")
@app_commands.describe(channel_name="Tracker channel", task_name="Task to update", link="Optional new link")
@app_commands.autocomplete(channel_name=channel_name_autocomplete, task_name=task_name_autocomplete)
async def update(interaction: discord.Interaction, channel_name: str, task_name: str, link: str = None):
    channel_id = state.find_channel_id_by_name(channel_name)
    if channel_id is None:
        await interaction.response.send_message("❌ That tracker channel doesn't exist.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    ok, msg = await cmd.update_task(channel_id, task_name, link)
    await interaction.followup.send(("✅ " if ok else "❌ ") + msg)
    if ok:
        await refresh_tracker_message(channel_id)
        await log_update(f"✏️ **{task_name}** updated in #{channel_name}")


@bot.tree.command(name="done", description="Mark a task as done")
@app_commands.describe(channel_name="Tracker channel", task_name="Task to mark done")
@app_commands.autocomplete(channel_name=channel_name_autocomplete, task_name=task_name_autocomplete)
async def done(interaction: discord.Interaction, channel_name: str, task_name: str):
    channel_id = state.find_channel_id_by_name(channel_name)
    if channel_id is None:
        await interaction.response.send_message("❌ That tracker channel doesn't exist.", ephemeral=True)
        return
    ok, msg = await cmd.mark_done(channel_id, task_name, True)
    await interaction.response.send_message(("✅ " if ok else "❌ ") + msg)
    if ok:
        await refresh_tracker_message(channel_id)
        await log_update(f"🟢 **{task_name}** marked done in #{channel_name}")


@bot.tree.command(name="undone", description="Mark a task as not done")
@app_commands.describe(channel_name="Tracker channel", task_name="Task to mark not done")
@app_commands.autocomplete(channel_name=channel_name_autocomplete, task_name=task_name_autocomplete)
async def undone(interaction: discord.Interaction, channel_name: str, task_name: str):
    channel_id = state.find_channel_id_by_name(channel_name)
    if channel_id is None:
        await interaction.response.send_message("❌ That tracker channel doesn't exist.", ephemeral=True)
        return
    ok, msg = await cmd.mark_done(channel_id, task_name, False)
    await interaction.response.send_message(("✅ " if ok else "❌ ") + msg)
    if ok:
        await refresh_tracker_message(channel_id)
        await log_update(f"⚪ **{task_name}** marked not done in #{channel_name}")
