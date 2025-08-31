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
            if 'ticket_counter' not in data:
                data['ticket_counter'] = 1
            if 'active_tickets' not in data:
                data['active_tickets'] = {}
            if 'ticket_settings' not in data:
                data['ticket_settings'] = {
                    'support_role_id': None,
                    'admin_role_id': None,
                    'category_id': None,
                    'log_channel_id': None,
                    'welcome_message': 'Thank you for creating a ticket! A staff member will be with you shortly.'
                }
            if 'automod_words' not in data:
                data['automod_words'] = []
            if 'automod_enabled' not in data:
                data['automod_enabled'] = True
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        default_data = {
            "ticket_counter": 1,
            "active_tickets": {},
            "stored_embeds": {},
            "embed_counter": 1,
            "ticket_settings": {
                "support_role_id": None,
                "admin_role_id": None,
                "category_id": None,
                "log_channel_id": None,
                "welcome_message": "Thank you for creating a ticket! A staff member will be with you shortly."
            },
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
            'author': self.embed_data.get('author'),
            'has_ticket_system': self.embed_data.get('has_ticket_system', False),
            'ticket_button_text': self.embed_data.get('ticket_button_text', 'Create Ticket'),
            'ticket_category_id': self.embed_data.get('ticket_category_id')
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

class TicketModal(discord.ui.Modal, title="Ticket System Settings"):
    def __init__(self, embed_data):
        super().__init__()
        self.embed_data = embed_data

        self.button_text.default = embed_data.get('ticket_button_text', 'Create Ticket')

    button_text = discord.ui.TextInput(
        label="Ticket Button Text",
        placeholder="Create Ticket",
        max_length=80,
        required=False
    )

    category_id = discord.ui.TextInput(
        label="Category ID (optional)",
        placeholder="Right-click category > Copy ID",
        max_length=20,
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        self.embed_data['has_ticket_system'] = True
        self.embed_data['ticket_button_text'] = str(self.button_text.value) if self.button_text.value else 'Create Ticket'

        if self.category_id.value:
            try:
                self.embed_data['ticket_category_id'] = int(self.category_id.value)
            except ValueError:
                pass

        view = EmbedOptionsView(self.embed_data)
        await interaction.response.send_message("Ticket system configured! Continue editing:", view=view, ephemeral=True)



class EmbedOptionsView(discord.ui.View):
    def __init__(self, embed_data, editing_embed_id=None):
        super().__init__(timeout=300)
        self.embed_data = embed_data
        self.editing_embed_id = editing_embed_id

    @discord.ui.button(label="Add Field", style=discord.ButtonStyle.primary, emoji="📝")
    async def add_field(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = FieldModal(self.embed_data)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Add Image", style=discord.ButtonStyle.secondary, emoji="🖼️")
    async def add_image(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = ImageModal(self.embed_data)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Add Author", style=discord.ButtonStyle.secondary, emoji="👤")
    async def add_author(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = AuthorModal(self.embed_data)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Ticket System", style=discord.ButtonStyle.green, emoji="🎫")
    async def add_ticket_system(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = TicketModal(self.embed_data)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Preview", style=discord.ButtonStyle.secondary, emoji="👁️")
    async def preview_embed(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = create_embed_from_data(self.embed_data)
        view = None

        if self.embed_data.get('has_ticket_system'):
            button_text = self.embed_data.get('ticket_button_text', 'Create Ticket')
            view = TicketView(button_text)

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
        view = None

        if self.embed_data.get('has_ticket_system'):
            button_text = self.embed_data.get('ticket_button_text', 'Create Ticket')
            view = TicketView(button_text)

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
        await interaction.followup.send(embed=embed, view=view)

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

class TicketView(discord.ui.View):
    def __init__(self, button_text="Create Ticket"):
        super().__init__(timeout=None)
        self.button_text = button_text

    @discord.ui.button(label="Create Ticket", style=discord.ButtonStyle.primary, emoji="🎫")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_data()

        # Check if user already has a ticket
        user_id = str(interaction.user.id)
        if user_id in data['active_tickets']:
            await interaction.response.send_message("You already have an active ticket!", ephemeral=True)
            return

        # Create ticket channel
        guild = interaction.guild
        category = None

        # Use configured category or create default
        if data['ticket_settings'].get('category_id'):
            category = guild.get_channel(data['ticket_settings']['category_id'])

        if not category:
            for cat in guild.categories:
                if cat.name.lower() == "tickets":
                    category = cat
                    break

        if not category:
            category = await guild.create_category("Tickets")

        # Create channel with proper permissions
        channel_name = f"ticket-{data['ticket_counter']}"
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }

        # Add support role permissions if configured
        if data['ticket_settings'].get('support_role_id'):
            support_role = guild.get_role(data['ticket_settings']['support_role_id'])
            if support_role:
                overwrites[support_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        # Add admin role permissions if configured
        if data['ticket_settings'].get('admin_role_id'):
            admin_role = guild.get_role(data['ticket_settings']['admin_role_id'])
            if admin_role:
                overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)

        ticket_channel = await guild.create_text_channel(
            channel_name,
            category=category,
            overwrites=overwrites
        )

        # Create ticket embed
        embed = discord.Embed(
            title="🎫 Support Ticket",
            description=f"Hello {interaction.user.mention}!\n\n{data['ticket_settings']['welcome_message']}\n\n**Ticket ID:** {data['ticket_counter']}",
            color=0x00ff00,
            timestamp=datetime.now()
        )
        embed.set_footer(text=f"Ticket created by {interaction.user}")

        close_view = TicketCloseView(user_id, data['ticket_counter'])
        await ticket_channel.send(embed=embed, view=close_view)

        # Update data
        data['active_tickets'][user_id] = {
            'channel_id': ticket_channel.id,
            'ticket_id': data['ticket_counter'],
            'created_at': datetime.now().isoformat()
        }
        data['ticket_counter'] += 1
        save_data(data)

        # Log ticket creation
        if data['ticket_settings'].get('log_channel_id'):
            log_channel = guild.get_channel(data['ticket_settings']['log_channel_id'])
            if log_channel:
                log_embed = discord.Embed(
                    title="📊 Ticket Created",
                    description=f"**User:** {interaction.user.mention}\n**Channel:** {ticket_channel.mention}\n**ID:** {data['ticket_counter'] - 1}",
                    color=0x00ff00,
                    timestamp=datetime.now()
                )
                await log_channel.send(embed=log_embed)

        await interaction.response.send_message(f"Ticket created! {ticket_channel.mention}", ephemeral=True)

class TicketCloseView(discord.ui.View):
    def __init__(self, user_id, ticket_id):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.ticket_id = ticket_id

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, emoji="🔒")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_data()

        # Log ticket closure
        guild = interaction.guild
        if data['ticket_settings'].get('log_channel_id'):
            log_channel = guild.get_channel(data['ticket_settings']['log_channel_id'])
            if log_channel:
                log_embed = discord.Embed(
                    title="📊 Ticket Closed",
                    description=f"**Closed by:** {interaction.user.mention}\n**Channel:** {interaction.channel.mention}\n**ID:** {self.ticket_id}",
                    color=0xff0000,
                    timestamp=datetime.now()
                )
                await log_channel.send(embed=log_embed)

        # Remove from active tickets
        if self.user_id in data['active_tickets']:
            del data['active_tickets'][self.user_id]
            save_data(data)

        embed = discord.Embed(
            title="🔒 Ticket Closed",
            description="This ticket will be deleted in 5 seconds.",
            color=0xff0000
        )

        await interaction.response.send_message(embed=embed)
        await asyncio.sleep(5)
        await interaction.channel.delete()

    @discord.ui.button(label="Add User", style=discord.ButtonStyle.secondary, emoji="➕")
    async def add_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = AddUserModal(interaction.channel)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Remove User", style=discord.ButtonStyle.secondary, emoji="➖")
    async def remove_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = RemoveUserModal(interaction.channel)
        await interaction.response.send_modal(modal)

class AddUserModal(discord.ui.Modal, title="Add User to Ticket"):
    def __init__(self, channel):
        super().__init__()
        self.channel = channel

    user_input = discord.ui.TextInput(
        label="User ID or Mention",
        placeholder="@user or 123456789012345678",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            user_id = self.user_input.value.strip()
            if user_id.startswith('<@') and user_id.endswith('>'):
                user_id = user_id[2:-1]
                if user_id.startswith('!'):
                    user_id = user_id[1:]

            user = interaction.guild.get_member(int(user_id))
            if user:
                await self.channel.set_permissions(user, read_messages=True, send_messages=True)
                await interaction.response.send_message(f"✅ Added {user.mention} to the ticket!", ephemeral=True)
            else:
                await interaction.response.send_message("❌ User not found!", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Invalid user ID!", ephemeral=True)

class RemoveUserModal(discord.ui.Modal, title="Remove User from Ticket"):
    def __init__(self, channel):
        super().__init__()
        self.channel = channel

    user_input = discord.ui.TextInput(
        label="User ID or Mention",
        placeholder="@user or 123456789012345678",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            user_id = self.user_input.value.strip()
            if user_id.startswith('<@') and user_id.endswith('>'):
                user_id = user_id[2:-1]
                if user_id.startswith('!'):
                    user_id = user_id[1:]

            user = interaction.guild.get_member(int(user_id))
            if user:
                await self.channel.set_permissions(user, overwrite=None)
                await interaction.response.send_message(f"✅ Removed {user.mention} from the ticket!", ephemeral=True)
            else:
                await interaction.response.send_message("❌ User not found!", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Invalid user ID!", ephemeral=True)



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
        info_embed.add_field(name="Has Ticket System", value="Yes" if embed_data.get('has_ticket_system') else "No", inline=True)
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
        view = None

        if embed_data.get('has_ticket_system'):
            button_text = embed_data.get('ticket_button_text', 'Create Ticket')
            view = TicketView(button_text)

        # Send the embed to the channel
        if view is not None:
            await interaction.response.send_message(embed=embed, view=view)
        else:
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

# Slash Commands
@bot.tree.command(name="create_embed", description="Create a custom embed message")
async def create_embed(interaction: discord.Interaction):
    if interaction.response.is_done():
        return

    modal = EmbedModal()
    await interaction.response.send_modal(modal)

@bot.tree.command(name="edit_embed", description="Edit an existing embed")
async def edit_embed(interaction: discord.Interaction):
    if interaction.response.is_done():
        return

    data = load_data()

    if not data.get('stored_embeds') or len(data['stored_embeds']) == 0:
        await interaction.response.send_message("No embeds stored! Use `/create_embed` to create one first.", ephemeral=True)
        return

    view = EditEmbedSelectView(data['stored_embeds'])
    await interaction.response.send_message(f"**Select Embed to Edit ({len(data['stored_embeds'])} available):**", view=view, ephemeral=True)

@bot.tree.command(name="list_embeds", description="List all stored embeds")
async def list_embeds(interaction: discord.Interaction):
    if interaction.response.is_done():
        return

    data = load_data()

    if not data.get('stored_embeds') or len(data['stored_embeds']) == 0:
        await interaction.response.send_message("No embeds stored! Use `/create_embed` to create one.", ephemeral=True)
        return

    view = EmbedSelectView(data['stored_embeds'])
    await interaction.response.send_message(f"**Stored Embeds ({len(data['stored_embeds'])} total):**\nSelect an embed to view details:", view=view, ephemeral=True)

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



@bot.tree.command(name="ticket_config", description="Configure ticket system settings")
async def ticket_config(interaction: discord.Interaction, support_role: discord.Role = None, admin_role: discord.Role = None, category: discord.CategoryChannel = None, log_channel: discord.TextChannel = None, welcome_message: str = None):
    data = load_data()

    if support_role:
        data['ticket_settings']['support_role_id'] = support_role.id

    if admin_role:
        data['ticket_settings']['admin_role_id'] = admin_role.id

    if category:
        data['ticket_settings']['category_id'] = category.id

    if log_channel:
        data['ticket_settings']['log_channel_id'] = log_channel.id

    if welcome_message:
        data['ticket_settings']['welcome_message'] = welcome_message

    save_data(data)

    embed = discord.Embed(
        title="🎫 Ticket Configuration Updated",
        color=0x00ff00
    )
    embed.add_field(name="Support Role", value=support_role.mention if support_role else "Not set", inline=True)
    embed.add_field(name="Admin Role", value=admin_role.mention if admin_role else "Not set", inline=True)
    embed.add_field(name="Category", value=category.mention if category else "Not set", inline=True)
    embed.add_field(name="Log Channel", value=log_channel.mention if log_channel else "Not set", inline=True)
    embed.add_field(name="Welcome Message", value=welcome_message if welcome_message else data['ticket_settings']['welcome_message'], inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="automod", description="Manage auto-moderation settings")
async def automod(interaction: discord.Interaction, action: str, word: str = None):
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

@bot.tree.command(name="ticket_list", description="List all active tickets")
async def ticket_list(interaction: discord.Interaction):
    data = load_data()

    if not data['active_tickets']:
        await interaction.response.send_message("No active tickets!", ephemeral=True)
        return

    embed = discord.Embed(
        title="🎫 Active Tickets",
        color=0x0099ff
    )

    for user_id, ticket_info in data['active_tickets'].items():
        user = interaction.guild.get_member(int(user_id))
        channel = interaction.guild.get_channel(ticket_info['channel_id'])

        if user and channel:
            embed.add_field(
                name=f"Ticket #{ticket_info['ticket_id']}",
                value=f"**User:** {user.mention}\n**Channel:** {channel.mention}\n**Created:** {ticket_info['created_at'][:10]}",
                inline=True
            )

    await interaction.response.send_message(embed=embed, ephemeral=True)

# Run the bot
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
if TOKEN:
    bot.run(TOKEN)
else:
    print("❌ DISCORD_BOT_TOKEN not found in environment variables")
    print("Please add your Discord bot token to the environment variables.")