
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
            return json.load(f)
    except FileNotFoundError:
        return {
            "ticket_counter": 1,
            "active_tickets": {},
            "stored_embeds": {},
            "embed_counter": 1
        }

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

class EmbedModal(discord.ui.Modal, title="Create Embed"):
    def __init__(self, embed_data=None):
        super().__init__()
        self.embed_data = embed_data or {}
        
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
        
        view = EmbedOptionsView(embed_data)
        await interaction.response.send_message("Embed created! Choose additional options:", view=view, ephemeral=True)

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
    def __init__(self, embed_data):
        super().__init__(timeout=300)
        self.embed_data = embed_data

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
            view = TicketView()
            
        await interaction.response.send_message("**Preview:**", embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="Send Embed", style=discord.ButtonStyle.success, emoji="✅")
    async def send_embed(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = create_embed_from_data(self.embed_data)
        view = None
        
        if self.embed_data.get('has_ticket_system'):
            view = TicketView()
        
        # Save embed
        data = load_data()
        embed_id = f"embed_{data['embed_counter']}"
        data['stored_embeds'][embed_id] = self.embed_data
        data['embed_counter'] += 1
        save_data(data)
        
        await interaction.response.send_message(f"Embed sent! (ID: {embed_id})", ephemeral=True)
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
    def __init__(self):
        super().__init__(timeout=None)

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
        
        # Try to find or create category
        for cat in guild.categories:
            if cat.name.lower() == "tickets":
                category = cat
                break
        
        if not category:
            category = await guild.create_category("Tickets")
        
        # Create channel
        channel_name = f"ticket-{data['ticket_counter']}"
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        ticket_channel = await guild.create_text_channel(
            channel_name,
            category=category,
            overwrites=overwrites
        )
        
        # Create ticket embed
        embed = discord.Embed(
            title="🎫 Support Ticket",
            description=f"Hello {interaction.user.mention}!\n\nThank you for creating a ticket. A staff member will be with you shortly.\n\n**Ticket ID:** {data['ticket_counter']}",
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
        
        await interaction.response.send_message(f"Ticket created! {ticket_channel.mention}", ephemeral=True)

class TicketCloseView(discord.ui.View):
    def __init__(self, user_id, ticket_id):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.ticket_id = ticket_id

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, emoji="🔒")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_data()
        
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

@bot.tree.command(name="create_embed", description="Create a custom embed message")
async def create_embed(interaction: discord.Interaction):
    modal = EmbedModal()
    await interaction.response.send_modal(modal)

@bot.tree.command(name="edit_embed", description="Edit an existing embed")
async def edit_embed(interaction: discord.Interaction, embed_id: str):
    data = load_data()
    
    if embed_id not in data['stored_embeds']:
        await interaction.response.send_message("Embed not found!", ephemeral=True)
        return
    
    embed_data = data['stored_embeds'][embed_id]
    modal = EmbedModal(embed_data)
    await interaction.response.send_modal(modal)

@bot.tree.command(name="list_embeds", description="List all stored embeds")
async def list_embeds(interaction: discord.Interaction):
    data = load_data()
    
    if not data['stored_embeds']:
        await interaction.response.send_message("No embeds stored!", ephemeral=True)
        return
    
    embed_list = "\n".join([f"**{embed_id}**: {embed_data.get('title', 'No title')}" 
                           for embed_id, embed_data in data['stored_embeds'].items()])
    
    embed = discord.Embed(
        title="📋 Stored Embeds",
        description=embed_list,
        color=0x0099ff
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Run the bot
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
if TOKEN:
    bot.run(TOKEN)
else:
    print("❌ DISCORD_BOT_TOKEN not found in environment variables")
    print("Please add your Discord bot token to the environment variables.")
