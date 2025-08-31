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

        # Ensure buttons list exists
        if 'buttons' not in self.embed_data:
            self.embed_data['buttons'] = []

    @discord.ui.button(label="Create Button", style=discord.ButtonStyle.primary, emoji="🔘")
    async def create_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if len(self.embed_data.get('buttons', [])) >= 5:
            await interaction.response.send_message("❌ Maximum of 5 buttons allowed per embed!", ephemeral=True)
            return
        
        try:
            modal = ButtonModal(self.embed_data)
            await interaction.response.send_modal(modal)
        except discord.InteractionResponded:
            # If interaction was already responded to, try followup
            modal = ButtonModal(self.embed_data)
            await interaction.followup.send("Opening button creation modal...", ephemeral=True)

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

    @discord.ui.button(label="Add Field", style=discord.ButtonStyle.secondary, emoji="📝")
    async def add_field(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = FieldModal(self.embed_data)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Manage Buttons", style=discord.ButtonStyle.secondary, emoji="🎛️")
    async def manage_buttons(self, interaction: discord.Interaction, button: discord.ui.Button):
        buttons = self.embed_data.get('buttons', [])
        if not buttons:
            await interaction.response.send_message("No buttons to manage! Add a button first.", ephemeral=True)
            return

        view = ButtonManagerView(self.embed_data, self.editing_embed_id)
        await interaction.response.send_message("**Button Manager:**\nSelect a button to edit or delete:", view=view, ephemeral=True)

    @discord.ui.button(label="Preview", style=discord.ButtonStyle.secondary, emoji="👁️")
    async def preview_embed(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = create_embed_from_data(self.embed_data)
        view = create_embed_button_view(self.embed_data) if self.embed_data.get('buttons') else None
        await interaction.response.send_message("**Preview:**", embed=embed, view=view, ephemeral=True)

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
        
        # Create button view if buttons exist
        button_view = create_embed_button_view(self.embed_data) if self.embed_data.get('buttons') else None
        await interaction.followup.send(embed=embed, view=button_view)

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

class ButtonModal(discord.ui.Modal, title="Add Button"):
    def __init__(self, embed_data, button_index=None):
        super().__init__()
        self.embed_data = embed_data
        self.button_index = button_index

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
        view = ButtonActionView(self.embed_data, self.button_index or (len(self.embed_data['buttons']) - 1))
        try:
            await interaction.response.send_message("Button created! Now choose what this button should do:", view=view, ephemeral=True)
        except discord.InteractionResponded:
            await interaction.followup.send("Button created! Now choose what this button should do:", view=view, ephemeral=True)

class ButtonActionView(discord.ui.View):
    def __init__(self, embed_data, button_index):
        super().__init__(timeout=300)
        self.embed_data = embed_data
        self.button_index = button_index

    @discord.ui.select(
        placeholder="Choose what this button should do...",
        options=[
            discord.SelectOption(label="Send Message", value="send_message", description="Send a message to the channel", emoji="💬"),
            discord.SelectOption(label="Give Role", value="give_role", description="Give a role to the user", emoji="🎭"),
            discord.SelectOption(label="Remove Role", value="remove_role", description="Remove a role from the user", emoji="🗑️"),
            discord.SelectOption(label="Send DM", value="send_dm", description="Send a direct message to the user", emoji="📩"),
            discord.SelectOption(label="Custom Response", value="custom_response", description="Send a custom response message", emoji="📝"),
            discord.SelectOption(label="Shop Item", value="shop_item", description="Virtual shop item purchase", emoji="🛒"),
        ]
    )
    async def select_action(self, interaction: discord.Interaction, select: discord.ui.Select):
        action_type = select.values[0]
        
        if action_type == "send_message":
            modal = ActionConfigModal(self.embed_data, self.button_index, "send_message", "Configure Message")
        elif action_type == "give_role":
            modal = ActionConfigModal(self.embed_data, self.button_index, "give_role", "Configure Role to Give")
        elif action_type == "remove_role":
            modal = ActionConfigModal(self.embed_data, self.button_index, "remove_role", "Configure Role to Remove")
        elif action_type == "send_dm":
            modal = ActionConfigModal(self.embed_data, self.button_index, "send_dm", "Configure DM Message")
        elif action_type == "custom_response":
            modal = ActionConfigModal(self.embed_data, self.button_index, "custom_response", "Configure Response")
        elif action_type == "shop_item":
            modal = ActionConfigModal(self.embed_data, self.button_index, "shop_item", "Configure Shop Item")
        
        await interaction.response.send_modal(modal)

class ActionConfigModal(discord.ui.Modal):
    def __init__(self, embed_data, button_index, action_type, title):
        super().__init__(title=title)
        self.embed_data = embed_data
        self.button_index = button_index
        self.action_type = action_type

        # Configure fields based on action type
        if action_type in ["send_message", "custom_response", "send_dm"]:
            self.add_item(discord.ui.TextInput(
                label="Message Content",
                placeholder="Enter the message to send...",
                style=discord.TextStyle.paragraph,
                max_length=2000,
                required=True
            ))
        elif action_type in ["give_role", "remove_role"]:
            self.add_item(discord.ui.TextInput(
                label="Role ID",
                placeholder="Enter the role ID (right-click role, copy ID)...",
                max_length=25,
                required=True
            ))
            self.add_item(discord.ui.TextInput(
                label="Success Message",
                placeholder="Message to send when action succeeds...",
                max_length=200,
                required=False,
                default="Action completed!"
            ))
        elif action_type == "shop_item":
            self.add_item(discord.ui.TextInput(
                label="Item Name",
                placeholder="Enter item name...",
                max_length=100,
                required=True
            ))
            self.add_item(discord.ui.TextInput(
                label="Item Price",
                placeholder="Enter price (for display)...",
                max_length=50,
                required=True
            ))
            self.add_item(discord.ui.TextInput(
                label="Purchase Message",
                placeholder="Message sent when purchased...",
                style=discord.TextStyle.paragraph,
                max_length=500,
                required=True
            ))

    async def on_submit(self, interaction: discord.Interaction):
        action_data = {'type': self.action_type}
        
        if self.action_type in ["send_message", "custom_response", "send_dm"]:
            action_data['message'] = str(self.children[0].value)
        elif self.action_type in ["give_role", "remove_role"]:
            action_data['role_id'] = str(self.children[0].value)
            action_data['success_message'] = str(self.children[1].value) if self.children[1].value else "Action completed!"
        elif self.action_type == "shop_item":
            action_data['item_name'] = str(self.children[0].value)
            action_data['price'] = str(self.children[1].value)
            action_data['purchase_message'] = str(self.children[2].value)

        # Update button with action
        self.embed_data['buttons'][self.button_index]['action'] = action_data

        view = EmbedOptionsView(self.embed_data)
        await interaction.response.send_message(f"✅ Button action configured! Continue editing:", view=view, ephemeral=True)

class ButtonManagerView(discord.ui.View):
    def __init__(self, embed_data, editing_embed_id=None):
        super().__init__(timeout=300)
        self.embed_data = embed_data
        self.editing_embed_id = editing_embed_id

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
        elif action.get('type') == 'shop_item':
            action_desc += f"\nItem: {action.get('item_name', 'N/A')} - {action.get('price', 'N/A')}"
        
        embed.add_field(name="Action", value=action_desc, inline=False)

        await interaction.response.send_message(embed=embed, view=self, ephemeral=True)

    @discord.ui.button(label="Edit Selected Button", style=discord.ButtonStyle.primary, emoji="✏️")
    async def edit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not hasattr(self, 'selected_button_index'):
            await interaction.response.send_message("❌ Please select a button first!", ephemeral=True)
            return

        modal = ButtonModal(self.embed_data, self.selected_button_index)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Delete Selected Button", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not hasattr(self, 'selected_button_index'):
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
            super().__init__(timeout=None)
            self.buttons_data = buttons_data
            
            # Add buttons dynamically
            for i, button_data in enumerate(buttons_data):
                style_map = {
                    'primary': discord.ButtonStyle.primary,
                    'secondary': discord.ButtonStyle.secondary,
                    'success': discord.ButtonStyle.success,
                    'danger': discord.ButtonStyle.danger
                }
                
                style = style_map.get(button_data.get('style', 'primary'), discord.ButtonStyle.primary)
                
                # Create button
                button = discord.ui.Button(
                    label=button_data.get('label', f'Button {i+1}'),
                    style=style,
                    emoji=button_data.get('emoji'),
                    custom_id=f"embed_button_{i}"
                )
                
                # Create callback function
                button.callback = self.create_button_callback(i, button_data.get('action', {}))
                self.add_item(button)
        
        def create_button_callback(self, button_index, action_data):
            async def button_callback(interaction):
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
                
                elif action_type == "give_role":
                    role_id = int(action_data.get('role_id', 0))
                    role = interaction.guild.get_role(role_id)
                    if role:
                        if role in interaction.user.roles:
                            await interaction.response.send_message(f"❌ You already have the {role.name} role!", ephemeral=True)
                        else:
                            try:
                                await interaction.user.add_roles(role)
                                success_msg = action_data.get('success_message', f"✅ You've been given the {role.name} role!")
                                await interaction.response.send_message(success_msg, ephemeral=True)
                            except discord.Forbidden:
                                await interaction.response.send_message("❌ I don't have permission to assign this role!", ephemeral=True)
                    else:
                        await interaction.response.send_message("❌ Role not found!", ephemeral=True)
                
                elif action_type == "remove_role":
                    role_id = int(action_data.get('role_id', 0))
                    role = interaction.guild.get_role(role_id)
                    if role:
                        if role not in interaction.user.roles:
                            await interaction.response.send_message(f"❌ You don't have the {role.name} role!", ephemeral=True)
                        else:
                            try:
                                await interaction.user.remove_roles(role)
                                success_msg = action_data.get('success_message', f"✅ The {role.name} role has been removed!")
                                await interaction.response.send_message(success_msg, ephemeral=True)
                            except discord.Forbidden:
                                await interaction.response.send_message("❌ I don't have permission to remove this role!", ephemeral=True)
                    else:
                        await interaction.response.send_message("❌ Role not found!", ephemeral=True)
                
                elif action_type == "shop_item":
                    item_name = action_data.get('item_name', 'Mystery Item')
                    price = action_data.get('price', 'Free')
                    purchase_msg = action_data.get('purchase_message', f'You purchased {item_name} for {price}!')
                    
                    embed = discord.Embed(
                        title="🛒 Purchase Successful!",
                        description=purchase_msg,
                        color=0x00ff00,
                        timestamp=datetime.now()
                    )
                    embed.add_field(name="Item", value=item_name, inline=True)
                    embed.add_field(name="Price", value=price, inline=True)
                    embed.set_footer(text=f"Purchased by {interaction.user.display_name}")
                    
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                
                else:
                    await interaction.response.send_message("🔘 Button clicked! (No action configured)", ephemeral=True)
                    
            except Exception as e:
                print(f"Error in button action: {e}")
                await interaction.response.send_message("❌ An error occurred while processing the button action.", ephemeral=True)
    
    return DynamicEmbedView(embed_data['buttons'])

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

# RIA Enrollment System - Command-based approach

async def send_welcome_dm(member, role_type):
    """Send welcome DM to member based on role type"""
    if role_type == "ria":
        embed = discord.Embed(
            title="🎉 Welcome to RIA! 🎉",
            description=f"We're glad to have you! To show your loyalty and represent the crew, please make sure to:\n\n🏳️ Set your flag to PURPLE 🏳️\n\nThis helps us recognize each other in the streets. Stay active, respect the crew, and enjoy the vibes!\n\n— RIA Leadership 💜",
            color=0x800080,
            timestamp=datetime.now()
        )
        embed.set_footer(text="RIA Enrollment System")
    elif role_type == "staff":
        embed = discord.Embed(
            title="🎉 Welcome to the RIA Staff Team! 🎉",
            description=f"Congratulations! You've been accepted into the RIA Staff Team. You now have additional responsibilities and privileges.\n\nPlease review the staff guidelines and contact leadership if you have any questions.\n\n— RIA Leadership 💜",
            color=0x800080,
            timestamp=datetime.now()
        )
        embed.set_footer(text="RIA Staff System")
    elif role_type == "membership":
        embed = discord.Embed(
            title="🎫 RIA Membership Access Granted! 🎫",
            description=f"You've been granted membership access! You now have access to member-only channels and features.\n\nEnjoy your membership benefits!\n\n— RIA Leadership 💜",
            color=0x800080,
            timestamp=datetime.now()
        )
        embed.set_footer(text="RIA Membership System")
    else:
        return "❌ Unknown role type"

    try:
        await member.send(embed=embed)
        return "✅ Welcome message sent via DM"
    except discord.Forbidden:
        return "⚠️ Could not send DM (user has DMs disabled)"

async def send_decline_dm(member):
    """Send decline DM to member"""
    embed = discord.Embed(
        title="❌ RIA Enrollment Declined",
        description=f"Unfortunately your enrollment into RIA has been declined at this time. You may reapply in the future.\n\nIf you have questions, please contact RIA leadership.\n\n— RIA Leadership",
        color=0xff0000,
        timestamp=datetime.now()
    )
    embed.set_footer(text="RIA Enrollment System")
    
    try:
        await member.send(embed=embed)
        return "✅ Decline message sent via DM"
    except discord.Forbidden:
        return "⚠️ Could not send DM (user has DMs disabled)"

# Slash Commands
@bot.tree.command(name="create_embed", description="Create a custom embed message")
async def create_embed(interaction: discord.Interaction):
    try:
        if not interaction.guild_id:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
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

@bot.tree.command(name="edit_embed", description="Edit an existing embed")
async def edit_embed(interaction: discord.Interaction):
    try:
        # Simplified guild check - just check if guild_id exists
        if not interaction.guild_id:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
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

@bot.tree.command(name="list_embeds", description="List all stored embeds")
async def list_embeds(interaction: discord.Interaction):
    try:
        if not interaction.guild_id:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
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

@bot.tree.command(name="spawnembed", description="Spawn a stored embed message")
async def spawn_embed(interaction: discord.Interaction):
    try:
        if not interaction.guild_id:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
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

@bot.tree.command(name="delete_embed", description="Delete a stored embed message")
async def delete_embed(interaction: discord.Interaction, embed_id: str):
    try:
        if not interaction.guild_id:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
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

@bot.tree.command(name="automod", description="Manage auto-moderation settings")
async def automod(interaction: discord.Interaction, action: str, word: str = None):
    try:
        if not interaction.guild_id:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
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
    except Exception as e:
        print(f"Error in automod: {e}")
        import traceback
        traceback.print_exc()
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred while processing your request.", ephemeral=True)
        except:
            pass

@bot.tree.command(name="ria_accept", description="Accept a member into RIA or show members without RIA role")
async def ria_accept(interaction: discord.Interaction, member: discord.Member = None):
    """Accept a member into RIA or show all members without RIA role"""
    try:
        if not interaction.guild_id:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
            return

        # Get the RIA role (ID: 1409683503100067951)
        ria_role = interaction.guild.get_role(1409683503100067951)
        if not ria_role:
            await interaction.response.send_message("❌ RIA role not found!", ephemeral=True)
            return

        # If no member specified, show all members without RIA role
        if member is None:
            members_without_ria = []
            for guild_member in interaction.guild.members:
                if not guild_member.bot and ria_role not in guild_member.roles:
                    members_without_ria.append(guild_member)

            if not members_without_ria:
                await interaction.response.send_message("✅ All members already have the RIA role!", ephemeral=True)
                return

            # Create embed showing members without RIA role
            embed = discord.Embed(
                title="👥 Members Without RIA Role",
                description=f"Found **{len(members_without_ria)}** members without the RIA role:",
                color=0xff9900
            )

            # Split members into chunks for fields (Discord has field limits)
            chunk_size = 10
            for i in range(0, len(members_without_ria), chunk_size):
                chunk = members_without_ria[i:i+chunk_size]
                member_list = "\n".join([f"• {member.mention} ({member.display_name})" for member in chunk])
                
                field_name = f"Members {i+1}-{min(i+chunk_size, len(members_without_ria))}"
                embed.add_field(name=field_name, value=member_list, inline=False)

            embed.set_footer(text="Use /ria_accept @member to accept a specific member")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # If member specified, accept them into RIA
        if ria_role in member.roles:
            await interaction.response.send_message(f"❌ {member.mention} already has the RIA role!", ephemeral=True)
            return

        try:
            await member.add_roles(ria_role)
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to assign roles!", ephemeral=True)
            return

        # Send welcome DM
        dm_status = await send_welcome_dm(member, "ria")
        
        await interaction.response.send_message(f"✅ Successfully enrolled {member.mention} into RIA!\n{dm_status}", ephemeral=True)

    except Exception as e:
        print(f"Error in ria_accept: {e}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred while processing your request.", ephemeral=True)
        except:
            pass

@bot.tree.command(name="ria_decline", description="Decline a member's RIA enrollment")
async def ria_decline(interaction: discord.Interaction, member: discord.Member):
    """Decline a member's RIA enrollment"""
    try:
        if not interaction.guild_id:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
            return

        # Send decline DM
        dm_status = await send_decline_dm(member)
        
        await interaction.response.send_message(f"❌ Declined enrollment for {member.mention}.\n{dm_status}", ephemeral=True)

    except Exception as e:
        print(f"Error in ria_decline: {e}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred while processing your request.", ephemeral=True)
        except:
            pass

@bot.tree.command(name="ria_staff", description="Add a member to RIA Staff Team")
async def ria_staff(interaction: discord.Interaction, member: discord.Member):
    """Add a member to RIA Staff Team"""
    try:
        if not interaction.guild_id:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
            return

        # Add the Staff role (ID: 1409695735829626942)
        staff_role = interaction.guild.get_role(1409695735829626942)
        if not staff_role:
            await interaction.response.send_message("❌ Staff role not found!", ephemeral=True)
            return

        try:
            await member.add_roles(staff_role)
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to assign staff roles!", ephemeral=True)
            return

        # Send staff welcome DM
        dm_status = await send_welcome_dm(member, "staff")
        
        await interaction.response.send_message(f"✅ Successfully added {member.mention} to the Staff Team!\n{dm_status}", ephemeral=True)

    except Exception as e:
        print(f"Error in ria_staff: {e}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred while processing your request.", ephemeral=True)
        except:
            pass

@bot.tree.command(name="ria_membership", description="Grant membership access to a member")
async def ria_membership(interaction: discord.Interaction, member: discord.Member):
    """Grant membership access to a member"""
    try:
        if not interaction.guild_id:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
            return

        # Add the Membership role (ID: 1411525587474059264)
        membership_role = interaction.guild.get_role(1411525587474059264)
        if not membership_role:
            await interaction.response.send_message("❌ Membership role not found!", ephemeral=True)
            return

        try:
            await member.add_roles(membership_role)
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to assign membership roles!", ephemeral=True)
            return

        # Send membership welcome DM
        dm_status = await send_welcome_dm(member, "membership")
        
        await interaction.response.send_message(f"✅ Successfully granted membership access to {member.mention}!\n{dm_status}", ephemeral=True)

    except Exception as e:
        print(f"Error in ria_membership: {e}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred while processing your request.", ephemeral=True)
        except:
            pass

@bot.tree.command(name="ria_remove", description="Remove RIA roles from a member")
async def ria_remove(interaction: discord.Interaction, member: discord.Member, role_type: str):
    """Remove RIA roles from a member"""
    try:
        if not interaction.guild_id:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
            return

        role_id = None
        role_name = ""
        
        if role_type.lower() == "ria":
            role_id = 1409683503100067951
            role_name = "RIA"
        elif role_type.lower() == "staff":
            role_id = 1409695735829626942
            role_name = "Staff"
        elif role_type.lower() == "membership":
            role_id = 1411525587474059264
            role_name = "Membership"
        else:
            await interaction.response.send_message("❌ Invalid role type! Use: ria, staff, or membership", ephemeral=True)
            return

        role = interaction.guild.get_role(role_id)
        if not role:
            await interaction.response.send_message(f"❌ {role_name} role not found!", ephemeral=True)
            return

        if role not in member.roles:
            await interaction.response.send_message(f"❌ {member.mention} doesn't have the {role_name} role!", ephemeral=True)
            return

        try:
            await member.remove_roles(role)
            await interaction.response.send_message(f"✅ Successfully removed {role_name} role from {member.mention}!", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to remove roles!", ephemeral=True)

    except Exception as e:
        print(f"Error in ria_remove: {e}")
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