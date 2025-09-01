import discord
from discord.ext import commands
import json
import os
from datetime import datetime
import asyncio

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Verification Key
VERIFICATION_KEY = "ZpofeVerifiedU"

def add_verified_user(user_id: int):
    """Add a user to the verified list and save to file."""
    data = load_data()
    if 'verified_users' not in data:
        data['verified_users'] = []
    
    if user_id not in data['verified_users']:
        data['verified_users'].append(user_id)
        save_data(data)

def is_verified(interaction: discord.Interaction) -> bool:
    """Check if user is in the verified list."""
    data = load_data()
    verified_users = data.get('verified_users', [])
    return interaction.user.id in verified_users

# Load bot data
def load_data():
    try:
        with open('bot_data.json', 'r') as f:
            data = json.load(f)
            if 'stored_embeds' not in data:
                data['stored_embeds'] = {}
            if 'embed_counter' not in data:
                data['embed_counter'] = 1
            if 'verified_users' not in data:
                data['verified_users'] = []
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        default_data = {
            "stored_embeds": {},
            "embed_counter": 1,
            "verified_users": []
        }
        save_data(default_data)
        return default_data

def save_data(data):
    with open('bot_data.json', 'w') as f:
        json.dump(data, f, indent=2)

@bot.event
async def on_ready():
    print(f'🤖 {bot.user} has connected to Discord!')

    try:
        await bot.wait_until_ready()
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash commands")

        print(f"📊 Connected to {len(bot.guilds)} guilds:")
        for guild in bot.guilds:
            print(f"  - {guild.name} (ID: {guild.id})")

    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")

@bot.event
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    print(f"❌ App command error: {error}")
    try:
        if not interaction.response.is_done():
            await interaction.response.send_message("❌ An error occurred while processing the command.", ephemeral=True)
    except:
        pass

