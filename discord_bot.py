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

# Store verified users (in-memory, will reset on bot restart)
# For persistent storage, consider a database or a file.
verified_users = set()

def add_verified_user(user_id: int):
    """Add a user to the verified list."""
    verified_users.add(user_id)

def is_verified(interaction: discord.Interaction) -> bool:
    """Check if user is in the verified list."""
    return interaction.user.id in verified_users

# Load bot data
def load_data():
    try:
        with open('bot_data.json', 'r') as f:
            data = json.load(f)
            # Ensure all required keys exist
            if 'stored_embeds' not in data:
                data['stored_embeds'] = {}
            if 'embed_counter' not in data:
                data['embed_counter'] = 1
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        default_data = {
            "stored_embeds": {},
            "embed_counter": 1
        }
        save_data(default_data)
        return default_data

def save_data(data):
    with open('bot_data.json', 'w') as f:
        json.dump(data, f, indent=2)

@bot.event
async def on_ready():
    print(f'🤖 {bot.user} has connected to Discord!')

    # Sync slash commands
    try:
        await bot.wait_until_ready()
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash commands")

        # Print available guilds for debugging
        print(f"📊 Connected to {len(bot.guilds)} guilds:")
        for guild in bot.guilds:
            print(f"  - {guild.name} (ID: {guild.id})")

    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")
        import traceback
        traceback.print_exc()

@bot.event
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    print(f"❌ App command error: {error}")
    import traceback
    traceback.print_exc()

    try:
        if not interaction.response.is_done():
            await interaction.response.send_message("❌ An error occurred while processing the command.", ephemeral=True)
        else:
            await interaction.followup.send("❌ An error occurred while processing the command.", ephemeral=True)
    except:
        pass

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    await bot.process_commands(message)

