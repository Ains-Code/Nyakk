import discord
from discord import app_commands
from discord.ext import commands

from discord_bot import state, embeds, commands as cmd
from ai_chat import chat as ai_chat
import config

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


# ── Autocomplete ──────────────────────────────────────────────────────────[...]

async def channel_name_autocomplete(interaction: discord.Interaction, current: str):
    return [
        app_commands.Choice(name=data["name"], value=data["name"])
        for data in state.all_registered_channels().values()
        if current.lower() in data["name"].lower()
    ][:25]


async def task_name_autocomplete(interaction: discord.Interaction, current: str):
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


# ── Helpers ───────────────────────────────────────────────────────────……[...]

async def refresh_tracker_message(channel_id: int):
    channel = bot.get_channel(channel_id)
    if not channel:
        return
    ch_state = state.get_channel_state(channel_id)
    if not ch_state:
        return
    label = state.get_progress_label(channel_id)
    embed = embeds.build_tracker_embed(ch_state["name"], ch_state["tasks"], label)
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


# ── State rebuild ─────────────────────────────────────────────────────────……[...]

async def rebuild_state_from_discord():
    if not config.DISCORD_GUILD_ID:
        return
    guild = bot.get_guild(int(config.DISCORD_GUILD_ID))
    if not guild:
        return
    recovered = 0
    for channel in guild.text_channels:
        try:
            async for message in channel.history(limit=20, oldest_first=True):
                if message.author != bot.user or not message.embeds:
                    continue
                embed = message.embeds[0]
                if not embed.title or "— Task Tracker" not in embed.title:
                    continue
                state.register_channel(channel.id, channel.name)
                state.set_tracker_message_id(channel.id, message.id)
                tasks = embeds.parse_embed_to_tasks(embed)
                for task_name, info in tasks.items():
                    state.add_task(channel.id, task_name,
                                   link=info.get("link"), display=info.get("display"))
                    if info.get("done"):
                        state.set_task_done(channel.id, task_name, True)
                    if info.get("progress", 0) > 0:
                        state.edit_task_progress(channel.id, task_name, info["progress"])
                print(f"[discord] Recovered #{channel.name} with {len(tasks)} task(s).")
                recovered += 1
                break
        except discord.Forbidden:
            pass
        except Exception as e:
            print(f"[discord] Error scanning #{channel.name}: {e}")
    print(f"[discord] State rebuild complete — {recovered} channel(s) recovered.")


# ── Events ───────────────────────────────────────────────────────────……[...]

