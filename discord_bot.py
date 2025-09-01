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

# Bot functionality continues here

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





# Membership System Commands

# Membership configuration - you can modify these
MEMBERSHIP_CONFIG = {
    "ria_premium": {
        "name": "RIA Premium Membership",
        "price": "$3/month",
        "role_id": 1411525587474059264,  # RIA Premium role ID
        "benefits": [
            "🎁 EXCLUSIVE Giveaways",
            "👕 RARE RIA PREMIUM SHIRT (IRL or in-server)",
            "🔒 HIDDEN Channel Access (Premium Members ONLY)",
            "⭐ Special Role in the server",
            "📝 ANY NAME OF YOUR CHOICE in the Discord!"
        ],
        "emoji": "💎",
        "signup_url": "https://docs.google.com/forms/d/e/1FAIpQLSckQudNZqdY1AF_Xco-KBueeQ_aa3R1XWEtR5aUKJM-KZmqVw/viewform"
    }
}

@bot.tree.command(name="membership", description="View available memberships")
async def membership(interaction: discord.Interaction):
    """Display available membership tiers"""
    try:
        if not interaction.guild_id:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
            return

        embed = discord.Embed(
            title="🌟 Server Memberships",
            description="Choose your membership tier and unlock exclusive benefits!",
            color=0xFFD700
        )

        for tier_id, config in MEMBERSHIP_CONFIG.items():
            benefits_text = "\n".join(config["benefits"])
            embed.add_field(
                name=f"{config['emoji']} {config['name']} - {config['price']}",
                value=f"```{benefits_text}```",
                inline=False
            )

        embed.set_footer(text="Use /purchase_membership to buy a membership!")
        embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)

        # Create purchase buttons
        view = MembershipPurchaseView()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    except Exception as e:
        print(f"Error in membership command: {e}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred.", ephemeral=True)
        except:
            pass

@bot.tree.command(name="purchase_membership", description="Purchase a membership tier")
@discord.app_commands.describe(tier="Choose membership tier")
@discord.app_commands.choices(tier=[
    discord.app_commands.Choice(name="💎 RIA Premium Membership", value="ria_premium")
])
async def purchase_membership(interaction: discord.Interaction, tier: str):
    """Handle membership purchase"""
    try:
        if not interaction.guild_id:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
            return

        if tier not in MEMBERSHIP_CONFIG:
            await interaction.response.send_message("❌ Invalid membership tier!", ephemeral=True)
            return

        config = MEMBERSHIP_CONFIG[tier]
        
        # Create purchase confirmation embed
        embed = discord.Embed(
            title=f"{config['emoji']} Purchase {config['name']}",
            description=f"**Price:** {config['price']}\n\n**Benefits Include:**",
            color=0x00FF00
        )

        benefits_text = "\n".join(config["benefits"])
        embed.add_field(name="Your Benefits", value=benefits_text, inline=False)
        
        embed.add_field(
            name="💳 Sign Up Now!",
            value=f"**[Click here to sign up for ONLY $3/month!]({config.get('signup_url', '#')})**\n\n```To complete your purchase:\n1. Fill out the signup form\n2. Submit proof of payment\n3. Get immediate access!```",
            inline=False
        )

        embed.add_field(
            name="🚀 Get Started",
            value="Don't forget to submit proof of payment at the end to get immediate access!\n**Elevate your RIA experience today!**",
            inline=False
        )
        
        embed.set_footer(text="Thank you for supporting our server!")

        # Create confirmation view
        view = PurchaseConfirmationView(tier, f"txn_{interaction.user.id}_{int(datetime.now().timestamp())}")
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    except Exception as e:
        print(f"Error in purchase_membership: {e}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred.", ephemeral=True)
        except:
            pass