class VerificationModal(discord.ui.Modal, title="Staff Verification Required"):
    def __init__(self, original_interaction, command_name):
        super().__init__()
        self.original_interaction = original_interaction
        self.command_name = command_name

    key_input = discord.ui.TextInput(
        label="Verification Key",
        placeholder="Enter your staff verification key...",
        max_length=50,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        entered_key = str(self.key_input.value).strip()

        if entered_key == VERIFICATION_KEY:
            # Add user to verified list
            add_verified_user(interaction.user.id)
            await interaction.response.send_message("✅ **Verification Successful!** You now have staff access. Please run the command again.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ **Invalid Key:** Incorrect verification key entered. Access denied.", ephemeral=True)

async def check_verification(interaction: discord.Interaction, command_name: str) -> bool:
    """Check if user is verified, show verification modal if not"""
    # Check if user is already verified
    if is_verified(interaction):
        return True

    # Show verification modal
    modal = VerificationModal(interaction, command_name)
    await interaction.response.send_modal(modal)
    return False

class EmbedModal(discord.ui.Modal):
    def __init__(self, embed_data=None, editing_embed_id=None):
        super().__init__(title="Create Embed")
        self.embed_data = embed_data or {}
        self.editing_embed_id = editing_embed_id

        # Create text inputs
        self.title_input = discord.ui.TextInput(
            label="Embed Title",
            placeholder="Enter the embed title...",
            max_length=256,
            required=False,
            default=self.embed_data.get('title', '')
        )

        self.description_input = discord.ui.TextInput(
            label="Embed Description",
            placeholder="Enter the embed description...",
            style=discord.TextStyle.paragraph,
            max_length=4000,
            required=False,
            default=self.embed_data.get('description', '')
        )

        self.color_input = discord.ui.TextInput(
            label="Embed Color (hex)",
            placeholder="e.g., #FF0000 or 0xFF0000",
            max_length=10,
            required=False,
            default=self.embed_data.get('color', '')
        )

        self.footer_input = discord.ui.TextInput(
            label="Footer Text",
            placeholder="Enter footer text...",
            max_length=2048,
            required=False,
            default=self.embed_data.get('footer', '')
        )

        self.thumbnail_input = discord.ui.TextInput(
            label="Thumbnail URL",
            placeholder="Enter image URL for thumbnail...",
            max_length=2048,
            required=False,
            default=self.embed_data.get('thumbnail', '')
        )

        # Add inputs to modal
        self.add_item(self.title_input)
        self.add_item(self.description_input)
        self.add_item(self.color_input)
        self.add_item(self.footer_input)
        self.add_item(self.thumbnail_input)

    async def on_submit(self, interaction: discord.Interaction):
        # Update the existing embed_data instead of creating new one
        self.embed_data.update({
            'title': str(self.title_input.value) if self.title_input.value else None,
            'description': str(self.description_input.value) if self.description_input.value else None,
            'color': str(self.color_input.value) if self.color_input.value else None,
            'footer': str(self.footer_input.value) if self.footer_input.value else None,
            'thumbnail': str(self.thumbnail_input.value) if self.thumbnail_input.value else None,
        })

        # Preserve existing data that wasn't in the modal
        if 'fields' not in self.embed_data:
            self.embed_data['fields'] = []
        if 'buttons' not in self.embed_data:
            self.embed_data['buttons'] = []

        view = EmbedOptionsView(self.embed_data, self.editing_embed_id)
        action_text = "updated" if self.editing_embed_id else "created"
        await interaction.response.send_message(f"Embed {action_text}! Choose additional options:", view=view, ephemeral=True)

class FieldModal(discord.ui.Modal, title="Add Field"):
    def __init__(self, embed_data, field_index=None, editing_embed_id=None):
        super().__init__()
        self.embed_data = embed_data
        self.field_index = field_index
        self.editing_embed_id = editing_embed_id

        if field_index is not None and field_index < len(embed_data.get('fields', [])):
            field = embed_data['fields'][field_index]
            self.name_input.default = field.get('name', '')
            self.value_input.default = field.get('value', '')
            self.inline_input.default = str(field.get('inline', False))

    name_input = discord.ui.TextInput(
        label="Field Name",
        placeholder="Enter field name...",
        max_length=256,
        required=True
    )

    value_input = discord.ui.TextInput(
        label="Field Value",
        placeholder="Enter field value...",
        style=discord.TextStyle.paragraph,
        max_length=1024,
        required=True
    )

    inline_input = discord.ui.TextInput(
        label="Inline (True/False)",
        placeholder="True or False",
        max_length=5,
        required=False,
        default="False"
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            inline = self.inline_input.value.lower() == 'true'
            field_data = {
                'name': str(self.name_input.value),
                'value': str(self.value_input.value),
                'inline': inline
            }

            if 'fields' not in self.embed_data:
                self.embed_data['fields'] = []

            if self.field_index is not None:
                self.embed_data['fields'][self.field_index] = field_data
                action_text = "updated"
            else:
                self.embed_data['fields'].append(field_data)
                action_text = "added"

            view = EmbedOptionsView(self.embed_data, self.editing_embed_id)
            await interaction.response.send_message(f"✅ Field {action_text}! Continue editing:", view=view, ephemeral=True)
        except Exception as e:
            print(f"Error in FieldModal submit: {e}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("❌ Error with field. Please try again.", ephemeral=True)
            except:
                pass

class EmbedOptionsView(discord.ui.View):
    def __init__(self, embed_data, editing_embed_id=None):
        super().__init__(timeout=300)
        self.embed_data = embed_data
        self.editing_embed_id = editing_embed_id

        # Ensure buttons list exists
        if 'buttons' not in self.embed_data:
            self.embed_data['buttons'] = []

    @discord.ui.button(label="Create Button", style=discord.ButtonStyle.primary, emoji="🔘")
    async def create_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if len(self.embed_data.get('buttons', [])) >= 5:
            await interaction.response.send_message("❌ Maximum of 5 buttons allowed per embed!", ephemeral=True)
            return

        try:
            modal = ButtonModal(self.embed_data, editing_embed_id=self.editing_embed_id)
            await interaction.response.send_modal(modal)
        except discord.InteractionResponded:
            # If interaction was already responded to, try followup
            modal = ButtonModal(self.embed_data, editing_embed_id=self.editing_embed_id)
            await interaction.followup.send("Opening button creation modal...", ephemeral=True)

    @discord.ui.button(label="Create Sound Button", style=discord.ButtonStyle.secondary, emoji="🔊")
    async def create_sound_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if len(self.embed_data.get('buttons', [])) >= 5:
            await interaction.response.send_message("❌ Maximum of 5 buttons allowed per embed!", ephemeral=True)
            return

        try:
            modal = SoundButtonModal(self.embed_data, editing_embed_id=self.editing_embed_id)
            await interaction.response.send_modal(modal)
        except discord.InteractionResponded:
            modal = SoundButtonModal(self.embed_data, editing_embed_id=self.editing_embed_id)
            await interaction.followup.send("Opening sound button creation modal...", ephemeral=True)

    @discord.ui.button(label="Add Field", style=discord.ButtonStyle.secondary, emoji="📝")
    async def add_field(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            modal = FieldModal(self.embed_data, editing_embed_id=self.editing_embed_id)
            await interaction.response.send_modal(modal)
        except Exception as e:
            print(f"Error in add_field: {e}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("❌ Error opening field modal. Please try again.", ephemeral=True)
            except:
                pass

    @discord.ui.button(label="Add Author", style=discord.ButtonStyle.secondary, emoji="👤")
    async def add_author(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            modal = AuthorModal(self.embed_data, self.editing_embed_id)
            await interaction.response.send_modal(modal)
        except Exception as e:
            print(f"Error in add_author: {e}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("❌ Error opening author modal. Please try again.", ephemeral=True)
            except:
                pass

    @discord.ui.button(label="Add Image", style=discord.ButtonStyle.secondary, emoji="🖼️")
    async def add_image(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            modal = ImageModal(self.embed_data, self.editing_embed_id)
            await interaction.response.send_modal(modal)
        except Exception as e:
            print(f"Error in add_image: {e}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("❌ Error opening image modal. Please try again.", ephemeral=True)
            except:
                pass

    @discord.ui.button(label="Manage Fields", style=discord.ButtonStyle.secondary, emoji="📝")
    async def manage_fields(self, interaction: discord.Interaction, button: discord.ui.Button):
        fields = self.embed_data.get('fields', [])
        if not fields:
            await interaction.response.send_message("No fields to manage! Add a field first using the 'Add Field' option.", ephemeral=True)
            return

        view = FieldManagerView(self.embed_data, self.editing_embed_id)
        await interaction.response.send_message("**Field Manager:**\nSelect a field to edit or delete. All fields from your embed will be shown here:", view=view, ephemeral=True)

    @discord.ui.button(label="Manage Buttons", style=discord.ButtonStyle.secondary, emoji="🎛️")
    async def manage_buttons(self, interaction: discord.Interaction, button: discord.ui.Button):
        buttons = self.embed_data.get('buttons', [])
        if not buttons:
            await interaction.response.send_message("No buttons to manage! Add a button first using the 'Create Button' option.", ephemeral=True)
            return

        view = ButtonManagerView(self.embed_data, self.editing_embed_id)
        await interaction.response.send_message("**Button Manager:**\nSelect a button to edit or delete. All buttons from your embed will be shown here:", view=view, ephemeral=True)

    @discord.ui.button(label="Preview", style=discord.ButtonStyle.secondary, emoji="👁️")
    async def preview_embed(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = create_embed_from_data(self.embed_data)
        view = create_embed_button_view(self.embed_data) if self.embed_data.get('buttons') else None
        await interaction.response.send_message("**Preview:**", embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="Save Changes", style=discord.ButtonStyle.primary, emoji="💾")
    async def save_changes(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            data = load_data()

            if self.editing_embed_id:
                # Update existing embed - don't create a new one
                data['stored_embeds'][self.editing_embed_id] = self.embed_data.copy()
                embed_id = self.editing_embed_id
                action_text = "updated and saved"
            else:
                # Create new embed
                embed_id = f"embed_{data.get('embed_counter', 1)}"
                data['stored_embeds'][embed_id] = self.embed_data.copy()
                data['embed_counter'] = data.get('embed_counter', 1) + 1
                action_text = "saved"
                # Update the view to show we're now editing this embed
                self.editing_embed_id = embed_id

            save_data(data)

            await interaction.response.send_message(f"✅ Embed {action_text}! (ID: {embed_id})", ephemeral=True)
        except Exception as e:
            print(f"Error in save_changes: {e}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("❌ Error saving embed. Please try again.", ephemeral=True)
                else:
                    await interaction.followup.send("❌ Error saving embed. Please try again.", ephemeral=True)
            except:
                pass

    @discord.ui.button(label="Send Embed", style=discord.ButtonStyle.success, emoji="✅")
    async def send_embed(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            embed = create_embed_from_data(self.embed_data)

            # Validate embed has content
            if not any([self.embed_data.get('title'), self.embed_data.get('description'),
                       self.embed_data.get('fields'), self.embed_data.get('image')]):
                await interaction.response.send_message("❌ Embed must have at least a title, description, field, or image.", ephemeral=True)
                return

            # Save embed if not already saved
            data = load_data()

            if self.editing_embed_id:
                # Update existing embed - don't create a new one
                data['stored_embeds'][self.editing_embed_id] = self.embed_data.copy()
                embed_id = self.editing_embed_id
                action_text = "updated and sent"
            else:
                # Create new embed
                embed_id = f"embed_{data.get('embed_counter', 1)}"
                data['stored_embeds'][embed_id] = self.embed_data.copy()
                data['embed_counter'] = data.get('embed_counter', 1) + 1
                action_text = "sent"
                # Update the view to show we're now editing this embed
                self.editing_embed_id = embed_id

            save_data(data)

            await interaction.response.send_message(f"✅ Embed {action_text}! (ID: {embed_id})", ephemeral=True)

            # Create button view if buttons exist
            button_view = create_embed_button_view(self.embed_data) if self.embed_data.get('buttons') else None

            # Use followup to send the actual embed to avoid interaction timeout
            await interaction.followup.send(embed=embed, view=button_view)

        except Exception as e:
            print(f"Error in send_embed: {e}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("❌ Error sending embed. Please try again.", ephemeral=True)
                else:
                    await interaction.followup.send("❌ Error sending embed. Please try again.", ephemeral=True)
            except:
                pass

class ImageModal(discord.ui.Modal, title="Add Image"):
    def __init__(self, embed_data, editing_embed_id=None):
        super().__init__()
        self.embed_data = embed_data
        self.editing_embed_id = editing_embed_id

        # Create text input with proper default value
        self.image_url = discord.ui.TextInput(
            label="Image URL",
            placeholder="Enter image URL...",
            max_length=2048,
            required=True,
            default=embed_data.get('image', '')
        )

        # Add input to modal
        self.add_item(self.image_url)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            self.embed_data['image'] = str(self.image_url.value)
            view = EmbedOptionsView(self.embed_data, self.editing_embed_id)
            await interaction.response.send_message("✅ Image added! Continue editing:", view=view, ephemeral=True)
        except Exception as e:
            print(f"Error in ImageModal submit: {e}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("❌ Error adding image. Please try again.", ephemeral=True)
            except:
                pass

class AuthorModal(discord.ui.Modal, title="Add Author"):
    def __init__(self, embed_data, editing_embed_id=None):
        super().__init__()
        self.embed_data = embed_data
        self.editing_embed_id = editing_embed_id

        # Get existing author data
        author = embed_data.get('author', {})

        # Create text inputs with proper default values
        self.author_name = discord.ui.TextInput(
            label="Author Name",
            placeholder="Enter author name...",
            max_length=256,
            required=True,
            default=author.get('name', '')
        )

        self.author_icon = discord.ui.TextInput(
            label="Author Icon URL",
            placeholder="Enter icon URL...",
            max_length=2048,
            required=False,
            default=author.get('icon_url', '')
        )

        # Add inputs to modal
        self.add_item(self.author_name)
        self.add_item(self.author_icon)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            self.embed_data['author'] = {
                'name': str(self.author_name.value),
                'icon_url': str(self.author_icon.value) if self.author_icon.value else None
            }
            view = EmbedOptionsView(self.embed_data, self.editing_embed_id)
            await interaction.response.send_message("✅ Author added! Continue editing:", view=view, ephemeral=True)
        except Exception as e:
            print(f"Error in AuthorModal submit: {e}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("❌ Error adding author. Please try again.", ephemeral=True)
            except:
                pass

class SoundButtonModal(discord.ui.Modal, title="Create Sound Button"):
    def __init__(self, embed_data, editing_embed_id=None):
        super().__init__()
        self.embed_data = embed_data
        self.editing_embed_id = editing_embed_id

    label_input = discord.ui.TextInput(
        label="Button Label",
        placeholder="Enter button text (e.g., Play Music)...",
        max_length=80,
        required=True
    )

    emoji_input = discord.ui.TextInput(
        label="Button Emoji (optional)",
        placeholder="Enter emoji (e.g., 🔊, 🎵, 🎶)",
        max_length=10,
        required=False
    )

    sound_url_input = discord.ui.TextInput(
        label="Sound File URL",
        placeholder="Enter .mp3, .mp4, .wav, or other audio file URL...",
        style=discord.TextStyle.paragraph,
        max_length=2048,
        required=True
    )

    style_input = discord.ui.TextInput(
        label="Button Style",
        placeholder="primary, secondary, success, danger",
        max_length=20,
        required=False,
        default="secondary"
    )

    async def on_submit(self, interaction: discord.Interaction):
        # Validate style
        valid_styles = ['primary', 'secondary', 'success', 'danger']
        style = self.style_input.value.lower() if self.style_input.value else 'secondary'
        if style not in valid_styles:
            style = 'secondary'

        button_data = {
            'label': str(self.label_input.value),
            'emoji': str(self.emoji_input.value) if self.emoji_input.value else None,
            'style': style,
            'action': {
                'type': 'play_sound',
                'sound_url': str(self.sound_url_input.value)
            }
        }

        if 'buttons' not in self.embed_data:
            self.embed_data['buttons'] = []

        self.embed_data['buttons'].append(button_data)

        view = EmbedOptionsView(self.embed_data, self.editing_embed_id)
        try:
            await interaction.response.send_message("🔊 Sound button created! Continue editing:", view=view, ephemeral=True)
        except discord.InteractionResponded:
            await interaction.followup.send("🔊 Sound button created! Continue editing:", view=view, ephemeral=True)

class ButtonModal(discord.ui.Modal, title="Add Button"):
    def __init__(self, embed_data, button_index=None, editing_embed_id=None):
        super().__init__()
        self.embed_data = embed_data
        self.button_index = button_index
        self.editing_embed_id = editing_embed_id

        if button_index is not None and button_index < len(embed_data.get('buttons', [])):
            button = embed_data['buttons'][button_index]
            self.label_input.default = button.get('label', '')
            self.emoji_input.default = button.get('emoji', '')
            self.style_input.default = button.get('style', 'primary')

    label_input = discord.ui.TextInput(
        label="Button Label",
        placeholder="Enter button text...",
        max_length=80,
        required=True
    )

    emoji_input = discord.ui.TextInput(
        label="Button Emoji (optional)",
        placeholder="Enter emoji (e.g., 🛒, 💰, ✅)",
        max_length=10,
        required=False
    )

    style_input = discord.ui.TextInput(
        label="Button Style",
        placeholder="primary, secondary, success, danger",
        max_length=20,
        required=False,
        default="primary"
    )

    async def on_submit(self, interaction: discord.Interaction):
        # Validate style
        valid_styles = ['primary', 'secondary', 'success', 'danger']
        style = self.style_input.value.lower() if self.style_input.value else 'primary'
        if style not in valid_styles:
            style = 'primary'

        button_data = {
            'label': str(self.label_input.value),
            'emoji': str(self.emoji_input.value) if self.emoji_input.value else None,
            'style': style,
            'action': None  # Will be set in the next step
        }

        if 'buttons' not in self.embed_data:
            self.embed_data['buttons'] = []

        if self.button_index is not None:
            # Keep existing action when editing
            if self.button_index < len(self.embed_data['buttons']):
                button_data['action'] = self.embed_data['buttons'][self.button_index].get('action')
            self.embed_data['buttons'][self.button_index] = button_data
        else:
            self.embed_data['buttons'].append(button_data)

        # Show action selection
        view = ButtonActionView(self.embed_data, self.button_index or (len(self.embed_data['buttons']) - 1), self.editing_embed_id)
        try:
            await interaction.response.send_message("Button created! Now choose what this button should do:", view=view, ephemeral=True)
        except discord.InteractionResponded:
            await interaction.followup.send("Button created! Now choose what this button should do:", view=view, ephemeral=True)

class ButtonActionView(discord.ui.View):
    def __init__(self, embed_data, button_index, editing_embed_id=None):
        super().__init__(timeout=300)
        self.embed_data = embed_data
        self.button_index = button_index
        self.editing_embed_id = editing_embed_id

    @discord.ui.select(
        placeholder="Choose what this button should do...",
        options=[
            discord.SelectOption(label="Send Message", value="send_message", description="Send a message to the channel", emoji="💬"),
            discord.SelectOption(label="Send DM", value="send_dm", description="Send a direct message to the user", emoji="📩"),
            discord.SelectOption(label="Custom Response", value="custom_response", description="Send a custom response message", emoji="📝"),
            discord.SelectOption(label="Play Sound", value="play_sound", description="Play an audio file", emoji="🔊"),
        ]
    )
    async def select_action(self, interaction: discord.Interaction, select: discord.ui.Select):
        action_type = select.values[0]

        if action_type == "send_message":
            modal = ActionConfigModal(self.embed_data, self.button_index, "send_message", "Configure Message")
        elif action_type == "send_dm":
            modal = ActionConfigModal(self.embed_data, self.button_index, "send_dm", "Configure DM Message")
        elif action_type == "custom_response":
            modal = ActionConfigModal(self.embed_data, self.button_index, "custom_response", "Configure Response")
        elif action_type == "play_sound":
            modal = SoundActionModal(self.embed_data, self.button_index)

        # Pass editing_embed_id to the modal
        modal.editing_embed_id = self.editing_embed_id
        await interaction.response.send_modal(modal)

class SoundActionModal(discord.ui.Modal):
    def __init__(self, embed_data, button_index):
        super().__init__(title="Configure Sound Action")
        self.embed_data = embed_data
        self.button_index = button_index

        # Get existing action data if editing
        existing_action = embed_data.get('buttons', [{}])[button_index].get('action', {})
        default_url = existing_action.get('sound_url', '')

        self.sound_url_input = discord.ui.TextInput(
            label="Sound File URL",
            placeholder="Enter .mp3, .mp4, .wav, or other audio file URL...",
            style=discord.TextStyle.paragraph,
            max_length=2048,
            required=True,
            default=default_url
        )
        self.add_item(self.sound_url_input)

    async def on_submit(self, interaction: discord.Interaction):
        action_data = {
            'type': 'play_sound',
            'sound_url': str(self.sound_url_input.value)
        }

        # Update button with action
        self.embed_data['buttons'][self.button_index]['action'] = action_data

        # Get editing_embed_id from the button data if it was being edited
        editing_embed_id = getattr(self, 'editing_embed_id', None)
        view = EmbedOptionsView(self.embed_data, editing_embed_id)
        await interaction.response.send_message(f"🔊 Sound button configured! Continue editing:", view=view, ephemeral=True)

class ActionConfigModal(discord.ui.Modal):
    def __init__(self, embed_data, button_index, action_type, title):
        super().__init__(title=title)
        self.embed_data = embed_data
        self.button_index = button_index
        self.action_type = action_type

        # Get existing action data if editing
        existing_action = embed_data.get('buttons', [{}])[button_index].get('action', {})
        default_message = existing_action.get('message', '')

        # Add message input for all action types
        self.message_input = discord.ui.TextInput(
            label="Message Content",
            placeholder="Enter the message to send...",
            style=discord.TextStyle.paragraph,
            max_length=2000,
            required=True,
            default=default_message
        )
        self.add_item(self.message_input)

    async def on_submit(self, interaction: discord.Interaction):
        action_data = {
            'type': self.action_type,
            'message': str(self.message_input.value)
        }

        # Update button with action
        self.embed_data['buttons'][self.button_index]['action'] = action_data

        # Get editing_embed_id from the button data if it was being edited
        editing_embed_id = getattr(self, 'editing_embed_id', None)
        view = EmbedOptionsView(self.embed_data, editing_embed_id)
        await interaction.response.send_message(f"✅ Button action configured! Continue editing:", view=view, ephemeral=True)

class ButtonManagerView(discord.ui.View):
    def __init__(self, embed_data, editing_embed_id=None):
        super().__init__(timeout=300)
        self.embed_data = embed_data
        self.editing_embed_id = editing_embed_id
        self.selected_button_index = None

        # Create select menu for buttons
        buttons = embed_data.get('buttons', [])
        options = []
        for i, button in enumerate(buttons):
            button_label = button.get('label', f'Button {i+1}')
            action_type = button.get('action', {}).get('type', 'No action')

            options.append(discord.SelectOption(
                label=f"{i+1}. {button_label}"[:100],
                value=str(i),
                description=f"Action: {action_type}"[:100]
            ))

        if options:
            self.select_button.options = options[:25]
        else:
            self.select_button.disabled = True

    @discord.ui.select(placeholder="Choose a button to manage...")
    async def select_button(self, interaction: discord.Interaction, select: discord.ui.Select):
        button_index = int(select.values[0])
        self.selected_button_index = button_index

        button = self.embed_data['buttons'][button_index]
        embed = discord.Embed(
            title=f"🔘 Button {button_index + 1}",
            color=0x0099ff
        )
        embed.add_field(name="Label", value=button.get('label', 'No label'), inline=False)
        embed.add_field(name="Style", value=button.get('style', 'primary'), inline=True)
        embed.add_field(name="Emoji", value=button.get('emoji', 'None'), inline=True)

        action = button.get('action', {})
        action_desc = f"Type: {action.get('type', 'None')}"
        if action.get('type') in ['send_message', 'custom_response', 'send_dm']:
            action_desc += f"\nMessage: {action.get('message', 'N/A')[:100]}"
        elif action.get('type') in ['give_role', 'remove_role']:
            action_desc += f"\nRole ID: {action.get('role_id', 'N/A')}"

        embed.add_field(name="Action", value=action_desc, inline=False)

        await interaction.response.send_message(embed=embed, view=self, ephemeral=True)

    @discord.ui.button(label="Edit Selected Button", style=discord.ButtonStyle.primary, emoji="✏️")
    async def edit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.selected_button_index is None:
            await interaction.response.send_message("❌ Please select a button first!", ephemeral=True)
            return

        modal = ButtonModal(self.embed_data, self.selected_button_index)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Delete Selected Button", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.selected_button_index is None:
            await interaction.response.send_message("❌ Please select a button first!", ephemeral=True)
            return

        button_label = self.embed_data['buttons'][self.selected_button_index].get('label', f'Button {self.selected_button_index + 1}')
        del self.embed_data['buttons'][self.selected_button_index]

        view = EmbedOptionsView(self.embed_data, self.editing_embed_id)
        await interaction.response.send_message(f"✅ Deleted button '{button_label}'. Continue editing:", view=view, ephemeral=True)

    @discord.ui.button(label="Back to Embed Editor", style=discord.ButtonStyle.secondary, emoji="↩️")
    async def back_to_editor(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = EmbedOptionsView(self.embed_data, self.editing_embed_id)
        await interaction.response.send_message("Back to embed editor:", view=view, ephemeral=True)

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
        if color_str.startswith('0x'):
            color_str = color_str[2:]
        try:
            embed.color = int(color_str, 16)
        except ValueError:
            embed.color = 0x0099ff

    if embed_data.get('footer'):
        embed.set_footer(text=embed_data['footer'])

    if embed_data.get('thumbnail'):
        embed.set_thumbnail(url=embed_data['thumbnail'])

    if embed_data.get('image'):
        embed.set_image(url=embed_data['image'])

    if embed_data.get('author'):
        author = embed_data['author']
        embed.set_author(name=author['name'], icon_url=author.get('icon_url'))

    if embed_data.get('fields'):
        for field in embed_data['fields']:
            embed.add_field(
                name=field['name'],
                value=field['value'],
                inline=field.get('inline', False)
            )

    return embed

def create_embed_button_view(embed_data):
    """Create a view with buttons for an embed"""
    if not embed_data.get('buttons'):
        return None

    class DynamicEmbedView(discord.ui.View):
        def __init__(self, buttons_data):
            super().__init__(timeout=None)  # Persistent view to avoid rate limiting
            self.buttons_data = buttons_data
            self.user_cooldowns = {}  # Track cooldowns per user

            # Add buttons dynamically with rate limiting protection
            for i, button_data in enumerate(buttons_data[:5]):  # Limit to 5 buttons max
                style_map = {
                    'primary': discord.ButtonStyle.primary,
                    'secondary': discord.ButtonStyle.secondary,
                    'success': discord.ButtonStyle.success,
                    'danger': discord.ButtonStyle.danger
                }

                style = style_map.get(button_data.get('style', 'primary'), discord.ButtonStyle.primary)

                # Create button with unique custom_id based on content hash
                button_hash = abs(hash(f"{button_data.get('label', '')}{button_data.get('action', {})}")) % 1000000
                button = discord.ui.Button(
                    label=button_data.get('label', f'Button {i+1}'),
                    style=style,
                    emoji=button_data.get('emoji'),
                    custom_id=f"emb_btn_{i}_{button_hash}"
                )

                # Create callback function
                button.callback = self.create_button_callback(i, button_data.get('action', {}))
                self.add_item(button)

        def create_button_callback(self, button_index, action_data):
            async def button_callback(interaction):
                # Enhanced cooldown check per user
                import time
                current_time = time.time()
                user_id = interaction.user.id

                if user_id in self.user_cooldowns:
                    if current_time - self.user_cooldowns[user_id] < 2:  # 2 second cooldown per user
                        await interaction.response.send_message("⏱️ Please wait a moment before clicking again.", ephemeral=True)
                        return

                self.user_cooldowns[user_id] = current_time

                await self.handle_button_action(interaction, action_data)
            return button_callback

        async def handle_button_action(self, interaction, action_data):
            action_type = action_data.get('type')

            try:
                if action_type == "send_message":
                    message = action_data.get('message', 'Button clicked!')
                    await interaction.response.send_message(message)

                elif action_type == "custom_response":
                    message = action_data.get('message', 'Custom response!')
                    await interaction.response.send_message(message, ephemeral=True)

                elif action_type == "send_dm":
                    message = action_data.get('message', 'Hello from the bot!')
                    try:
                        await interaction.user.send(message)
                        await interaction.response.send_message("✅ Message sent to your DMs!", ephemeral=True)
                    except discord.Forbidden:
                        await interaction.response.send_message("❌ Could not send DM. Please check your privacy settings.", ephemeral=True)

                elif action_type == "play_sound":
                    sound_url = action_data.get('sound_url', '')
                    if sound_url:
                        embed = discord.Embed(
                            title="🔊 Audio Player",
                            description=f"[Click here to play the audio]({sound_url})",
                            color=0x1f8b4c
                        )
                        embed.add_field(name="Audio URL", value=sound_url, inline=False)
                        embed.set_footer(text="Click the link above to play the audio file")
                        await interaction.response.send_message(embed=embed, ephemeral=True)
                    else:
                        await interaction.response.send_message("❌ No sound URL configured for this button!", ephemeral=True)

                else:
                    await interaction.response.send_message("🔘 Button clicked! (No action configured)", ephemeral=True)

            except Exception as e:
                print(f"Error in button action: {e}")
                if not interaction.response.is_done():
                    await interaction.response.send_message("❌ An error occurred while processing the button action.", ephemeral=True)
                else:
                    await interaction.followup.send("❌ An error occurred while processing the button action.", ephemeral=True)

    return DynamicEmbedView(embed_data['buttons'])

class FieldManagerView(discord.ui.View):
    def __init__(self, embed_data, editing_embed_id=None):
        super().__init__(timeout=300)
        self.embed_data = embed_data
        self.editing_embed_id = editing_embed_id
        self.selected_field_index = None

        # Create select menu for fields
        fields = embed_data.get('fields', [])
        options = []
        for i, field in enumerate(fields):
            field_name = field.get('name', f'Field {i+1}')
            field_value = field.get('value', '')
            # Truncate for display
            if len(field_value) > 50:
                field_value = field_value[:47] + "..."

            options.append(discord.SelectOption(
                label=f"{i+1}. {field_name}"[:100],
                value=str(i),
                description=field_value[:100] if field_value else "No value"
            ))

        if options:
            self.select_field.options = options[:25]
        else:
            # Disable select if no fields
            self.select_field.disabled = True

    @discord.ui.select(placeholder="Choose a field to manage...")
    async def select_field(self, interaction: discord.Interaction, select: discord.ui.Select):
        field_index = int(select.values[0])
        self.selected_field_index = field_index

        field = self.embed_data['fields'][field_index]
        embed = discord.Embed(
            title=f"📝 Field {field_index + 1}",
            color=0x0099ff
        )
        embed.add_field(name="Name", value=field.get('name', 'No name'), inline=False)
        embed.add_field(name="Value", value=field.get('value', 'No value'), inline=False)
        embed.add_field(name="Inline", value=str(field.get('inline', False)), inline=False)

        await interaction.response.send_message(embed=embed, view=self, ephemeral=True)

    @discord.ui.button(label="Edit Selected Field", style=discord.ButtonStyle.primary, emoji="✏️")
    async def edit_field(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.selected_field_index is None:
            await interaction.response.send_message("❌ Please select a field first!", ephemeral=True)
            return

        modal = FieldModal(self.embed_data, self.selected_field_index, self.editing_embed_id)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Delete Selected Field", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def delete_field(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.selected_field_index is None:
            await interaction.response.send_message("❌ Please select a field first!", ephemeral=True)
            return

        field_name = self.embed_data['fields'][self.selected_field_index].get('name', f'Field {self.selected_field_index + 1}')
        del self.embed_data['fields'][self.selected_field_index]

        view = EmbedOptionsView(self.embed_data, self.editing_embed_id)
        await interaction.response.send_message(f"✅ Deleted field '{field_name}'. Continue editing:", view=view, ephemeral=True)

    @discord.ui.button(label="Back to Embed Editor", style=discord.ButtonStyle.secondary, emoji="↩️")
    async def back_to_editor(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = EmbedOptionsView(self.embed_data, self.editing_embed_id)
        await interaction.response.send_message("Back to embed editor:", view=view, ephemeral=True)

class EmbedSelectView(discord.ui.View):
    def __init__(self, stored_embeds):
        super().__init__(timeout=300)
        self.stored_embeds = stored_embeds
        self.selected_embed_id = None

        # Create select menu options
        options = []
        for embed_id, embed_data in stored_embeds.items():
            title = embed_data.get('title', 'No title')
            description = embed_data.get('description', '')
            # Truncate description for option description
            if description and len(description) > 100:
                description = description[:97] + "..."

            options.append(discord.SelectOption(
                label=f"{embed_id}: {title}"[:100],  # Discord limit
                value=embed_id,
                description=description[:100] if description else "No description"
            ))

        self.select_embed.options = options[:25]  # Discord limit

    @discord.ui.select(placeholder="Choose an embed to view...")
    async def select_embed(self, interaction: discord.Interaction, select: discord.ui.Select):
        embed_id = select.values[0]
        embed_data = self.stored_embeds[embed_id]
        self.selected_embed_id = embed_id

        # Create preview embed
        preview_embed = create_embed_from_data(embed_data)

        # Add metadata
        info_embed = discord.Embed(
            title=f"📋 Embed Details: {embed_id}",
            color=0x0099ff
        )
        info_embed.add_field(name="Title", value=embed_data.get('title', 'No title'), inline=True)
        info_embed.add_field(name="Fields Count", value=len(embed_data.get('fields', [])), inline=True)
        info_embed.add_field(name="Buttons Count", value=len(embed_data.get('buttons', [])), inline=True)

        await interaction.response.send_message(embeds=[info_embed, preview_embed], view=self, ephemeral=True)

    @discord.ui.button(label="Delete Selected Embed", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def delete_embed(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.selected_embed_id:
            await interaction.response.send_message("❌ Please select an embed first!", ephemeral=True)
            return

        data = load_data()

        if self.selected_embed_id not in data['stored_embeds']:
            await interaction.response.send_message(f"❌ Embed '{self.selected_embed_id}' not found!", ephemeral=True)
            return

        # Get embed title for confirmation message
        embed_title = data['stored_embeds'][self.selected_embed_id].get('title', 'Untitled')

        # Delete the embed
        del data['stored_embeds'][self.selected_embed_id]
        save_data(data)

        await interaction.response.send_message(f"✅ Successfully deleted embed '{self.selected_embed_id}' ({embed_title})", ephemeral=True)

class SpawnEmbedSelectView(discord.ui.View):
    def __init__(self, stored_embeds):
        super().__init__(timeout=300)
        self.stored_embeds = stored_embeds

        # Create select menu options
        options = []
        for embed_id, embed_data in stored_embeds.items():
            title = embed_data.get('title', 'No title')
            description = embed_data.get('description', '')
            # Truncate description for option description
            if description and len(description) > 100:
                description = description[:97] + "..."

            options.append(discord.SelectOption(
                label=f"{embed_id}: {title}"[:100],  # Discord limit
                value=embed_id,
                description=description[:100] if description else "No description"
            ))

        self.select_embed.options = options[:25]  # Discord limit

    @discord.ui.select(placeholder="Choose an embed to spawn...")
    async def select_embed(self, interaction: discord.Interaction, select: discord.ui.Select):
        embed_id = select.values[0]
        embed_data = self.stored_embeds[embed_id]

        # Create the embed
        embed = create_embed_from_data(embed_data)

        # Create button view if buttons exist
        button_view = create_embed_button_view(embed_data) if embed_data.get('buttons') else None

        # Send the embed to the channel with buttons
        await interaction.response.send_message(embed=embed, view=button_view)

class EditEmbedSelectView(discord.ui.View):
    def __init__(self, stored_embeds):
        super().__init__(timeout=300)
        self.stored_embeds = stored_embeds

        # Create select menu options
        options = []
        for embed_id, embed_data in stored_embeds.items():
            title = embed_data.get('title', 'No title')
            description = embed_data.get('description', '')
            # Truncate description for option description
            if description and len(description) > 100:
                description = description[:97] + "..."

            options.append(discord.SelectOption(
                label=f"{embed_id}: {title}"[:100],  # Discord limit
                value=embed_id,
                description=description[:100] if description else "No description"
            ))

        self.select_embed.options = options[:25]  # Discord limit

    @discord.ui.select(placeholder="Choose an embed to edit...")
    async def select_embed(self, interaction: discord.Interaction, select: discord.ui.Select):
        embed_id = select.values[0]
        embed_data = self.stored_embeds[embed_id]

        # Open the edit modal
        modal = EmbedModal(embed_data, embed_id)
        await interaction.response.send_modal(modal)

# Slash Commands
@bot.tree.command(name="create_embed", description="[STAFF ONLY] Create a custom embed message")
async def create_embed(interaction: discord.Interaction):
    try:
        if not interaction.guild_id:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
            return

        # Use verification check
        if not await check_verification(interaction, "create_embed"):
            return

        modal = EmbedModal()
        await interaction.response.send_modal(modal)
    except discord.NotFound as e:
        print(f"NotFound error in create_embed: {e}")
        return
    except discord.HTTPException as e:
        if e.code == 10062:  # Unknown interaction
            print(f"Unknown interaction in create_embed - likely expired")
            return
        else:
            print(f"HTTP Error in create_embed: {e}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("❌ An error occurred.", ephemeral=True)
            except:
                pass
    except Exception as e:
        print(f"Error in create_embed: {e}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred.", ephemeral=True)
        except:
            pass

@bot.tree.command(name="edit_embed", description="[STAFF ONLY] Edit an existing embed")
async def edit_embed(interaction: discord.Interaction):
    try:
        # Simplified guild check - just check if guild_id exists
        if not interaction.guild_id:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
            return

        # Use verification check
        if not await check_verification(interaction, "edit_embed"):
            return

        data = load_data()

        if not data.get('stored_embeds') or len(data['stored_embeds']) == 0:
            await interaction.response.send_message("No embeds stored! Use `/create_embed` to create one first.", ephemeral=True)
            return

        view = EditEmbedSelectView(data['stored_embeds'])
        await interaction.response.send_message(f"**Select Embed to Edit ({len(data['stored_embeds'])} available):**", view=view, ephemeral=True)
    except discord.NotFound as e:
        print(f"NotFound error in edit_embed: {e}")
    except discord.HTTPException as e:
        if e.code == 10062:  # Unknown interaction
            print(f"Unknown interaction in edit_embed - likely expired")
        else:
            print(f"HTTP Error in edit_embed: {e}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("❌ An error occurred.", ephemeral=True)
            except:
                pass
    except Exception as e:
        print(f"Error in edit_embed: {e}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred.", ephemeral=True)
        except:
            pass

@bot.tree.command(name="list_embeds", description="[STAFF ONLY] List all stored embeds")
async def list_embeds(interaction: discord.Interaction):
    try:
        if not interaction.guild_id:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
            return

        # Use verification check
        if not await check_verification(interaction, "list_embeds"):
            return

        data = load_data()

        if not data.get('stored_embeds') or len(data['stored_embeds']) == 0:
            await interaction.response.send_message("No embeds stored! Use `/create_embed` to create one.", ephemeral=True)
            return

        # Create summary embed
        summary_embed = discord.Embed(
            title="📋 Stored Embeds Summary",
            description=f"Total embeds: **{len(data['stored_embeds'])}**",
            color=0x0099ff
        )

        # Add quick summary of each embed
        for embed_id, embed_data in list(data['stored_embeds'].items())[:10]:  # Limit to first 10
            title = embed_data.get('title', 'No title')
            field_count = len(embed_data.get('fields', []))
            button_count = len(embed_data.get('buttons', []))

            summary_embed.add_field(
                name=f"{embed_id}",
                value=f"**Title:** {title[:50]}{'...' if len(title) > 50 else ''}\n**Fields:** {field_count}\n**Buttons:** {button_count}",
                inline=True
            )

        if len(data['stored_embeds']) > 10:
            summary_embed.set_footer(text=f"Showing first 10 of {len(data['stored_embeds'])} embeds. Use the dropdown to see all.")

        view = EmbedSelectView(data['stored_embeds'])
        await interaction.response.send_message(embed=summary_embed, view=view, ephemeral=True)
    except discord.NotFound as e:
        print(f"NotFound error in list_embeds: {e}")
    except discord.HTTPException as e:
        if e.code == 10062:  # Unknown interaction
            print(f"Unknown interaction in list_embeds - likely expired")
        else:
            print(f"HTTP Error in list_embeds: {e}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("❌ An error occurred.", ephemeral=True)
            except:
                pass
    except Exception as e:
        print(f"Error in list_embeds: {e}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred.", ephemeral=True)
        except:
            pass

@bot.tree.command(name="spawnembed", description="[STAFF ONLY] Spawn a stored embed message")
async def spawn_embed(interaction: discord.Interaction):
    try:
        if not interaction.guild_id:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
            return

        # Use verification check
        if not await check_verification(interaction, "spawnembed"):
            return

        data = load_data()

        if not data.get('stored_embeds') or len(data['stored_embeds']) == 0:
            await interaction.response.send_message("No embeds stored! Use `/create_embed` to create one first.", ephemeral=True)
            return

        view = SpawnEmbedSelectView(data['stored_embeds'])
        await interaction.response.send_message(f"**Select Embed to Spawn ({len(data['stored_embeds'])} available):**", view=view, ephemeral=True)
    except Exception as e:
        print(f"Error in spawn_embed: {e}")
        import traceback
        traceback.print_exc()
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred while processing your request.", ephemeral=True)
        except:
            pass

@bot.tree.command(name="delete_embed", description="[STAFF ONLY] Delete a stored embed message")
async def delete_embed(interaction: discord.Interaction, embed_id: str):
    try:
        if not interaction.guild_id:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
            return

        # Use verification check
        if not await check_verification(interaction, "delete_embed"):
            return

        data = load_data()

        if embed_id not in data['stored_embeds']:
            await interaction.response.send_message(f"❌ Embed '{embed_id}' not found!", ephemeral=True)
            return

        # Get embed title for confirmation message
        embed_title = data['stored_embeds'][embed_id].get('title', 'Untitled')

        # Delete the embed
        del data['stored_embeds'][embed_id]
        save_data(data)

        await interaction.response.send_message(f"✅ Successfully deleted embed '{embed_id}' ({embed_title})", ephemeral=True)
    except Exception as e:
        print(f"Error in delete_embed: {e}")
        import traceback
        traceback.print_exc()
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred while processing your request.", ephemeral=True)
        except:
            pass

# Run the bot
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
if TOKEN:
    bot.run(TOKEN)
else:
    print("❌ DISCORD_BOT_TOKEN not found in environment variables")
    print("Please add your Discord bot token to the environment variables.")