class VerificationModal(discord.ui.Modal, title="Staff Verification Required"):
    def __init__(self):
        super().__init__()

    key_input = discord.ui.TextInput(
        label="Verification Key",
        placeholder="Enter your staff verification key...",
        max_length=50,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            entered_key = str(self.key_input.value).strip()

            if entered_key == VERIFICATION_KEY:
                add_verified_user(interaction.user.id)
                await interaction.response.send_message("✅ **Verification Successful!** You now have staff access. Please run the command again.", ephemeral=True)
            else:
                await interaction.response.send_message("❌ **Invalid Key:** Incorrect verification key entered. Access denied.", ephemeral=True)
        except (discord.errors.NotFound, discord.errors.HTTPException) as e:
            print(f"Verification submit error: {e}")
            # Don't try to respond again if interaction is already done

async def check_verification(interaction: discord.Interaction) -> bool:
    """Check if user is verified, show verification modal if not"""
    if is_verified(interaction):
        return True

    try:
        modal = VerificationModal()
        await interaction.response.send_modal(modal)
    except (discord.errors.NotFound, discord.errors.HTTPException) as e:
        print(f"Verification modal error: {e}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ Session expired. Please try the command again.", ephemeral=True)
        except:
            pass
    return False

class EmbedModal(discord.ui.Modal, title="Create Embed"):
    def __init__(self):
        super().__init__()

    title_input = discord.ui.TextInput(
        label="Embed Title",
        placeholder="Enter the embed title...",
        max_length=256,
        required=False
    )

    description_input = discord.ui.TextInput(
        label="Embed Description",
        placeholder="Enter the embed description...",
        style=discord.TextStyle.paragraph,
        max_length=4000,
        required=False
    )

    color_input = discord.ui.TextInput(
        label="Embed Color (hex)",
        placeholder="e.g., #FF0000",
        max_length=10,
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            embed_data = {
                'title': str(self.title_input.value) if self.title_input.value else None,
                'description': str(self.description_input.value) if self.description_input.value else None,
                'color': str(self.color_input.value) if self.color_input.value else None,
            }

            view = EmbedOptionsView(embed_data)
            await interaction.response.send_message("Embed created! Choose an option:", view=view, ephemeral=True)
        except Exception as e:
            print(f"Error in EmbedModal submit: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ Error creating embed.", ephemeral=True)

class EmbedOptionsView(discord.ui.View):
    def __init__(self, embed_data):
        super().__init__(timeout=300)
        self.embed_data = embed_data

    @discord.ui.button(label="Preview", style=discord.ButtonStyle.secondary, emoji="👁️")
    async def preview_embed(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            embed = create_embed_from_data(self.embed_data)
            await interaction.response.send_message("**Preview:**", embed=embed, ephemeral=True)
        except Exception as e:
            print(f"Error in preview_embed: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ Error creating preview.", ephemeral=True)

    @discord.ui.button(label="Save", style=discord.ButtonStyle.success, emoji="💾")
    async def save_embed(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            data = load_data()
            embed_id = f"embed_{data.get('embed_counter', 1)}"
            data['stored_embeds'][embed_id] = self.embed_data.copy()
            data['embed_counter'] = data.get('embed_counter', 1) + 1
            save_data(data)

            await interaction.response.send_message(f"✅ Embed saved! (ID: {embed_id})", ephemeral=True)
        except Exception as e:
            print(f"Error in save_embed: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ Error saving embed.", ephemeral=True)

def create_embed_from_data(embed_data):
    embed = discord.Embed()

    if embed_data.get('title'):
        embed.title = embed_data['title']

    if embed_data.get('description'):
        embed.description = embed_data['description']

    if embed_data.get('color'):
        color_str = embed_data['color']
        if color_str.startswith('#'):
            color_str = color_str[1:]
        try:
            embed.color = int(color_str, 16)
        except ValueError:
            embed.color = 0x0099ff

    return embed

class SpawnEmbedSelectView(discord.ui.View):
    def __init__(self, stored_embeds):
        super().__init__(timeout=300)
        self.stored_embeds = stored_embeds

        options = []
        for embed_id, embed_data in stored_embeds.items():
            title = embed_data.get('title', 'No title')
            options.append(discord.SelectOption(
                label=f"{embed_id}: {title}"[:100],
                value=embed_id
            ))

        self.select_embed.options = options[:25]

    @discord.ui.select(placeholder="Choose an embed to spawn...")
    async def select_embed(self, interaction: discord.Interaction, select: discord.ui.Select):
        try:
            embed_id = select.values[0]
            embed_data = self.stored_embeds[embed_id]
            embed = create_embed_from_data(embed_data)
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            print(f"Error in spawn embed select: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ Error spawning embed.", ephemeral=True)

# Slash Commands
@bot.tree.command(name="create_embed", description="[STAFF ONLY] Create a custom embed message")
async def create_embed(interaction: discord.Interaction):
    try:
        if not await check_verification(interaction):
            return

        try:
            modal = EmbedModal()
            await interaction.response.send_modal(modal)
        except (discord.errors.NotFound, discord.errors.HTTPException) as e:
            print(f"Modal error in create_embed: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ Session expired. Please try the command again.", ephemeral=True)
    except Exception as e:
        print(f"Error in create_embed: {e}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred.", ephemeral=True)
        except:
            pass

@bot.tree.command(name="spawnembed", description="[STAFF ONLY] Spawn a stored embed message")
async def spawn_embed(interaction: discord.Interaction):
    try:
        if not await check_verification(interaction):
            return

        data = load_data()

        if not data.get('stored_embeds') or len(data['stored_embeds']) == 0:
            await interaction.response.send_message("No embeds stored! Use `/create_embed` to create one first.", ephemeral=True)
            return

        view = SpawnEmbedSelectView(data['stored_embeds'])
        await interaction.response.send_message(f"**Select Embed to Spawn:**", view=view, ephemeral=True)
    except Exception as e:
        print(f"Error in spawn_embed: {e}")
        if not interaction.response.is_done():
            await interaction.response.send_message("❌ An error occurred.", ephemeral=True)

class EditEmbedSelectView(discord.ui.View):
    def __init__(self, stored_embeds):
        super().__init__(timeout=300)
        self.stored_embeds = stored_embeds

        options = []
        for embed_id, embed_data in stored_embeds.items():
            title = embed_data.get('title', 'No title')
            options.append(discord.SelectOption(
                label=f"{embed_id}: {title}"[:100],
                value=embed_id
            ))

        self.select_embed.options = options[:25]

    @discord.ui.select(placeholder="Choose an embed to edit...")
    async def select_embed(self, interaction: discord.Interaction, select: discord.ui.Select):
        try:
            embed_id = select.values[0]
            embed_data = self.stored_embeds[embed_id]
            modal = EditEmbedModal(embed_id, embed_data)
            await interaction.response.send_modal(modal)
        except Exception as e:
            print(f"Error in edit embed select: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ Error loading embed for editing.", ephemeral=True)

class EditEmbedModal(discord.ui.Modal, title="Edit Embed"):
    def __init__(self, embed_id, embed_data):
        super().__init__()
        self.embed_id = embed_id
        
        # Pre-fill the inputs with existing data
        self.title_input.default = embed_data.get('title', '')
        self.description_input.default = embed_data.get('description', '')
        self.color_input.default = embed_data.get('color', '')

    title_input = discord.ui.TextInput(
        label="Embed Title",
        placeholder="Enter the embed title...",
        max_length=256,
        required=False
    )

    description_input = discord.ui.TextInput(
        label="Embed Description",
        placeholder="Enter the embed description...",
        style=discord.TextStyle.paragraph,
        max_length=4000,
        required=False
    )

    color_input = discord.ui.TextInput(
        label="Embed Color (hex)",
        placeholder="e.g., #FF0000",
        max_length=10,
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            updated_embed_data = {
                'title': str(self.title_input.value) if self.title_input.value else None,
                'description': str(self.description_input.value) if self.description_input.value else None,
                'color': str(self.color_input.value) if self.color_input.value else None,
            }

            # Save the updated embed
            data = load_data()
            data['stored_embeds'][self.embed_id] = updated_embed_data
            save_data(data)

            view = EmbedOptionsView(updated_embed_data)
            await interaction.response.send_message(f"✅ Embed `{self.embed_id}` updated! Choose an option:", view=view, ephemeral=True)
        except Exception as e:
            print(f"Error in EditEmbedModal submit: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ Error updating embed.", ephemeral=True)

@bot.tree.command(name="edit_embed", description="[STAFF ONLY] Edit a stored embed message")
async def edit_embed(interaction: discord.Interaction):
    try:
        if not await check_verification(interaction):
            return

        data = load_data()

        if not data.get('stored_embeds') or len(data['stored_embeds']) == 0:
            try:
                await interaction.response.send_message("No embeds stored! Use `/create_embed` to create one first.", ephemeral=True)
            except (discord.errors.NotFound, discord.errors.HTTPException):
                pass
            return

        try:
            view = EditEmbedSelectView(data['stored_embeds'])
            await interaction.response.send_message("**Select Embed to Edit:**", view=view, ephemeral=True)
        except (discord.errors.NotFound, discord.errors.HTTPException) as e:
            print(f"Response error in edit_embed: {e}")
    except Exception as e:
        print(f"Error in edit_embed: {e}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred.", ephemeral=True)
        except:
            pass

# Run the bot
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
if TOKEN:
    bot.run(TOKEN)
else:
    print("❌ DISCORD_BOT_TOKEN not found in environment variables")
    print("Please add your Discord bot token to the environment variables.")