@bot.tree.command(name="grant_membership", description="Grant membership to a user (Staff Only)")
@discord.app_commands.describe(
    member="The member to grant membership to",
    tier="Membership tier to grant"
)
@discord.app_commands.choices(tier=[
    discord.app_commands.Choice(name="💎 RIA Premium Membership", value="ria_premium")
])
async def grant_membership(interaction: discord.Interaction, member: discord.Member, tier: str):
    """Grant membership to a user (staff command)"""
    try:
        if not interaction.guild_id:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
            return

        # Check if user has permission (you can modify this check)
        if not interaction.user.guild_permissions.manage_roles:
            await interaction.response.send_message("❌ You don't have permission to grant memberships!", ephemeral=True)
            return

        if tier not in MEMBERSHIP_CONFIG:
            await interaction.response.send_message("❌ Invalid membership tier!", ephemeral=True)
            return

        config = MEMBERSHIP_CONFIG[tier]
        
        # Check if role is configured
        if not config["role_id"]:
            await interaction.response.send_message("❌ Membership role not configured! Please set the role ID in the bot configuration.", ephemeral=True)
            return

        role = interaction.guild.get_role(config["role_id"])
        if not role:
            await interaction.response.send_message("❌ Membership role not found!", ephemeral=True)
            return

        # Check if user already has the role
        if role in member.roles:
            await interaction.response.send_message(f"❌ {member.mention} already has {config['name']}!", ephemeral=True)
            return

        # Grant the role
        try:
            await member.add_roles(role)
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to assign this role!", ephemeral=True)
            return

        # Create success embed
        embed = discord.Embed(
            title="✅ Membership Granted!",
            description=f"{member.mention} has been granted **{config['name']}**!",
            color=0x00FF00
        )
        embed.add_field(name="Granted by", value=interaction.user.mention, inline=True)
        embed.add_field(name="Membership Tier", value=f"{config['emoji']} {config['name']}", inline=True)

        await interaction.response.send_message(embed=embed)

        # Send welcome DM to the member
        try:
            dm_embed = discord.Embed(
                title=f"🎉 Welcome to {config['name']}!",
                description=f"Congratulations! You now have access to exclusive member benefits in **{interaction.guild.name}**.",
                color=0xFFD700
            )
            benefits_text = "\n".join(config["benefits"])
            dm_embed.add_field(name="Your Benefits", value=benefits_text, inline=False)
            dm_embed.set_footer(text="Thank you for being a valued member!")

            await member.send(embed=dm_embed)
        except discord.Forbidden:
            pass  # User has DMs disabled

    except Exception as e:
        print(f"Error in grant_membership: {e}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred.", ephemeral=True)
        except:
            pass

@bot.tree.command(name="revoke_membership", description="Revoke membership from a user (Staff Only)")
@discord.app_commands.describe(
    member="The member to revoke membership from",
    tier="Membership tier to revoke"
)
@discord.app_commands.choices(tier=[
    discord.app_commands.Choice(name="💎 RIA Premium Membership", value="ria_premium")
])
async def revoke_membership(interaction: discord.Interaction, member: discord.Member, tier: str):
    """Revoke membership from a user (staff command)"""
    try:
        if not interaction.guild_id:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
            return

        # Check if user has permission
        if not interaction.user.guild_permissions.manage_roles:
            await interaction.response.send_message("❌ You don't have permission to revoke memberships!", ephemeral=True)
            return

        if tier not in MEMBERSHIP_CONFIG:
            await interaction.response.send_message("❌ Invalid membership tier!", ephemeral=True)
            return

        config = MEMBERSHIP_CONFIG[tier]
        
        if not config["role_id"]:
            await interaction.response.send_message("❌ Membership role not configured!", ephemeral=True)
            return

        role = interaction.guild.get_role(config["role_id"])
        if not role:
            await interaction.response.send_message("❌ Membership role not found!", ephemeral=True)
            return

        if role not in member.roles:
            await interaction.response.send_message(f"❌ {member.mention} doesn't have {config['name']}!", ephemeral=True)
            return

        # Remove the role
        try:
            await member.remove_roles(role)
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to remove this role!", ephemeral=True)
            return

        embed = discord.Embed(
            title="🗑️ Membership Revoked",
            description=f"{config['name']} has been revoked from {member.mention}.",
            color=0xFF6B6B
        )
        embed.add_field(name="Revoked by", value=interaction.user.mention, inline=True)

        await interaction.response.send_message(embed=embed)

    except Exception as e:
        print(f"Error in revoke_membership: {e}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred.", ephemeral=True)
        except:
            pass