@bot.event
async def on_ready():
    print(f"[discord] Logged in as {bot.user}")
    await rebuild_state_from_discord()
    try:
        synced = await bot.tree.sync()
        print(f"[discord] Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"[discord] Failed to sync commands: {e}")
    print("[discord] Slash commands synced.")


# ── Slash commands ─────────────────────────────────────────────────────────[...]

@bot.tree.command(name="add_channel", description="Create and register a new tracker channel")
@app_commands.describe(task_category_name="Name for the new tracker channel")
async def add_channel(interaction: discord.Interaction, task_category_name: str):
    new_channel = await interaction.guild.create_text_channel(task_category_name)
    state.register_channel(new_channel.id, task_category_name)
    label = state.get_progress_label(new_channel.id)
    embed = embeds.build_tracker_embed(task_category_name, {}, label)
    msg = await new_channel.send(embed=embed)
    state.set_tracker_message_id(new_channel.id, msg.id)
    await interaction.response.send_message(f"✅ Created {new_channel.mention} as a tracker channel.")
    await log_update(f"📁 New tracker channel: **{task_category_name}**")


@bot.tree.command(name="add", description="Add a new task with link and chapter/episode number")
@app_commands.describe(channel_name="Tracker channel", link="Link to page/chapter/episode", progress="Chapter, episode, or amount number (optional)")
@app_commands.autocomplete(channel_name=channel_name_autocomplete)
async def add(interaction: discord.Interaction, channel_name: str, link: str, progress: int = 0):
    channel_id = state.find_channel_id_by_name(channel_name)
    if not channel_id:
        await interaction.response.send_message("❌ Channel not found.", ephemeral=True)
        return
    await interaction.response.defer()
    ok, msg = await cmd.add_task(channel_id, link, progress)
    await interaction.followup.send(("✅ " if ok else "❌ ") + msg)
    if ok:
        await refresh_tracker_message(channel_id)
        await log_update(f"➕ Added to #{channel_name}")


@bot.tree.command(name="remove", description="Remove a task from a tracker channel")
@app_commands.describe(channel_name="Tracker channel", task_name="Task to remove")
@app_commands.autocomplete(channel_name=channel_name_autocomplete, task_name=task_name_autocomplete)
async def remove(interaction: discord.Interaction, channel_name: str, task_name: str):
    channel_id = state.find_channel_id_by_name(channel_name)
    if not channel_id:
        await interaction.response.send_message("❌ Channel not found.", ephemeral=True)
        return
    ok, msg = await cmd.remove_task(channel_id, task_name)
    await interaction.response.send_message(("✅ " if ok else "❌ ") + msg)
    if ok:
        await refresh_tracker_message(channel_id)
        await log_update(f"🗑️ {msg} in #{channel_name}")


@bot.tree.command(name="edit", description="Edit a task's name, link, or chapter/episode progress")
@app_commands.describe(
    channel_name="Tracker channel",
    task_name="Task to edit",
    new_name="New task name (optional)",
    new_link="New link (optional)",
    progress="Chapter or episode number (optional)",
)
@app_commands.autocomplete(channel_name=channel_name_autocomplete, task_name=task_name_autocomplete)
async def edit(interaction: discord.Interaction, channel_name: str, task_name: str,
               new_name: str = None, new_link: str = None, progress: int = None):
    channel_id = state.find_channel_id_by_name(channel_name)
    if not channel_id:
        await interaction.response.send_message("❌ Channel not found.", ephemeral=True)
        return
    await interaction.response.defer()
    ok, msg = await cmd.edit_task(channel_id, task_name, new_name, new_link, progress)
    await interaction.followup.send(("✅ " if ok else "❌ ") + msg)
    if ok:
        await refresh_tracker_message(channel_id)
        await log_update(f"✏️ {msg} in #{channel_name}")


@bot.tree.command(name="update", description="Update an existing task's link")
@app_commands.describe(channel_name="Tracker channel", task_name="Task to update", link="New link")
@app_commands.autocomplete(channel_name=channel_name_autocomplete, task_name=task_name_autocomplete)
async def update(interaction: discord.Interaction, channel_name: str, task_name: str, link: str = None):
    channel_id = state.find_channel_id_by_name(channel_name)
    if not channel_id:
        await interaction.response.send_message("❌ Channel not found.", ephemeral=True)
        return
    await interaction.response.defer()
    ok, msg = await cmd.update_task(channel_id, task_name, link)
    await interaction.followup.send(("✅ " if ok else "❌ ") + msg)
    if ok:
        await refresh_tracker_message(channel_id)
        await log_update(f"🔗 **{task_name}** link updated in #{channel_name}")


@bot.tree.command(name="done", description="Mark a task as done")
@app_commands.describe(channel_name="Tracker channel", task_name="Task to mark done")
@app_commands.autocomplete(channel_name=channel_name_autocomplete, task_name=task_name_autocomplete)
async def done(interaction: discord.Interaction, channel_name: str, task_name: str):
    channel_id = state.find_channel_id_by_name(channel_name)
    if not channel_id:
        await interaction.response.send_message("❌ Channel not found.", ephemeral=True)
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
    if not channel_id:
        await interaction.response.send_message("❌ Channel not found.", ephemeral=True)
        return
    ok, msg = await cmd.mark_done(channel_id, task_name, False)
    await interaction.response.send_message(("✅ " if ok else "❌ ") + msg)
    if ok:
        await refresh_tracker_message(channel_id)
        await log_update(f"⚪ **{task_name}** marked not done in #{channel_name}")


@bot.tree.command(name="ask", description="Ask the AI assistant about anime, manga, or this tracker")
@app_commands.describe(channel_name="Tracker channel to use for context", question="What you want to ask")
@app_commands.autocomplete(channel_name=channel_name_autocomplete)
async def ask(interaction: discord.Interaction, channel_name: str, question: str):
    channel_id = state.find_channel_id_by_name(channel_name)
    if not channel_id:
        await interaction.response.send_message("❌ Channel not found.", ephemeral=True)
        return
    await interaction.response.defer()
    reply = await ai_chat.chat(interaction.user.id, channel_id, question)
    await interaction.followup.send(reply)


@bot.tree.command(name="recommend", description="Get AI anime/manga recommendations from a tracker")
@app_commands.describe(channel_name="Tracker channel to use for recommendations")
@app_commands.autocomplete(channel_name=channel_name_autocomplete)
async def recommend(interaction: discord.Interaction, channel_name: str):
    channel_id = state.find_channel_id_by_name(channel_name)
    if not channel_id:
        await interaction.response.send_message("❌ Channel not found.", ephemeral=True)
        return
    await interaction.response.defer()
    reply = await ai_chat.get_recommendations(channel_id)
    await interaction.followup.send(reply)


@bot.tree.command(name="clear_ai", description="Clear your AI conversation history")
async def clear_ai(interaction: discord.Interaction):
    ai_chat.clear_conversation(interaction.user.id)
    await interaction.response.send_message("✅ Cleared your AI conversation history.", ephemeral=True)
