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
            if 'automod_words' not in data:
                data['automod_words'] = []
            if 'automod_enabled' not in data:
                data['automod_enabled'] = True
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        default_data = {
            "stored_embeds": {},
            "embed_counter": 1,
            "automod_words": [],
            "automod_enabled": True
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
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash commands")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Auto-moderation
    data = load_data()
    if data.get('automod_enabled', True) and data.get('automod_words'):
        content_lower = message.content.lower()
        for word in data['automod_words']:
            if word.lower() in content_lower:
                try:
                    await message.delete()
                    await message.channel.send(f"{message.author.mention}, your message was removed for containing prohibited content.", delete_after=5)
                    print(f"Auto-deleted message from {message.author}: {message.content}")
                except discord.Forbidden:
                    print(f"No permission to delete message from {message.author}")
                break

    await bot.process_commands(message)

class EmbedModal(discord.ui.Modal, title="Create Embed"):
    def __init__(self, embed_data=None, editing_embed_id=None):
        super().__init__()
        self.embed_data = embed_data or {}
        self.editing_embed_id = editing_embed_id

        # Pre-fill if editing
        self.title_input.default = self.embed_data.get('title', '')
        self.description_input.default = self.embed_data.get('description', '')
        self.color_input.default = self.embed_data.get('color', '')
        self.footer_input.default = self.embed_data.get('footer', '')
        self.thumbnail_input.default = self.embed_data.get('thumbnail', '')

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
        placeholder="e.g., #FF0000 or 0xFF0000",
        max_length=10,
        required=False
    )

    footer_input = discord.ui.TextInput(
        label="Footer Text",
        placeholder="Enter footer text...",
        max_length=2048,
        required=False
    )

    thumbnail_input = discord.ui.TextInput(
        label="Thumbnail URL",
        placeholder="Enter image URL for thumbnail...",
        max_length=2048,
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        embed_data = {
            'title': str(self.title_input.value) if self.title_input.value else None,
            'description': str(self.description_input.value) if self.description_input.value else None,
            'color': str(self.color_input.value) if self.color_input.value else None,
            'footer': str(self.footer_input.value) if self.footer_input.value else None,
            'thumbnail': str(self.thumbnail_input.value) if self.thumbnail_input.value else None,
            'fields': self.embed_data.get('fields', []),
            'image': self.embed_data.get('image'),
            'author': self.embed_data.get('author')
        }

        view = EmbedOptionsView(embed_data, self.editing_embed_id)
        action_text = "updated" if self.editing_embed_id else "created"
        await interaction.response.send_message(f"Embed {action_text}! Choose additional options:", view=view, ephemeral=True)

class FieldModal(discord.ui.Modal, title="Add Field"):
    def __init__(self, embed_data, field_index=None):
        super().__init__()
        self.embed_data = embed_data
        self.field_index = field_index

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
        else:
            self.embed_data['fields'].append(field_data)

        view = EmbedOptionsView(self.embed_data)
        await interaction.response.send_message("Field added! Continue editing:", view=view, ephemeral=True)

class EmbedOptionsView(discord.ui.View):
    def __init__(self, embed_data, editing_embed_id=None):
        super().__init__(timeout=300)
        self.embed_data = embed_data
        self.editing_embed_id = editing_embed_id

    @discord.ui.button(label="Add Field", style=discord.ButtonStyle.primary, emoji="📝")
    async def add_field(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = FieldModal(self.embed_data)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Manage Fields", style=discord.ButtonStyle.secondary, emoji="📋")
    async def manage_fields(self, interaction: discord.Interaction, button: discord.ui.Button):
        fields = self.embed_data.get('fields', [])
        if not fields:
            await interaction.response.send_message("No fields to manage! Add a field first.", ephemeral=True)
            return

        view = FieldManagerView(self.embed_data, self.editing_embed_id)
        await interaction.response.send_message("**Field Manager:**\nSelect a field to edit or delete:", view=view, ephemeral=True)

    @discord.ui.button(label="Add Image", style=discord.ButtonStyle.secondary, emoji="🖼️")
    async def add_image(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = ImageModal(self.embed_data)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Add Author", style=discord.ButtonStyle.secondary, emoji="👤")
    async def add_author(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = AuthorModal(self.embed_data)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Preview", style=discord.ButtonStyle.secondary, emoji="👁️")
    async def preview_embed(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = create_embed_from_data(self.embed_data)
        await interaction.response.send_message("**Preview:**", embed=embed, ephemeral=True)

    @discord.ui.button(label="Save Changes", style=discord.ButtonStyle.primary, emoji="💾")
    async def save_changes(self, interaction: discord.Interaction, button: discord.ui.Button):
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

    @discord.ui.button(label="Send Embed", style=discord.ButtonStyle.success, emoji="✅")
    async def send_embed(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = create_embed_from_data(self.embed_data)

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

        await interaction.response.send_message(f"Embed {action_text}! (ID: {embed_id})", ephemeral=True)
        await interaction.followup.send(embed=embed)

class ImageModal(discord.ui.Modal, title="Add Image"):
    def __init__(self, embed_data):
        super().__init__()
        self.embed_data = embed_data

        self.image_url.default = embed_data.get('image', '')

    image_url = discord.ui.TextInput(
        label="Image URL",
        placeholder="Enter image URL...",
        max_length=2048,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        self.embed_data['image'] = str(self.image_url.value)
        view = EmbedOptionsView(self.embed_data)
        await interaction.response.send_message("Image added! Continue editing:", view=view, ephemeral=True)

class AuthorModal(discord.ui.Modal, title="Add Author"):
    def __init__(self, embed_data):
        super().__init__()
        self.embed_data = embed_data

        author = embed_data.get('author', {})
        self.author_name.default = author.get('name', '')
        self.author_icon.default = author.get('icon_url', '')

    author_name = discord.ui.TextInput(
        label="Author Name",
        placeholder="Enter author name...",
        max_length=256,
        required=True
    )

    author_icon = discord.ui.TextInput(
        label="Author Icon URL",
        placeholder="Enter icon URL...",
        max_length=2048,
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        self.embed_data['author'] = {
            'name': str(self.author_name.value),
            'icon_url': str(self.author_icon.value) if self.author_icon.value else None
        }
        view = EmbedOptionsView(self.embed_data)
        await interaction.response.send_message("Author added! Continue editing:", view=view, ephemeral=True)

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

class FieldManagerView(discord.ui.View):
    def __init__(self, embed_data, editing_embed_id=None):
        super().__init__(timeout=300)
        self.embed_data = embed_data
        self.editing_embed_id = editing_embed_id

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
        if not hasattr(self, 'selected_field_index'):
            await interaction.response.send_message("❌ Please select a field first!", ephemeral=True)
            return

        modal = FieldModal(self.embed_data, self.selected_field_index)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Delete Selected Field", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def delete_field(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not hasattr(self, 'selected_field_index'):
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

        # Send the embed to the channel
        await interaction.response.send_message(embed=embed)

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

# Application System Classes and Commands

class ApplicationCreateModal(discord.ui.Modal, title="Create Application Panel"):
    def __init__(self):
        super().__init__()

    app_name = discord.ui.TextInput(
        label="Application Name",
        placeholder="e.g., 'Staff Application', 'Member Application'",
        max_length=100,
        required=True
    )

    app_description = discord.ui.TextInput(
        label="Application Description",
        placeholder="Brief description of what this application is for...",
        style=discord.TextStyle.paragraph,
        max_length=500,
        required=True
    )

    button_text = discord.ui.TextInput(
        label="Button Text",
        placeholder="e.g., 'Apply for Staff', 'Join Us'",
        max_length=80,
        required=False
    )

    staff_channel_id = discord.ui.TextInput(
        label="Staff Channel ID (optional)",
        placeholder="Channel ID where applications will be sent",
        max_length=20,
        required=False
    )

    member_role_id = discord.ui.TextInput(
        label="Auto-assign Role ID (optional)",
        placeholder="Role ID to assign when accepted",
        max_length=20,
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        data = load_data()

        # Initialize custom applications if not exists
        if 'custom_applications' not in data:
            data['custom_applications'] = {}
        if 'app_panel_counter' not in data:
            data['app_panel_counter'] = 1

        app_id = f"app_panel_{data['app_panel_counter']}"

        app_panel_data = {
            'name': str(self.app_name.value),
            'description': str(self.app_description.value),
            'button_text': str(self.button_text.value) if self.button_text.value else f"Apply for {self.app_name.value}",
            'staff_channel_id': int(self.staff_channel_id.value) if self.staff_channel_id.value and self.staff_channel_id.value.isdigit() else None,
            'member_role_id': int(self.member_role_id.value) if self.member_role_id.value and self.member_role_id.value.isdigit() else None,
            'fields': [],
            'created_by': interaction.user.id,
            'created_at': datetime.now().isoformat(),
            'applications': {}
        }

        data['custom_applications'][app_id] = app_panel_data
        data['app_panel_counter'] += 1
        save_data(data)

        view = ApplicationFieldsView(app_id)
        await interaction.response.send_message(f"✅ Application panel '{self.app_name.value}' created! (ID: {app_id})\n\nNow add fields to your application form:", view=view, ephemeral=True)

class ApplicationFieldModal(discord.ui.Modal, title="Add Application Field"):
    def __init__(self, app_id):
        super().__init__()
        self.app_id = app_id

    field_label = discord.ui.TextInput(
        label="Field Label",
        placeholder="e.g., 'Experience', 'Age', 'Timezone'",
        max_length=45,
        required=True
    )

    field_placeholder = discord.ui.TextInput(
        label="Field Placeholder",
        placeholder="Placeholder text for this field...",
        max_length=100,
        required=False
    )

    field_type = discord.ui.TextInput(
        label="Field Type",
        placeholder="short (single line) or long (paragraph)",
        max_length=10,
        required=False
    )

    max_length = discord.ui.TextInput(
        label="Max Length",
        placeholder="Maximum characters (default: 1000)",
        max_length=4,
        required=False
    )

    required = discord.ui.TextInput(
        label="Required",
        placeholder="true or false (default: true)",
        max_length=5,
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        data = load_data()

        if self.app_id not in data.get('custom_applications', {}):
            await interaction.response.send_message("❌ Application panel not found!", ephemeral=True)
            return

        field_type = self.field_type.value.lower() if self.field_type.value else "short"
        max_len = int(self.max_length.value) if self.max_length.value and self.max_length.value.isdigit() else 1000
        is_required = self.required.value.lower() != "false" if self.required.value else True

        field_data = {
            'label': str(self.field_label.value),
            'placeholder': str(self.field_placeholder.value) if self.field_placeholder.value else f"Enter {self.field_label.value.lower()}...",
            'type': 'paragraph' if field_type in ['long', 'paragraph'] else 'short',
            'max_length': min(max_len, 4000),
            'required': is_required
        }

        data['custom_applications'][self.app_id]['fields'].append(field_data)
        save_data(data)

        view = ApplicationFieldsView(self.app_id)
        await interaction.response.send_message(f"✅ Field '{self.field_label.value}' added! Continue managing fields:", view=view, ephemeral=True)

class ApplicationFieldsView(discord.ui.View):
    def __init__(self, app_id):
        super().__init__(timeout=300)
        self.app_id = app_id

    @discord.ui.button(label="Add Field", style=discord.ButtonStyle.primary, emoji="➕")
    async def add_field(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_data()
        app_data = data.get('custom_applications', {}).get(self.app_id)

        if not app_data:
            await interaction.response.send_message("❌ Application panel not found!", ephemeral=True)
            return

        if len(app_data.get('fields', [])) >= 5:
            await interaction.response.send_message("❌ Maximum 5 fields allowed per application!", ephemeral=True)
            return

        modal = ApplicationFieldModal(self.app_id)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Preview Panel", style=discord.ButtonStyle.secondary, emoji="👁️")
    async def preview_panel(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_data()
        app_data = data.get('custom_applications', {}).get(self.app_id)

        if not app_data:
            await interaction.response.send_message("❌ Application panel not found!", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"📋 {app_data['name']} - Application Panel",
            description=app_data['description'],
            color=0x0099ff,
            timestamp=datetime.now()
        )

        if app_data.get('fields'):
            field_list = "\n".join([f"• {field['label']} ({'Required' if field['required'] else 'Optional'})" for field in app_data['fields']])
            embed.add_field(name="📝 Application Fields", value=field_list, inline=False)
        else:
            embed.add_field(name="⚠️ No Fields", value="Add at least one field before deploying this panel.", inline=False)

        embed.set_footer(text="Application Panel Preview")

        preview_view = CustomApplicationPanelView(self.app_id)
        await interaction.response.send_message("**Preview:**", embed=embed, view=preview_view, ephemeral=True)

    @discord.ui.button(label="Deploy Panel", style=discord.ButtonStyle.success, emoji="🚀")
    async def deploy_panel(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_data()
        app_data = data.get('custom_applications', {}).get(self.app_id)

        if not app_data:
            await interaction.response.send_message("❌ Application panel not found!", ephemeral=True)
            return

        if not app_data.get('fields'):
            await interaction.response.send_message("❌ Please add at least one field before deploying!", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"📋 {app_data['name']} - Application Panel",
            description=app_data['description'],
            color=0x0099ff,
            timestamp=datetime.now()
        )

        embed.add_field(
            name="📝 How to Apply",
            value=f"Click the **{app_data['button_text']}** button below to start your application.",
            inline=False
        )

        field_list = "\n".join([f"• {field['label']}" for field in app_data['fields']])
        embed.add_field(name="📋 Application Fields", value=field_list, inline=False)

        embed.set_footer(text="Custom Application System")

        if interaction.guild and interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)

        view = CustomApplicationPanelView(self.app_id)

        await interaction.response.send_message(f"✅ Application panel '{app_data['name']}' deployed!", ephemeral=True)
        await interaction.followup.send(embed=embed, view=view)

class CustomApplicationPanelView(discord.ui.View):
    def __init__(self, app_id):
        super().__init__(timeout=None)
        self.app_id = app_id

        # Update button label
        data = load_data()
        app_data = data.get('custom_applications', {}).get(app_id, {})
        if app_data.get('button_text'):
            for item in self.children:
                if hasattr(item, 'label'):
                    item.label = app_data['button_text']

    @discord.ui.button(label="Apply", style=discord.ButtonStyle.primary, emoji="📝")
    async def apply_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_data()
        app_data = data.get('custom_applications', {}).get(self.app_id)

        if not app_data:
            await interaction.response.send_message("❌ Application panel not found!", ephemeral=True)
            return

        # Check if user already has a pending application for this panel
        user_applications = [app for app in app_data.get('applications', {}).values() 
                           if app['user_id'] == interaction.user.id and app['status'] == 'pending']

        if user_applications:
            await interaction.response.send_message(f"❌ You already have a pending application for {app_data['name']}! Please wait for it to be reviewed.", ephemeral=True)
            return

        modal = DynamicApplicationModal(self.app_id, app_data)
        await interaction.response.send_modal(modal)

class DynamicApplicationModal(discord.ui.Modal):
    def __init__(self, app_id, app_data):
        super().__init__(title=f"{app_data['name']} Application")
        self.app_id = app_id
        self.app_data = app_data

        # Add fields dynamically
        for i, field in enumerate(app_data.get('fields', [])[:5]):  # Discord limit of 5 components
            text_input = discord.ui.TextInput(
                label=field['label'],
                placeholder=field['placeholder'],
                style=discord.TextStyle.paragraph if field['type'] == 'paragraph' else discord.TextStyle.short,
                max_length=field['max_length'],
                required=field['required']
            )
            setattr(self, f'field_{i}', text_input)
            self.add_item(text_input)

    async def on_submit(self, interaction: discord.Interaction):
        data = load_data()

        if 'application_counter' not in data:
            data['application_counter'] = 1

        application_id = f"app_{data['application_counter']}"

        # Collect field responses
        responses = {}
        for i, field in enumerate(self.app_data.get('fields', [])):
            if hasattr(self, f'field_{i}'):
                responses[field['label']] = str(getattr(self, f'field_{i}').value)

        application_data = {
            'user_id': interaction.user.id,
            'responses': responses,
            'status': 'pending',
            'submitted_at': datetime.now().isoformat(),
            'reviewed_by': None,
            'review_notes': None
        }

        data['custom_applications'][self.app_id]['applications'][application_id] = application_data
        data['application_counter'] += 1
        save_data(data)

        # Create confirmation embed
        confirm_embed = discord.Embed(
            title="✅ Application Submitted Successfully!",
            description=f"Thank you for applying for {self.app_data['name']}, {interaction.user.mention}!",
            color=0x00ff00,
            timestamp=datetime.now()
        )
        confirm_embed.add_field(name="Application ID", value=application_id, inline=True)
        confirm_embed.add_field(name="Status", value="Pending Review", inline=True)
        confirm_embed.set_footer(text="Custom Application System")

        await interaction.response.send_message(embed=confirm_embed, ephemeral=True)

        # Send notification to staff channel if configured
        if self.app_data.get('staff_channel_id'):
            staff_channel = interaction.guild.get_channel(self.app_data['staff_channel_id'])
            if staff_channel:
                staff_embed = discord.Embed(
                    title=f"📋 New {self.app_data['name']} Application",
                    description=f"**Applicant:** {interaction.user.mention}\n**Application ID:** {application_id}",
                    color=0x0099ff,
                    timestamp=datetime.now()
                )

                for field_name, response in responses.items():
                    staff_embed.add_field(
                        name=field_name,
                        value=response[:100] + "..." if len(response) > 100 else response,
                        inline=False
                    )

                review_view = CustomApplicationReviewView(self.app_id, application_id)
                await staff_channel.send(embed=staff_embed, view=review_view)

class CustomApplicationReviewView(discord.ui.View):
    def __init__(self, app_id, application_id):
        super().__init__(timeout=300)
        self.app_id = app_id
        self.application_id = application_id

    @discord.ui.button(label="✅ Accept Application", style=discord.ButtonStyle.success, emoji="✅")
    async def accept_application(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = CustomApplicationReviewModal(self.app_id, self.application_id, "accepted")
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="❌ Reject Application", style=discord.ButtonStyle.danger, emoji="❌")
    async def reject_application(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = CustomApplicationReviewModal(self.app_id, self.application_id, "rejected")
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="📝 Add Private Notes", style=discord.ButtonStyle.secondary, emoji="📝")
    async def add_notes(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Quick way to add notes without making a decision
        modal = discord.ui.Modal(title="Add Review Notes")
        
        notes_input = discord.ui.TextInput(
            label="Private Notes",
            placeholder="Add any private notes about this application...",
            style=discord.TextStyle.paragraph,
            max_length=1000,
            required=False
        )
        modal.add_item(notes_input)
        
        async def notes_submit(modal_interaction):
            data = load_data()
            app_data = data.get('custom_applications', {}).get(self.app_id)
            if app_data and self.application_id in app_data.get('applications', {}):
                if 'private_notes' not in app_data['applications'][self.application_id]:
                    app_data['applications'][self.application_id]['private_notes'] = []
                
                note_entry = {
                    'note': str(notes_input.value),
                    'author': modal_interaction.user.id,
                    'timestamp': datetime.now().isoformat()
                }
                app_data['applications'][self.application_id]['private_notes'].append(note_entry)
                save_data(data)
                
                await modal_interaction.response.send_message(f"✅ Private note added to application {self.application_id}", ephemeral=True)
            else:
                await modal_interaction.response.send_message("❌ Application not found!", ephemeral=True)
        
        modal.on_submit = notes_submit
        await interaction.response.send_modal(modal)

class CustomApplicationReviewModal(discord.ui.Modal, title="Review Application"):
    def __init__(self, app_id, application_id, decision):
        super().__init__()
        self.app_id = app_id
        self.application_id = application_id
        self.decision = decision
        self.title = f"{'Accept' if decision == 'accepted' else 'Reject'} Application"

    review_notes = discord.ui.TextInput(
        label="Review Notes",
        placeholder="Add any notes about this decision...",
        style=discord.TextStyle.paragraph,
        max_length=1000,
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        # Check if interaction.guild is available
        if interaction.guild is None:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
            return

        data = load_data()

        app_data = data.get('custom_applications', {}).get(self.app_id)
        if not app_data or self.application_id not in app_data.get('applications', {}):
            await interaction.response.send_message("❌ Application not found!", ephemeral=True)
            return

        application = app_data['applications'][self.application_id]
        application['status'] = self.decision
        application['reviewed_by'] = interaction.user.id
        application['review_notes'] = str(self.review_notes.value) if self.review_notes.value else None
        application['reviewed_at'] = datetime.now().isoformat()

        save_data(data)

        # Notify the applicant
        applicant = interaction.guild.get_member(application['user_id'])
        if applicant:
            status_color = 0x00ff00 if self.decision == "accepted" else 0xff0000
            status_emoji = "✅" if self.decision == "accepted" else "❌"

            dm_embed = discord.Embed(
                title=f"{status_emoji} {app_data['name']} Application {self.decision.title()}",
                description=f"Your application for {app_data['name']} has been **{self.decision}**.",
                color=status_color,
                timestamp=datetime.now()
            )

            if self.review_notes.value:
                dm_embed.add_field(name="Review Notes", value=self.review_notes.value, inline=False)

            dm_embed.set_footer(text="Custom Application System")

            try:
                await applicant.send(embed=dm_embed)
            except discord.Forbidden:
                pass

            # If accepted, add role if configured
            if self.decision == "accepted" and app_data.get('member_role_id'):
                role = interaction.guild.get_role(app_data['member_role_id'])
                if role:
                    try:
                        await applicant.add_roles(role)
                    except discord.Forbidden:
                        pass

        await interaction.response.send_message(f"✅ Application {self.decision}! Applicant has been notified.", ephemeral=True)

class RIAApplicationModal(discord.ui.Modal, title="RIA Application Form"):
    def __init__(self):
        super().__init__()

    username = discord.ui.TextInput(
        label="Discord Username",
        placeholder="Your Discord username...",
        max_length=100,
        required=True
    )

    age = discord.ui.TextInput(
        label="Age",
        placeholder="Your age...",
        max_length=3,
        required=True
    )

    experience = discord.ui.TextInput(
        label="Previous Experience",
        placeholder="Describe your previous experience with similar communities...",
        style=discord.TextStyle.paragraph,
        max_length=1000,
        required=True
    )

    motivation = discord.ui.TextInput(
        label="Why do you want to join RIA?",
        placeholder="Tell us why you're interested in joining RIA...",
        style=discord.TextStyle.paragraph,
        max_length=1000,
        required=True
    )

    availability = discord.ui.TextInput(
        label="Availability",
        placeholder="What times/days are you typically available?",
        style=discord.TextStyle.paragraph,
        max_length=500,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        data = load_data()

        # Initialize RIA applications if not exists
        if 'ria_applications' not in data:
            data['ria_applications'] = {}
        if 'ria_application_counter' not in data:
            data['ria_application_counter'] = 1

        application_id = f"ria_app_{data['ria_application_counter']}"

        application_data = {
            'user_id': interaction.user.id,
            'username': str(self.username.value),
            'age': str(self.age.value),
            'experience': str(self.experience.value),
            'motivation': str(self.motivation.value),
            'availability': str(self.availability.value),
            'status': 'pending',
            'submitted_at': datetime.now().isoformat(),
            'reviewed_by': None,
            'review_notes': None
        }

        data['ria_applications'][application_id] = application_data
        data['ria_application_counter'] += 1
        save_data(data)

        # Create confirmation embed
        confirm_embed = discord.Embed(
            title="✅ Application Submitted Successfully!",
            description=f"Thank you for applying to join RIA, {interaction.user.mention}!",
            color=0x00ff00,
            timestamp=datetime.now()
        )
        confirm_embed.add_field(name="Application ID", value=application_id, inline=True)
        confirm_embed.add_field(name="Status", value="Pending Review", inline=True)
        confirm_embed.add_field(name="Next Steps", value="Our team will review your application and get back to you soon!", inline=False)
        confirm_embed.set_footer(text="RIA Application System")

        await interaction.response.send_message(embed=confirm_embed, ephemeral=True)

        # Send notification to staff channel (if configured)
        if data.get('ria_settings', {}).get('staff_channel_id'):
            staff_channel = interaction.guild.get_channel(data['ria_settings']['staff_channel_id'])
            if staff_channel:
                staff_embed = discord.Embed(
                    title="📋 New RIA Application",
                    description=f"**Applicant:** {interaction.user.mention}\n**Application ID:** {application_id}",
                    color=0x0099ff,
                    timestamp=datetime.now()
                )
                staff_embed.add_field(name="Username", value=self.username.value, inline=True)
                staff_embed.add_field(name="Age", value=self.age.value, inline=True)
                staff_embed.add_field(name="Experience", value=self.experience.value[:100] + "..." if len(self.experience.value) > 100 else self.experience.value, inline=False)

                review_view = RIAApplicationReviewView(application_id)
                await staff_channel.send(embed=staff_embed, view=review_view)

class RIAApplicationReviewView(discord.ui.View):
    def __init__(self, application_id):
        super().__init__(timeout=300)
        self.application_id = application_id

    @discord.ui.button(label="✅ Accept Application", style=discord.ButtonStyle.success, emoji="✅")
    async def accept_application(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = RIAReviewModal(self.application_id, "accepted")
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="❌ Reject Application", style=discord.ButtonStyle.danger, emoji="❌")
    async def reject_application(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = RIAReviewModal(self.application_id, "rejected")
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="📝 Add Private Notes", style=discord.ButtonStyle.secondary, emoji="📝")
    async def add_notes(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Quick way to add notes without making a decision
        modal = discord.ui.Modal(title="Add Review Notes")
        
        notes_input = discord.ui.TextInput(
            label="Private Notes",
            placeholder="Add any private notes about this application...",
            style=discord.TextStyle.paragraph,
            max_length=1000,
            required=False
        )
        modal.add_item(notes_input)
        
        async def notes_submit(modal_interaction):
            data = load_data()
            if self.application_id in data.get('ria_applications', {}):
                if 'private_notes' not in data['ria_applications'][self.application_id]:
                    data['ria_applications'][self.application_id]['private_notes'] = []
                
                note_entry = {
                    'note': str(notes_input.value),
                    'author': modal_interaction.user.id,
                    'timestamp': datetime.now().isoformat()
                }
                data['ria_applications'][self.application_id]['private_notes'].append(note_entry)
                save_data(data)
                
                await modal_interaction.response.send_message(f"✅ Private note added to application {self.application_id}", ephemeral=True)
            else:
                await modal_interaction.response.send_message("❌ Application not found!", ephemeral=True)
        
        modal.on_submit = notes_submit
        await interaction.response.send_modal(modal)

class RIAReviewModal(discord.ui.Modal, title="Review RIA Application"):
    def __init__(self, application_id, decision):
        super().__init__()
        self.application_id = application_id
        self.decision = decision
        self.title = f"{'Accept' if decision == 'accepted' else 'Reject'} Application"

    review_notes = discord.ui.TextInput(
        label="Review Notes",
        placeholder="Add any notes about this decision...",
        style=discord.TextStyle.paragraph,
        max_length=1000,
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        # Check if interaction.guild is available
        if interaction.guild is None:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
            return

        data = load_data()

        if self.application_id not in data.get('ria_applications', {}):
            await interaction.response.send_message("❌ Application not found!", ephemeral=True)
            return

        app_data = data['ria_applications'][self.application_id]
        app_data['status'] = self.decision
        app_data['reviewed_by'] = interaction.user.id
        app_data['review_notes'] = str(self.review_notes.value) if self.review_notes.value else None
        app_data['reviewed_at'] = datetime.now().isoformat()

        save_data(data)

        # Notify the applicant
        applicant = interaction.guild.get_member(app_data['user_id'])
        if applicant:
            if self.decision == "accepted":
                # Custom RIA welcome message
                dm_embed = discord.Embed(
                    title="🎉 Welcome to RIA! 🎉",
                    description="We're glad to have you! To show your loyalty and represent the crew, please make sure to:\n\n🏳️ Set your flag to PURPLE 🏳️\n\nThis helps us recognize each other in the streets. Stay active, respect the crew, and enjoy the vibes!\n\n— RIA Leadership 💜",
                    color=0x800080,  # Purple color
                    timestamp=datetime.now()
                )
                dm_embed.set_footer(text="RIA Application System")
                
                # Add the RIA role (ID: 1409683503100067951)
                ria_role = interaction.guild.get_role(1409683503100067951)
                if ria_role:
                    try:
                        await applicant.add_roles(ria_role)
                    except discord.Forbidden:
                        pass
                
                # Also add configured member role if set
                if data.get('ria_settings', {}).get('member_role_id'):
                    role = interaction.guild.get_role(data['ria_settings']['member_role_id'])
                    if role:
                        try:
                            await applicant.add_roles(role)
                        except discord.Forbidden:
                            pass
            else:
                # Rejection message
                dm_embed = discord.Embed(
                    title="❌ RIA Application Rejected",
                    description=f"Your application to join RIA has been **{self.decision}**.",
                    color=0xff0000,
                    timestamp=datetime.now()
                )
                dm_embed.set_footer(text="RIA Application System")

            if self.review_notes.value:
                dm_embed.add_field(name="Review Notes", value=self.review_notes.value, inline=False)

            try:
                await applicant.send(embed=dm_embed)
            except discord.Forbidden:
                # If can't DM, mention in the current channel
                await interaction.followup.send(f"{applicant.mention} Your RIA application has been **{self.decision}**.", ephemeral=True)

        await interaction.response.send_message(f"✅ Application {self.decision}! Applicant has been notified.", ephemeral=True)

class RIAApplicationPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Apply to Join RIA", style=discord.ButtonStyle.primary, emoji="📝")
    async def apply_to_ria(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_data()

        # Check if user already has a pending application
        user_applications = [app for app in data.get('ria_applications', {}).values() 
                           if app['user_id'] == interaction.user.id and app['status'] == 'pending']

        if user_applications:
            await interaction.response.send_message("❌ You already have a pending application! Please wait for it to be reviewed.", ephemeral=True)
            return

        modal = RIAApplicationModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Check Application Status", style=discord.ButtonStyle.secondary, emoji="📊")
    async def check_status(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_data()

        user_applications = [app for app_id, app in data.get('ria_applications', {}).items() 
                           if app['user_id'] == interaction.user.id]

        if not user_applications:
            await interaction.response.send_message("❌ You don't have any applications on file.", ephemeral=True)
            return

        # Show the most recent application
        latest_app = max(user_applications, key=lambda x: x['submitted_at'])

        status_colors = {'pending': 0xffff00, 'accepted': 0x00ff00, 'rejected': 0xff0000}
        status_emoji = {'pending': '⏳', 'accepted': '✅', 'rejected': '❌'}

        embed = discord.Embed(
            title="📊 Your RIA Application Status",
            color=status_colors.get(latest_app['status'], 0x0099ff),
            timestamp=datetime.fromisoformat(latest_app['submitted_at'])
        )

        embed.add_field(name="Status", value=f"{status_emoji.get(latest_app['status'], '❓')} {latest_app['status'].title()}", inline=True)
        embed.add_field(name="Submitted", value=latest_app['submitted_at'][:10], inline=True)

        if latest_app.get('reviewed_at'):
            embed.add_field(name="Reviewed", value=latest_app['reviewed_at'][:10], inline=True)

        if latest_app.get('review_notes'):
            embed.add_field(name="Review Notes", value=latest_app['review_notes'], inline=False)

        embed.set_footer(text="RIA Application System")

        await interaction.response.send_message(embed=embed, ephemeral=True)

# Slash Commands
@bot.tree.command(name="create_embed", description="Create a custom embed message")
async def create_embed(interaction: discord.Interaction):
    try:
        if interaction.response.is_done():
            return

        modal = EmbedModal()
        await interaction.response.send_modal(modal)
    except discord.NotFound:
        # Interaction expired, ignore silently
        pass
    except Exception as e:
        print(f"Error in create_embed: {e}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred while processing your request.", ephemeral=True)
        except:
            pass

@bot.tree.command(name="edit_embed", description="Edit an existing embed")
async def edit_embed(interaction: discord.Interaction):
    try:
        if interaction.response.is_done():
            return

        data = load_data()

        if not data.get('stored_embeds') or len(data['stored_embeds']) == 0:
            await interaction.response.send_message("No embeds stored! Use `/create_embed` to create one first.", ephemeral=True)
            return

        view = EditEmbedSelectView(data['stored_embeds'])
        await interaction.response.send_message(f"**Select Embed to Edit ({len(data['stored_embeds'])} available):**", view=view, ephemeral=True)
    except discord.NotFound:
        # Interaction expired, ignore silently
        pass
    except Exception as e:
        print(f"Error in edit_embed: {e}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred while processing your request.", ephemeral=True)
        except:
            pass

@bot.tree.command(name="list_embeds", description="List all stored embeds")
async def list_embeds(interaction: discord.Interaction):
    try:
        if interaction.response.is_done():
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

            summary_embed.add_field(
                name=f"{embed_id}",
                value=f"**Title:** {title[:50]}{'...' if len(title) > 50 else ''}\n**Fields:** {field_count}",
                inline=True
            )

        if len(data['stored_embeds']) > 10:
            summary_embed.set_footer(text=f"Showing first 10 of {len(data['stored_embeds'])} embeds. Use the dropdown to see all.")

        view = EmbedSelectView(data['stored_embeds'])
        await interaction.response.send_message(embed=summary_embed, view=view, ephemeral=True)
    except discord.NotFound:
        # Interaction expired, ignore silently
        pass
    except Exception as e:
        print(f"Error in list_embeds: {e}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred while processing your request.", ephemeral=True)
        except:
            pass

@bot.tree.command(name="spawnembed", description="Spawn a stored embed message")
async def spawn_embed(interaction: discord.Interaction):
    try:
        if interaction.response.is_done():
            return

        data = load_data()

        if not data.get('stored_embeds') or len(data['stored_embeds']) == 0:
            await interaction.response.send_message("No embeds stored! Use `/create_embed` to create one first.", ephemeral=True)
            return

        view = SpawnEmbedSelectView(data['stored_embeds'])
        await interaction.response.send_message(f"**Select Embed to Spawn ({len(data['stored_embeds'])} available):**", view=view, ephemeral=True)
    except discord.NotFound:
        # Interaction expired, ignore
        pass
    except Exception as e:
        print(f"Error in spawn_embed: {e}")

@bot.tree.command(name="delete_embed", description="Delete a stored embed message")
async def delete_embed(interaction: discord.Interaction, embed_id: str):
    try:
        if interaction.response.is_done():
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
    except discord.NotFound:
        # Interaction expired, ignore silently
        pass
    except Exception as e:
        print(f"Error in delete_embed: {e}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred while processing your request.", ephemeral=True)
        except:
            pass

@bot.tree.command(name="automod", description="Manage auto-moderation settings")
async def automod(interaction: discord.Interaction, action: str, word: str = None):
    try:
        if interaction.response.is_done():
            return

        data = load_data()

        if action.lower() == "add" and word:
            if word.lower() not in [w.lower() for w in data['automod_words']]:
                data['automod_words'].append(word)
                save_data(data)
                await interaction.response.send_message(f"✅ Added '{word}' to auto-mod list", ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ '{word}' is already in the auto-mod list", ephemeral=True)

        elif action.lower() == "remove" and word:
            original_length = len(data['automod_words'])
            data['automod_words'] = [w for w in data['automod_words'] if w.lower() != word.lower()]
            if len(data['automod_words']) < original_length:
                save_data(data)
                await interaction.response.send_message(f"✅ Removed '{word}' from auto-mod list", ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ '{word}' was not found in the auto-mod list", ephemeral=True)

        elif action.lower() == "list":
            if data['automod_words']:
                word_list = "\n".join([f"• {word}" for word in data['automod_words']])
                embed = discord.Embed(
                    title="🛡️ Auto-Mod Word List",
                    description=word_list,
                    color=0xff0000
                )
            else:
                embed = discord.Embed(
                    title="🛡️ Auto-Mod Word List",
                    description="No words in the auto-mod list",
                    color=0xff0000
                )
            embed.add_field(name="Status", value="Enabled" if data['automod_enabled'] else "Disabled", inline=True)
            await interaction.response.send_message(embed=embed, ephemeral=True)

        elif action.lower() == "toggle":
            data['automod_enabled'] = not data['automod_enabled']
            save_data(data)
            status = "enabled" if data['automod_enabled'] else "disabled"
            await interaction.response.send_message(f"✅ Auto-moderation {status}", ephemeral=True)

        else:
            await interaction.response.send_message("❌ Invalid action! Use: add, remove, list, or toggle", ephemeral=True)
    except discord.NotFound:
        # Interaction expired, ignore silently
        pass
    except Exception as e:
        print(f"Error in automod: {e}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred while processing your request.", ephemeral=True)
        except:
            pass

@bot.tree.command(name="spawnapplication", description="Spawn an application panel from available panels")
async def spawn_application(interaction: discord.Interaction):
    try:
        if interaction.response.is_done():
            return

        data = load_data()
        
        # Get all available application panels
        available_panels = []
        
        # Add custom application panels
        for app_id, app_data in data.get('custom_applications', {}).items():
            available_panels.append({
                'id': app_id,
                'name': app_data['name'],
                'description': app_data['description'],
                'type': 'custom'
            })
        
        # Add RIA panel as an option
        available_panels.append({
            'id': 'ria_panel',
            'name': 'RIA Application',
            'description': 'Join the RIA community - recruitment application',
            'type': 'ria'
        })

        if not available_panels:
            await interaction.response.send_message("❌ No application panels available! Use `/applicationcreate` to create one first.", ephemeral=True)
            return

        view = SpawnApplicationSelectView(available_panels)
        await interaction.response.send_message(f"**Select Application Panel to Spawn ({len(available_panels)} available):**", view=view, ephemeral=True)
    except discord.NotFound:
        # Interaction expired, ignore silently
        pass
    except Exception as e:
        print(f"Error in spawn_application: {e}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred while processing your request.", ephemeral=True)
        except:
            pass

@bot.tree.command(name="ria_config", description="Configure RIA application settings")
async def ria_config(interaction: discord.Interaction, staff_channel: discord.TextChannel = None, member_role: discord.Role = None):
    try:
        if interaction.response.is_done():
            return

        data = load_data()

        if 'ria_settings' not in data:
            data['ria_settings'] = {}

        if staff_channel:
            data['ria_settings']['staff_channel_id'] = staff_channel.id

        if member_role:
            data['ria_settings']['member_role_id'] = member_role.id

        save_data(data)

        embed = discord.Embed(
            title="⚙️ RIA Configuration Updated",
            color=0x00ff00
        )
        embed.add_field(name="Staff Channel", value=staff_channel.mention if staff_channel else "Not set", inline=True)
        embed.add_field(name="Member Role", value=member_role.mention if member_role else "Not set", inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)
    except discord.NotFound:
        # Interaction expired, ignore silently
        pass
    except Exception as e:
        print(f"Error in ria_config: {e}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred while processing your request.", ephemeral=True)
        except:
            pass

@bot.tree.command(name="applicationcreate", description="Create a custom application panel")
async def application_create(interaction: discord.Interaction):
    try:
        if interaction.response.is_done():
            return

        modal = ApplicationCreateModal()
        await interaction.response.send_modal(modal)
    except discord.NotFound:
        # Interaction expired, ignore silently
        pass
    except Exception as e:
        print(f"Error in application_create: {e}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred while processing your request.", ephemeral=True)
        except:
            pass

@bot.tree.command(name="list_applications", description="View and manage pending applications")
async def list_applications(interaction: discord.Interaction):
    try:
        if interaction.response.is_done():
            return

        data = load_data()
        
        # Collect all pending applications from all panels
        all_pending = []
        
        # Check custom applications
        for app_id, app_data in data.get('custom_applications', {}).items():
            for application_id, application in app_data.get('applications', {}).items():
                if application['status'] == 'pending':
                    all_pending.append({
                        'id': application_id,
                        'panel_name': app_data['name'],
                        'panel_id': app_id,
                        'applicant_id': application['user_id'],
                        'submitted_at': application['submitted_at'],
                        'type': 'custom',
                        'responses': application['responses']
                    })

        # Check RIA applications
        for app_id, app_data in data.get('ria_applications', {}).items():
            if app_data['status'] == 'pending':
                all_pending.append({
                    'id': app_id,
                    'panel_name': 'RIA Application',
                    'panel_id': 'ria',
                    'applicant_id': app_data['user_id'],
                    'submitted_at': app_data['submitted_at'],
                    'type': 'ria',
                    'responses': {
                        'Username': app_data.get('username', ''),
                        'Age': app_data.get('age', ''),
                        'Experience': app_data.get('experience', ''),
                        'Motivation': app_data.get('motivation', ''),
                        'Availability': app_data.get('availability', '')
                    }
                })

        if not all_pending:
            await interaction.response.send_message("📋 No pending applications found!", ephemeral=True)
            return

        # Sort by submission date (newest first)
        all_pending.sort(key=lambda x: x['submitted_at'], reverse=True)

        embed = discord.Embed(
            title="📋 Pending Applications",
            description=f"Total pending applications: **{len(all_pending)}**\n\nSelect an application below to review it.",
            color=0xffff00,
            timestamp=datetime.now()
        )

        # Show summary by panel type
        panel_counts = {}
        for app in all_pending:
            panel_counts[app['panel_name']] = panel_counts.get(app['panel_name'], 0) + 1

        summary = "\n".join([f"**{panel}:** {count}" for panel, count in panel_counts.items()])
        embed.add_field(name="📊 By Panel Type", value=summary, inline=False)

        view = PendingApplicationsSelectView(all_pending)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    except discord.NotFound:
        # Interaction expired, ignore silently
        pass
    except Exception as e:
        print(f"Error in list_applications: {e}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred while processing your request.", ephemeral=True)
        except:
            pass

class ApplicationConfigView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="Edit Application Panels", style=discord.ButtonStyle.primary, emoji="✏️")
    async def edit_panels(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_data()
        custom_apps = data.get('custom_applications', {})

        if not custom_apps:
            await interaction.response.send_message("❌ No application panels found! Use `/applicationcreate` to create one first.", ephemeral=True)
            return

        view = EditApplicationPanelSelectView(custom_apps)
        await interaction.response.send_message("**Select Application Panel to Edit:**", view=view, ephemeral=True)

    @discord.ui.button(label="View Pending Applications", style=discord.ButtonStyle.secondary, emoji="📋")
    async def view_pending(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_data()
        
        # Collect all pending applications from all panels
        all_pending = []
        
        # Check custom applications
        for app_id, app_data in data.get('custom_applications', {}).items():
            for application_id, application in app_data.get('applications', {}).items():
                if application['status'] == 'pending':
                    all_pending.append({
                        'id': application_id,
                        'panel_name': app_data['name'],
                        'panel_id': app_id,
                        'applicant_id': application['user_id'],
                        'submitted_at': application['submitted_at'],
                        'type': 'custom'
                    })

        # Check RIA applications
        for app_id, app_data in data.get('ria_applications', {}).items():
            if app_data['status'] == 'pending':
                all_pending.append({
                    'id': app_id,
                    'panel_name': 'RIA Application',
                    'panel_id': 'ria',
                    'applicant_id': app_data['user_id'],
                    'submitted_at': app_data['submitted_at'],
                    'type': 'ria'
                })

        if not all_pending:
            await interaction.response.send_message("📋 No pending applications found!", ephemeral=True)
            return

        # Sort by submission date (newest first)
        all_pending.sort(key=lambda x: x['submitted_at'], reverse=True)

        embed = discord.Embed(
            title="📋 All Pending Applications",
            description=f"Total pending applications: **{len(all_pending)}**",
            color=0xffff00,
            timestamp=datetime.now()
        )

        # Show up to 10 pending applications
        for i, app in enumerate(all_pending[:10]):
            applicant = interaction.guild.get_member(app['applicant_id'])
            applicant_name = applicant.display_name if applicant else "Unknown User"
            
            embed.add_field(
                name=f"⏳ {app['id']}",
                value=f"**Panel:** {app['panel_name']}\n**Applicant:** {applicant_name}\n**Submitted:** {app['submitted_at'][:10]}",
                inline=True
            )

        if len(all_pending) > 10:
            embed.set_footer(text=f"Showing 10 most recent of {len(all_pending)} pending applications")

        await interaction.response.send_message(embed=embed, ephemeral=True)

class EditApplicationPanelSelectView(discord.ui.View):
    def __init__(self, custom_apps):
        super().__init__(timeout=300)
        self.custom_apps = custom_apps

        # Create select menu options
        options = []
        for app_id, app_data in custom_apps.items():
            name = app_data.get('name', 'Unnamed Panel')
            description = app_data.get('description', '')
            
            if description and len(description) > 100:
                description = description[:97] + "..."

            options.append(discord.SelectOption(
                label=f"{app_id}: {name}"[:100],
                value=app_id,
                description=description[:100] if description else "No description"
            ))

        self.select_panel.options = options[:25]

    @discord.ui.select(placeholder="Choose an application panel to edit...")
    async def select_panel(self, interaction: discord.Interaction, select: discord.ui.Select):
        app_id = select.values[0]
        app_data = self.custom_apps[app_id]

        # Show panel details and edit options
        embed = discord.Embed(
            title=f"📋 Editing Panel: {app_data['name']}",
            description=app_data['description'],
            color=0x0099ff
        )

        embed.add_field(name="Panel ID", value=app_id, inline=True)
        embed.add_field(name="Fields Count", value=len(app_data.get('fields', [])), inline=True)
        embed.add_field(name="Total Applications", value=len(app_data.get('applications', {})), inline=True)

        if app_data.get('staff_channel_id'):
            channel = interaction.guild.get_channel(app_data['staff_channel_id'])
            embed.add_field(name="Staff Channel", value=channel.mention if channel else "Invalid Channel", inline=True)

        if app_data.get('member_role_id'):
            role = interaction.guild.get_role(app_data['member_role_id'])
            embed.add_field(name="Auto-assign Role", value=role.mention if role else "Invalid Role", inline=True)

        view = ApplicationPanelEditView(app_id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class ApplicationPanelEditView(discord.ui.View):
    def __init__(self, app_id):
        super().__init__(timeout=300)
        self.app_id = app_id

    @discord.ui.button(label="Edit Panel Details", style=discord.ButtonStyle.primary, emoji="✏️")
    async def edit_details(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_data()
        app_data = data.get('custom_applications', {}).get(self.app_id)
        
        if not app_data:
            await interaction.response.send_message("❌ Application panel not found!", ephemeral=True)
            return

        modal = EditApplicationPanelModal(self.app_id, app_data)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Manage Fields", style=discord.ButtonStyle.secondary, emoji="📝")
    async def manage_fields(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = ApplicationFieldsView(self.app_id)
        await interaction.response.send_message("**Field Manager:**", view=view, ephemeral=True)

    @discord.ui.button(label="View Applications", style=discord.ButtonStyle.secondary, emoji="📋")
    async def view_applications(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_data()
        app_data = data.get('custom_applications', {}).get(self.app_id)
        
        if not app_data:
            await interaction.response.send_message("❌ Application panel not found!", ephemeral=True)
            return

        applications = app_data.get('applications', {})
        
        if not applications:
            await interaction.response.send_message("📋 No applications found for this panel!", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"📋 Applications for {app_data['name']}",
            description=f"Total applications: **{len(applications)}**",
            color=0x0099ff
        )

        # Status summary
        status_counts = {}
        for app in applications.values():
            status_counts[app['status']] = status_counts.get(app['status'], 0) + 1

        summary = "\n".join([f"**{status.title()}:** {count}" for status, count in status_counts.items()])
        embed.add_field(name="📊 Status Summary", value=summary, inline=False)

        # Show recent applications
        recent_apps = sorted(applications.items(), key=lambda x: x[1]['submitted_at'], reverse=True)[:5]

        for application_id, application in recent_apps:
            applicant = interaction.guild.get_member(application['user_id'])
            applicant_name = applicant.display_name if applicant else "Unknown User"

            status_emoji = {'pending': '⏳', 'accepted': '✅', 'rejected': '❌'}

            embed.add_field(
                name=f"{status_emoji.get(application['status'], '❓')} {application_id}",
                value=f"**Applicant:** {applicant_name}\n**Status:** {application['status'].title()}\n**Submitted:** {application['submitted_at'][:10]}",
                inline=True
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Delete Panel", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def delete_panel(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_data()
        app_data = data.get('custom_applications', {}).get(self.app_id)
        
        if not app_data:
            await interaction.response.send_message("❌ Application panel not found!", ephemeral=True)
            return

        # Delete the panel
        del data['custom_applications'][self.app_id]
        save_data(data)

        await interaction.response.send_message(f"✅ Successfully deleted application panel '{app_data['name']}' ({self.app_id})", ephemeral=True)

class SpawnApplicationSelectView(discord.ui.View):
    def __init__(self, available_panels):
        super().__init__(timeout=300)
        self.available_panels = available_panels

        # Create select menu options
        options = []
        for panel in available_panels:
            description = panel['description']
            if description and len(description) > 100:
                description = description[:97] + "..."

            options.append(discord.SelectOption(
                label=f"{panel['name']}"[:100],
                value=panel['id'],
                description=description[:100] if description else "No description",
                emoji="📋"
            ))

        self.select_panel.options = options[:25]

    @discord.ui.select(placeholder="Choose an application panel to spawn...")
    async def select_panel(self, interaction: discord.Interaction, select: discord.ui.Select):
        panel_id = select.values[0]
        
        if panel_id == 'ria_panel':
            # Spawn RIA panel
            embed = discord.Embed(
                title="🌟 Join RIA - Application Panel",
                description="Welcome to the RIA recruitment center! We're looking for dedicated individuals to join our community.",
                color=0x0099ff,
                timestamp=datetime.now()
            )

            embed.add_field(
                name="📋 How to Apply",
                value="Click the **Apply to Join RIA** button below to start your application process.",
                inline=False
            )

            embed.add_field(
                name="📊 Application Process",
                value="1. Fill out the application form\n2. Wait for review by our team\n3. Receive notification of decision",
                inline=False
            )

            embed.add_field(
                name="❓ Questions?",
                value="If you have any questions about the application process, feel free to reach out to our staff.",
                inline=False
            )

            embed.set_footer(text="RIA Recruitment System")

            if interaction.guild and interaction.guild.icon:
                embed.set_thumbnail(url=interaction.guild.icon.url)

            view = RIAApplicationPanelView()
            await interaction.response.send_message(embed=embed, view=view)
        else:
            # Spawn custom application panel
            data = load_data()
            app_data = data.get('custom_applications', {}).get(panel_id)

            if not app_data:
                await interaction.response.send_message("❌ Application panel not found!", ephemeral=True)
                return

            embed = discord.Embed(
                title=f"📋 {app_data['name']} - Application Panel",
                description=app_data['description'],
                color=0x0099ff,
                timestamp=datetime.now()
            )

            embed.add_field(
                name="📝 How to Apply",
                value=f"Click the **{app_data['button_text']}** button below to start your application.",
                inline=False
            )

            field_list = "\n".join([f"• {field['label']}" for field in app_data['fields']])
            embed.add_field(name="📋 Application Fields", value=field_list, inline=False)

            embed.set_footer(text="Custom Application System")

            if interaction.guild and interaction.guild.icon:
                embed.set_thumbnail(url=interaction.guild.icon.url)

            view = CustomApplicationPanelView(panel_id)
            await interaction.response.send_message(embed=embed, view=view)

class PendingApplicationsSelectView(discord.ui.View):
    def __init__(self, pending_applications):
        super().__init__(timeout=300)
        self.pending_applications = pending_applications

        # Create select menu options
        options = []
        for app in pending_applications[:25]:  # Discord limit
            applicant_id = app['applicant_id']
            applicant_name = f"User {applicant_id}"  # Fallback name
            
            # Try to get actual name from responses if available
            if app['type'] == 'ria' and 'Username' in app['responses']:
                applicant_name = app['responses']['Username']
            
            options.append(discord.SelectOption(
                label=f"{app['panel_name']} - {applicant_name}"[:100],
                value=f"{app['type']}:{app['panel_id']}:{app['id']}",
                description=f"Submitted: {app['submitted_at'][:10]}"[:100],
                emoji="⏳"
            ))

        self.select_application.options = options

    @discord.ui.select(placeholder="Choose a pending application to review...")
    async def select_application(self, interaction: discord.Interaction, select: discord.ui.Select):
        # Check if interaction.guild is available first
        if interaction.guild is None:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
            return
            
        selection = select.values[0]
        app_type, panel_id, application_id = selection.split(':', 2)
        
        data = load_data()
        
        if app_type == 'ria':
            # Handle RIA application
            if application_id not in data.get('ria_applications', {}):
                await interaction.response.send_message("❌ Application not found!", ephemeral=True)
                return

            app_data = data['ria_applications'][application_id]
            applicant = interaction.guild.get_member(app_data['user_id'])
            applicant_name = applicant.display_name if applicant else "Unknown User"

            embed = discord.Embed(
                title="📋 RIA Application Review",
                description=f"**Applicant:** {applicant_name}\n**Application ID:** `{application_id}`",
                color=0x0099ff
            )

            # Show what the user filled out in their application
            embed.add_field(name="📝 Discord Username", value=app_data.get('username', 'Not provided'), inline=False)
            embed.add_field(name="🎂 Age", value=app_data.get('age', 'Not provided'), inline=False)
            embed.add_field(name="💼 Previous Experience", value=app_data.get('experience', 'Not provided')[:1000], inline=False)
            embed.add_field(name="💭 Why do you want to join RIA?", value=app_data.get('motivation', 'Not provided')[:1000], inline=False)
            embed.add_field(name="⏰ Availability", value=app_data.get('availability', 'Not provided')[:1000], inline=False)

            embed.set_footer(text=f"Submitted: {app_data['submitted_at'][:19].replace('T', ' ')}")

            review_view = RIAApplicationReviewView(application_id)
            await interaction.response.send_message(embed=embed, view=review_view, ephemeral=True)
        
        else:
            # Handle custom application
            app_panel = data.get('custom_applications', {}).get(panel_id)
            if not app_panel or application_id not in app_panel.get('applications', {}):
                await interaction.response.send_message("❌ Application not found!", ephemeral=True)
                return

            application = app_panel['applications'][application_id]
            applicant = interaction.guild.get_member(application['user_id'])
            applicant_name = applicant.display_name if applicant else "Unknown User"

            embed = discord.Embed(
                title=f"📋 {app_panel['name']} Review",
                description=f"**Applicant:** {applicant_name}\n**Application ID:** `{application_id}`",
                color=0x0099ff
            )

            # Show what the user filled out in their application
            for field_name, response in application.get('responses', {}).items():
                embed.add_field(name=f"📝 {field_name}", value=response[:1000] if response else 'Not provided', inline=False)

            embed.set_footer(text=f"Submitted: {application['submitted_at'][:19].replace('T', ' ')}")

            review_view = CustomApplicationReviewView(panel_id, application_id)
            await interaction.response.send_message(embed=embed, view=review_view, ephemeral=True)

class EditApplicationPanelModal(discord.ui.Modal, title="Edit Application Panel"):
    def __init__(self, app_id, app_data):
        super().__init__()
        self.app_id = app_id

        # Pre-fill with existing data
        self.app_name.default = app_data.get('name', '')
        self.app_description.default = app_data.get('description', '')
        self.button_text.default = app_data.get('button_text', '')
        self.staff_channel_id.default = str(app_data.get('staff_channel_id', '')) if app_data.get('staff_channel_id') else ''
        self.member_role_id.default = str(app_data.get('member_role_id', '')) if app_data.get('member_role_id') else ''

    app_name = discord.ui.TextInput(
        label="Application Name",
        placeholder="e.g., 'Staff Application', 'Member Application'",
        max_length=100,
        required=True
    )

    app_description = discord.ui.TextInput(
        label="Application Description",
        placeholder="Brief description of what this application is for...",
        style=discord.TextStyle.paragraph,
        max_length=500,
        required=True
    )

    button_text = discord.ui.TextInput(
        label="Button Text",
        placeholder="e.g., 'Apply for Staff', 'Join Us'",
        max_length=80,
        required=False
    )

    staff_channel_id = discord.ui.TextInput(
        label="Staff Channel ID (optional)",
        placeholder="Channel ID where applications will be sent",
        max_length=20,
        required=False
    )

    member_role_id = discord.ui.TextInput(
        label="Auto-assign Role ID (optional)",
        placeholder="Role ID to assign when accepted",
        max_length=20,
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        data = load_data()

        if self.app_id not in data.get('custom_applications', {}):
            await interaction.response.send_message("❌ Application panel not found!", ephemeral=True)
            return

        # Update the panel data
        app_data = data['custom_applications'][self.app_id]
        app_data['name'] = str(self.app_name.value)
        app_data['description'] = str(self.app_description.value)
        app_data['button_text'] = str(self.button_text.value) if self.button_text.value else f"Apply for {self.app_name.value}"
        app_data['staff_channel_id'] = int(self.staff_channel_id.value) if self.staff_channel_id.value and self.staff_channel_id.value.isdigit() else None
        app_data['member_role_id'] = int(self.member_role_id.value) if self.member_role_id.value and self.member_role_id.value.isdigit() else None

        save_data(data)

        await interaction.response.send_message(f"✅ Application panel '{self.app_name.value}' updated successfully!", ephemeral=True)

@bot.tree.command(name="configapplication", description="Configure and manage application panels")
async def config_application(interaction: discord.Interaction):
    try:
        if interaction.response.is_done():
            return

        view = ApplicationConfigView()
        
        embed = discord.Embed(
            title="⚙️ Application Configuration Panel",
            description="Manage your application panels and view pending applications.",
            color=0x0099ff
        )

        embed.add_field(
            name="📝 Edit Application Panels",
            value="Modify existing application panel settings and fields",
            inline=False
        )

        embed.add_field(
            name="📋 View Pending Applications",
            value="See all pending applications across all panels",
            inline=False
        )

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    except discord.NotFound:
        # Interaction expired, ignore silently
        pass
    except Exception as e:
        print(f"Error in config_application: {e}")
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