@bot.tree.command(name="my_membership", description="Check your current membership status")
async def my_membership(interaction: discord.Interaction):
    """Check user's current membership status"""
    try:
        if not interaction.guild_id:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
            return

        user_memberships = []
        
        for tier_id, config in MEMBERSHIP_CONFIG.items():
            if config["role_id"]:
                role = interaction.guild.get_role(config["role_id"])
                if role and role in interaction.user.roles:
                    user_memberships.append((tier_id, config))

        embed = discord.Embed(
            title="👤 Your Membership Status",
            color=0x0099FF
        )

        if user_memberships:
            embed.description = "🎉 Thank you for being a valued member!"
            
            for tier_id, config in user_memberships:
                benefits_text = "\n".join(config["benefits"])
                embed.add_field(
                    name=f"{config['emoji']} {config['name']}",
                    value=f"```{benefits_text}```",
                    inline=False
                )
        else:
            embed.description = "You don't have any active memberships."
            embed.add_field(
                name="💡 Want to become a member?",
                value="Use `/membership` to view available tiers and `/purchase_membership` to get started!",
                inline=False
            )

        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        print(f"Error in my_membership: {e}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred.", ephemeral=True)
        except:
            pass

class MembershipPurchaseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="💎 Buy RIA Premium", style=discord.ButtonStyle.primary)
    async def buy_ria_premium(self, interaction: discord.Interaction, button: discord.ui.Button):
        await purchase_membership.callback(interaction, "ria_premium")

class PurchaseConfirmationView(discord.ui.View):
    def __init__(self, tier, transaction_id):
        super().__init__(timeout=300)
        self.tier = tier
        self.transaction_id = transaction_id

    @discord.ui.button(label="📝 Sign Up Now", style=discord.ButtonStyle.primary, emoji="🚀")
    async def signup_now(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = MEMBERSHIP_CONFIG[self.tier]
        signup_url = config.get('signup_url', '#')
        
        embed = discord.Embed(
            title="🚀 Complete Your Membership!",
            description=f"**Click the link below to sign up for RIA Premium:**\n\n🔗 **[SIGN UP FOR ONLY $3/MONTH!]({signup_url})**",
            color=0x00FF00
        )
        embed.add_field(
            name="📋 What to do:",
            value="1. Click the signup link above\n2. Fill out the form completely\n3. Submit proof of payment\n4. Get immediate access to all benefits!",
            inline=False
        )
        embed.set_footer(text="Elevate your RIA experience today!")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="📞 Contact Staff", style=discord.ButtonStyle.secondary)
    async def contact_staff(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="📞 Need Help?",
            description="If you need assistance with your membership purchase, contact any staff member.",
            color=0x0099FF
        )
        embed.add_field(name="How to Contact", value="• Send a DM to any staff member\n• Use a support ticket\n• Tag staff in an appropriate channel", inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="membership_panel", description="Create a membership panel for users to purchase")
