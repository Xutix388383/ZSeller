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

class EmbedModal(discord.ui.Modal, title="Create Advanced Embed"):
    def __init__(self):
        super().__init__()

    embed_name_input = discord.ui.TextInput(
        label="🏷️ Embed Name (for saving/referencing)",
        placeholder="Enter a unique name for this embed...",
        max_length=50,
        required=True
    )

    title_input = discord.ui.TextInput(
        label="📝 Embed Title",
        placeholder="Enter the main title for your embed...",
        max_length=256,
        required=False
    )

    description_input = discord.ui.TextInput(
        label="📄 Embed Description",
        placeholder="Enter detailed description or content...",
        style=discord.TextStyle.paragraph,
        max_length=4000,
        required=False
    )

    color_input = discord.ui.TextInput(
        label="🎨 Embed Color (hex)",
        placeholder="e.g., #FF0000, #00FF00, #0099FF",
        max_length=10,
        required=False
    )

    image_input = discord.ui.TextInput(
        label="🖼️ Main Image URL",
        placeholder="Enter image URL (jpg, png, gif, webp)...",
        max_length=500,
        required=False
    )

    footer_input = discord.ui.TextInput(
        label="👣 Footer Text",
        placeholder="Enter footer text (appears at bottom)...",
        max_length=2048,
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            embed_name = str(self.embed_name_input.value).strip()
            
            # Check if embed name already exists
            data = load_data()
            if embed_name in data.get('stored_embeds', {}):
                await interaction.response.send_message(f"❌ **Embed name `{embed_name}` already exists!** Please choose a different name.", ephemeral=True)
                return

            embed_data = {
                'embed_name': embed_name,
                'title': str(self.title_input.value) if self.title_input.value else None,
                'description': str(self.description_input.value) if self.description_input.value else None,
                'color': str(self.color_input.value) if self.color_input.value else None,
                'image_url': str(self.image_input.value) if self.image_input.value else None,
                'footer_text': str(self.footer_input.value) if self.footer_input.value else None
            }

            # Show advanced options modal
            modal = AdvancedEmbedModal(embed_data)
            await interaction.response.send_modal(modal)
        except Exception as e:
            print(f"Error in EmbedModal submit: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ Error creating embed.", ephemeral=True)

class AdvancedEmbedModal(discord.ui.Modal, title="Advanced Embed Options"):
    def __init__(self, embed_data):
        super().__init__()
        self.embed_data = embed_data

    thumbnail_input = discord.ui.TextInput(
        label="🖼️ Thumbnail URL (small image top-right)",
        placeholder="Enter thumbnail URL (optional)...",
        max_length=500,
        required=False
    )

    footer_icon_input = discord.ui.TextInput(
        label="🔗 Footer Icon URL",
        placeholder="Enter footer icon URL (optional)...",
        max_length=500,
        required=False
    )

    author_name_input = discord.ui.TextInput(
        label="👤 Author Name (appears at top)",
        placeholder="Enter author name (optional)...",
        max_length=256,
        required=False
    )

    author_icon_input = discord.ui.TextInput(
        label="👤 Author Icon URL",
        placeholder="Enter author icon URL (optional)...",
        max_length=500,
        required=False
    )

    timestamp_input = discord.ui.TextInput(
        label="⏰ Show Timestamp (yes/no)",
        placeholder="Type 'yes' to show current timestamp...",
        max_length=3,
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Add advanced options to embed data
            self.embed_data.update({
                'thumbnail_url': str(self.thumbnail_input.value) if self.thumbnail_input.value else None,
                'footer_icon_url': str(self.footer_icon_input.value) if self.footer_icon_input.value else None,
                'author_name': str(self.author_name_input.value) if self.author_name_input.value else None,
                'author_icon_url': str(self.author_icon_input.value) if self.author_icon_url.value else None,
                'show_timestamp': str(self.timestamp_input.value).lower() == 'yes' if self.timestamp_input.value else False
            })

            # Auto-save the embed without button options
            data = load_data()
            embed_name = self.embed_data.get('embed_name', f"embed_{data.get('embed_counter', 1)}")
            
            # Remove embed_name from the data before saving
            embed_data_to_save = self.embed_data.copy()
            if 'embed_name' in embed_data_to_save:
                del embed_data_to_save['embed_name']
            
            data['stored_embeds'][embed_name] = embed_data_to_save
            data['embed_counter'] = data.get('embed_counter', 1) + 1
            save_data(data)

            # Create and show preview of the saved embed
            embed = create_embed_from_data(embed_data_to_save)
            await interaction.response.send_message(f"✅ **Embed `{embed_name}` created and saved successfully!**\n**Preview:**", embed=embed, ephemeral=True)
        except Exception as e:
            print(f"Error in AdvancedEmbedModal submit: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ Error creating advanced embed.", ephemeral=True)



def create_embed_from_data(embed_data):
    embed = discord.Embed()

    # Basic embed properties
    if embed_data.get('title'):
        embed.title = embed_data['title']

    if embed_data.get('description'):
        embed.description = embed_data['description']

    # Color handling with better defaults
    if embed_data.get('color'):
        color_str = embed_data['color']
        if color_str.startswith('#'):
            color_str = color_str[1:]
        try:
            embed.color = int(color_str, 16)
        except ValueError:
            embed.color = 0x0099ff
    else:
        embed.color = 0x0099FF  # Default blue color

    # Advanced image options
    if embed_data.get('image_url'):
        embed.set_image(url=embed_data['image_url'])

    if embed_data.get('thumbnail_url'):
        embed.set_thumbnail(url=embed_data['thumbnail_url'])

    # Advanced author section
    if embed_data.get('author_name'):
        author_icon = embed_data.get('author_icon_url')
        embed.set_author(
            name=embed_data['author_name'],
            icon_url=author_icon if author_icon else None
        )

    # Advanced footer with icon support
    if embed_data.get('footer_text'):
        footer_icon = embed_data.get('footer_icon_url')
        embed.set_footer(
            text=embed_data['footer_text'],
            icon_url=footer_icon if footer_icon else None
        )

    # Timestamp support
    if embed_data.get('show_timestamp'):
        embed.timestamp = datetime.utcnow()

    return embed

class SpawnEmbedSelectView(discord.ui.View):
    def __init__(self, stored_embeds):
        super().__init__(timeout=300)
        self.stored_embeds = stored_embeds

        options = []
        for embed_name, embed_data in stored_embeds.items():
            title = embed_data.get('title', 'No title')
            options.append(discord.SelectOption(
                label=f"{embed_name}: {title}"[:100],
                value=embed_name
            ))

        self.select_embed.options = options[:25]

    @discord.ui.select(placeholder="Choose an embed to spawn...")
    async def select_embed(self, interaction: discord.Interaction, select: discord.ui.Select):
        try:
            embed_name = select.values[0]
            embed_data = self.stored_embeds[embed_name]
            embed = create_embed_from_data(embed_data)
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            print(f"Error in spawn embed select: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ Error spawning embed.", ephemeral=True)

# Slash Commands
@bot.tree.command(name="create_embed", description="[STAFF ONLY] Create advanced embeds with images, footers, and styling")
async def create_embed(interaction: discord.Interaction):
    try:
        if not await check_verification(interaction):
            return

        modal = EmbedModal()
        await interaction.response.send_modal(modal)
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
        stored_embeds = data.get('stored_embeds', {})

        if not stored_embeds or len(stored_embeds) == 0:
            await interaction.response.send_message("📭 **No embeds stored!** Use `/create_embed` to create one first.", ephemeral=True)
            return

        view = SpawnEmbedSelectView(stored_embeds)
        await interaction.response.send_message("**Select Embed to Spawn:**", view=view, ephemeral=True)
    except Exception as e:
        print(f"Error in spawn_embed: {e}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred.", ephemeral=True)
        except:
            pass

class EditEmbedSelectView(discord.ui.View):
    def __init__(self, stored_embeds):
        super().__init__(timeout=300)
        self.stored_embeds = stored_embeds

        options = []
        for embed_name, embed_data in stored_embeds.items():
            title = embed_data.get('title', 'No title')
            options.append(discord.SelectOption(
                label=f"{embed_name}: {title}"[:100],
                value=embed_name
            ))

        self.select_embed.options = options[:25]

    @discord.ui.select(placeholder="Choose an embed to edit...")
    async def select_embed(self, interaction: discord.Interaction, select: discord.ui.Select):
        try:
            embed_name = select.values[0]
            embed_data = self.stored_embeds[embed_name]
            modal = EditEmbedModal(embed_name, embed_data)
            await interaction.response.send_modal(modal)
        except Exception as e:
            print(f"Error in edit embed select: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ Error loading embed for editing.", ephemeral=True)

class EditEmbedModal(discord.ui.Modal, title="Edit Advanced Embed"):
    def __init__(self, embed_name, embed_data):
        super().__init__()
        self.embed_name = embed_name
        self.embed_data = embed_data

        # Pre-fill the inputs with existing data
        self.title_input.default = embed_data.get('title', '')
        self.description_input.default = embed_data.get('description', '')
        self.color_input.default = embed_data.get('color', '')
        self.image_input.default = embed_data.get('image_url', '')
        self.footer_input.default = embed_data.get('footer_text', '')

    title_input = discord.ui.TextInput(
        label="📝 Embed Title",
        placeholder="Enter the embed title...",
        max_length=256,
        required=False
    )

    description_input = discord.ui.TextInput(
        label="📄 Embed Description",
        placeholder="Enter the embed description...",
        style=discord.TextStyle.paragraph,
        max_length=4000,
        required=False
    )

    color_input = discord.ui.TextInput(
        label="🎨 Embed Color (hex)",
        placeholder="e.g., #FF0000, #00FF00, #0099FF",
        max_length=10,
        required=False
    )

    image_input = discord.ui.TextInput(
        label="🖼️ Main Image URL",
        placeholder="Enter image URL (jpg, png, gif, webp)...",
        max_length=500,
        required=False
    )

    footer_input = discord.ui.TextInput(
        label="👣 Footer Text",
        placeholder="Enter footer text...",
        max_length=2048,
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            updated_embed_data = {
                'title': str(self.title_input.value) if self.title_input.value else None,
                'description': str(self.description_input.value) if self.description_input.value else None,
                'color': str(self.color_input.value) if self.color_input.value else None,
                'image_url': str(self.image_input.value) if self.image_input.value else None,
                'footer_text': str(self.footer_input.value) if self.footer_input.value else None,
                # Preserve existing advanced features
                'thumbnail_url': self.embed_data.get('thumbnail_url'),
                'footer_icon_url': self.embed_data.get('footer_icon_url'),
                'author_name': self.embed_data.get('author_name'),
                'author_icon_url': self.embed_data.get('author_icon_url'),
                'show_timestamp': self.embed_data.get('show_timestamp', False)
            }

            # Save the updated embed
            data = load_data()
            data['stored_embeds'][self.embed_name] = updated_embed_data
            save_data(data)

            # Create and show preview of the updated embed
            embed = create_embed_from_data(updated_embed_data)
            await interaction.response.send_message(f"✅ **Embed `{self.embed_name}` updated successfully!**\n**Preview:**", embed=embed, ephemeral=True)
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
        stored_embeds = data.get('stored_embeds', {})

        if not stored_embeds or len(stored_embeds) == 0:
            await interaction.response.send_message("📭 **No embeds stored!** Use `/create_embed` to create one first.", ephemeral=True)
            return

        view = EditEmbedSelectView(stored_embeds)
        await interaction.response.send_message("**Select Embed to Edit:**", view=view, ephemeral=True)
    except Exception as e:
        print(f"Error in edit_embed: {e}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred.", ephemeral=True)
        except:
            pass

@bot.tree.command(name="delete_embed", description="[STAFF ONLY] Delete a stored embed by name")
async def delete_embed(interaction: discord.Interaction, embed_name: str):
    try:
        if not await check_verification(interaction):
            return

        data = load_data()
        stored_embeds = data.get('stored_embeds', {})

        if not stored_embeds or len(stored_embeds) == 0:
            await interaction.response.send_message("📭 **No embeds have been created yet!** Use `/create_embed` to create your first embed.", ephemeral=True)
            return

        # Check if the embed exists
        if embed_name not in stored_embeds:
            available_embeds = list(stored_embeds.keys())
            embed_list = ", ".join([f"`{name}`" for name in available_embeds])
            await interaction.response.send_message(
                f"❌ **Embed `{embed_name}` not found!**\n\n**Available embeds:** {embed_list}",
                ephemeral=True
            )
            return

        # Show confirmation
        view = ConfirmDeleteView(embed_name)
        await interaction.response.send_message(
            f"⚠️ **Are you sure you want to delete embed `{embed_name}`?**\nThis action cannot be undone!",
            view=view,
            ephemeral=True
        )
    except Exception as e:
        print(f"Error in delete_embed: {e}")
        if not interaction.response.is_done():
            await interaction.response.send_message("❌ An error occurred.", ephemeral=True)

class ConfirmDeleteView(discord.ui.View):
    def __init__(self, embed_name):
        super().__init__(timeout=60)
        self.embed_name = embed_name

    @discord.ui.button(label="Yes, Delete", style=discord.ButtonStyle.danger, emoji="✅")
    async def confirm_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            data = load_data()
            
            if self.embed_name in data.get('stored_embeds', {}):
                del data['stored_embeds'][self.embed_name]
                save_data(data)
                await interaction.response.send_message(f"✅ **Embed `{self.embed_name}` has been deleted successfully!**", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Embed not found or already deleted.", ephemeral=True)
        except Exception as e:
            print(f"Error in confirm delete: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ Error deleting embed.", ephemeral=True)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("❌ Delete operation cancelled.", ephemeral=True)

# Run the bot
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
if TOKEN:
    bot.run(TOKEN)
else:
    print("❌ DISCORD_BOT_TOKEN not found in environment variables")
    print("Please add your Discord bot token to the environment variables.")