async def membership_panel(interaction: discord.Interaction):
    """Create and send a membership panel embed"""
    try:
        if not interaction.guild_id:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
            return

        # Check if user has permission to create panels
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("❌ You need Manage Messages permission to create membership panels!", ephemeral=True)
            return

        config = MEMBERSHIP_CONFIG["ria_premium"]
        
        # Create the main membership panel embed
        embed = discord.Embed(
            title="🌟 RIA Premium Membership",
            description="**Sign up now for ONLY $3/month and unlock these EXCLUSIVE benefits:**",
            color=0xFFD700
        )
        
        # Add benefits as fields
        benefits_text = "\n".join(config["benefits"])
        embed.add_field(
            name="💎 Exclusive Benefits",
            value=benefits_text,
            inline=False
        )
        
        embed.add_field(
            name="💰 Price",
            value=f"**{config['price']}**",
            inline=True
        )
        
        embed.add_field(
            name="🚀 Get Started",
            value=f"[Sign Up Here!]({config['signup_url']})",
            inline=True
        )
        
        embed.add_field(
            name="📋 Important",
            value="Don't forget to submit proof of payment at the end to get immediate access!",
            inline=False
        )
        
        embed.set_footer(text="Elevate your RIA experience today!")
        embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
        
        # Create view with purchase button
        class MembershipPanelView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=None)  # Persistent view
                
            @discord.ui.button(label="💎 Buy RIA Premium - $3/month", style=discord.ButtonStyle.primary, emoji="🛒")
            async def purchase_premium(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                config = MEMBERSHIP_CONFIG["ria_premium"]
                
                # Check if user already has the role
                premium_role = button_interaction.guild.get_role(config["role_id"])
                if premium_role and premium_role in button_interaction.user.roles:
                    await button_interaction.response.send_message("✅ You already have RIA Premium membership!", ephemeral=True)
                    return
                
                # Create purchase embed
                purchase_embed = discord.Embed(
                    title="💎 Purchase RIA Premium Membership",
                    description=f"**Ready to upgrade your RIA experience?**\n\nPrice: **{config['price']}**",
                    color=0x00FF00
                )
                
                purchase_embed.add_field(
                    name="🎁 What You'll Get",
                    value="\n".join(config["benefits"]),
                    inline=False
                )
                
                purchase_embed.add_field(
                    name="💳 Complete Your Purchase",
                    value=f"**[🔗 Sign Up Now for ONLY $3/month!]({config['signup_url']})**\n\n```Steps to complete:\n1. Fill out the signup form\n2. Submit proof of payment\n3. Get immediate access!```",
                    inline=False
                )
                
                purchase_embed.set_footer(text="Elevate your RIA experience today!")
                
                await button_interaction.response.send_message(embed=purchase_embed, ephemeral=True)
            
            @discord.ui.button(label="ℹ️ Check My Membership", style=discord.ButtonStyle.secondary)
            async def check_membership(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                await my_membership.callback(button_interaction)

        view = MembershipPanelView()
        await interaction.response.send_message("✅ Creating membership panel...", ephemeral=True)
        await interaction.followup.send(embed=embed, view=view)

    except Exception as e:
        print(f"Error in membership_panel: {e}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred.", ephemeral=True)
        except:
            pass

@bot.tree.command(name="membership_stats", description="View membership statistics (Admin Only)")
async def membership_stats(interaction: discord.Interaction):
    """View membership statistics for admins"""
    try:
        if not interaction.guild_id:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
            return

        # Check admin permissions
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ This command requires Administrator permissions!", ephemeral=True)
            return

        guild = interaction.guild
        config = MEMBERSHIP_CONFIG["ria_premium"]
        
        # Get the premium role
        premium_role = guild.get_role(config["role_id"])
        if not premium_role:
            await interaction.response.send_message("❌ Premium membership role not found!", ephemeral=True)
            return

        # Count members with premium role
        premium_members = [member for member in guild.members if premium_role in member.roles and not member.bot]
        total_members = len([member for member in guild.members if not member.bot])
        
        # Calculate statistics
        premium_percentage = (len(premium_members) / total_members * 100) if total_members > 0 else 0
        
        embed = discord.Embed(
            title="📊 Membership Statistics",
            description=f"Statistics for **{guild.name}**",
            color=0x0099FF
        )
        
        embed.add_field(
            name="💎 RIA Premium Members",
            value=f"**{len(premium_members)}** members\n({premium_percentage:.1f}% of server)",
            inline=True
        )
        
        embed.add_field(
            name="👥 Total Members",
            value=f"**{total_members}** members",
            inline=True
        )
        
        embed.add_field(
            name="💰 Monthly Revenue",
            value=f"**${len(premium_members) * 3}** estimated",
            inline=True
        )
        
        # Show recent premium members (last 10)
        if premium_members:
            recent_members = sorted(premium_members, key=lambda m: m.joined_at or datetime.min, reverse=True)[:10]
            members_list = "\n".join([f"• {member.mention}" for member in recent_members])
            embed.add_field(
                name="🔥 Recent Premium Members",
                value=members_list,
                inline=False
            )
        
        embed.set_footer(text=f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        embed.set_thumbnail(url=guild.icon.url if guild.icon else None)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        print(f"Error in membership_stats: {e}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred.", ephemeral=True)
        except:
            pass

@bot.tree.command(name="list_premium_members", description="List all premium members (Admin Only)")
async def list_premium_members(interaction: discord.Interaction):
    """List all premium members for admins"""
    try:
        if not interaction.guild_id:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
            return

        # Check admin permissions
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ This command requires Administrator permissions!", ephemeral=True)
            return

        guild = interaction.guild
        config = MEMBERSHIP_CONFIG["ria_premium"]
        
        # Get the premium role
        premium_role = guild.get_role(config["role_id"])
        if not premium_role:
            await interaction.response.send_message("❌ Premium membership role not found!", ephemeral=True)
            return

        # Get all premium members
        premium_members = [member for member in guild.members if premium_role in member.roles and not member.bot]
        
        if not premium_members:
            await interaction.response.send_message("No premium members found.", ephemeral=True)
            return

        embed = discord.Embed(
            title="💎 RIA Premium Members",
            description=f"Total Premium Members: **{len(premium_members)}**",
            color=0xFFD700
        )

        # Split members into chunks of 20 for multiple fields
        chunk_size = 20
        for i in range(0, len(premium_members), chunk_size):
            chunk = premium_members[i:i+chunk_size]
            member_list = "\n".join([f"• {member.mention} ({member.display_name})" for member in chunk])
            
            field_name = f"Members {i+1}-{min(i+chunk_size, len(premium_members))}"
            embed.add_field(name=field_name, value=member_list, inline=False)

        embed.set_footer(text=f"Use /grant_membership or /revoke_membership to manage members")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        print(f"Error in list_premium_members: {e}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred.", ephemeral=True)
        except:
            pass

@bot.tree.command(name="membership_audit", description="Audit membership permissions and setup (Admin Only)")
async def membership_audit(interaction: discord.Interaction):
    """Audit membership system for admins"""
    try:
        if not interaction.guild_id:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
            return

        # Check admin permissions
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ This command requires Administrator permissions!", ephemeral=True)
            return

        guild = interaction.guild
        config = MEMBERSHIP_CONFIG["ria_premium"]
        
        embed = discord.Embed(
            title="🔍 Membership System Audit",
            description="System status and configuration check",
            color=0x0099FF
        )
        
        # Check premium role
        premium_role = guild.get_role(config["role_id"])
        if premium_role:
            embed.add_field(
                name="✅ Premium Role",
                value=f"**{premium_role.name}** (ID: {premium_role.id})\nPosition: {premium_role.position}\nMembers: {len(premium_role.members)}",
                inline=False
            )
        else:
            embed.add_field(
                name="❌ Premium Role",
                value=f"Role ID {config['role_id']} not found!",
                inline=False
            )
        
        # Check bot permissions
        bot_member = guild.get_member(bot.user.id)
        can_manage_roles = bot_member.guild_permissions.manage_roles if bot_member else False
        can_send_messages = bot_member.guild_permissions.send_messages if bot_member else False
        
        permissions_status = "✅" if (can_manage_roles and can_send_messages) else "⚠️"
        embed.add_field(
            name=f"{permissions_status} Bot Permissions",
            value=f"Manage Roles: {'✅' if can_manage_roles else '❌'}\nSend Messages: {'✅' if can_send_messages else '❌'}",
            inline=True
        )
        
        # Check signup URL
        url_status = "✅" if config.get('signup_url') and config['signup_url'] != '#' else "⚠️"
        embed.add_field(
            name=f"{url_status} Signup URL",
            value="Configured" if url_status == "✅" else "Not configured",
            inline=True
        )
        
        # Add configuration summary
        embed.add_field(
            name="⚙️ Configuration",
            value=f"**Price:** {config['price']}\n**Benefits:** {len(config['benefits'])} configured",
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        print(f"Error in membership_audit: {e}")
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