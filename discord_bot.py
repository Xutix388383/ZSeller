import discord
from discord.ext import commands, tasks
import json
import os
from datetime import datetime
import asyncio
import aiohttp
import re

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Enhanced channel and member detection functions
def get_channels_by_name(guild):
    """Auto-detect channels by name patterns with enhanced matching"""
    channels = {}

    if not guild:
        return channels

    # Define comprehensive channel name patterns
    channel_patterns = {
        'support': ['support', 'help', 'ticket', 'assistance', 'staff', 'admin', 'mod', 'report', 'contact'],
        'stk': ['stk', 'gang', 'recruitment', 'join', 'member', 'recruit', 'crew', 'team', 'clan'],
        'tos': ['tos', 'terms', 'legal', 'policy', 'agreement', 'conditions', 'service'],
        'rules': ['rules', 'guidelines', 'info', 'information', 'guide', 'regulation', 'law'],
        'news': ['news', 'announcements', 'updates', 'notice', 'alert', 'broadcast', 'announce'],
        'welcome': ['welcome', 'general', 'main', 'lobby', 'entrance', 'start', 'begin', 'intro'],
        'shop': ['shop', 'store', 'buy', 'sell', 'market', 'trading', 'trade', 'purchase'],
        'chat': ['chat', 'talk', 'discuss', 'conversation', 'social'],
        'bot': ['bot', 'command', 'cmd', 'control', 'automation'],
        'log': ['log', 'logs', 'audit', 'record', 'history', 'track'],
        'voice': ['voice', 'vc', 'talk', 'speak', 'audio'],
        'meme': ['meme', 'memes', 'funny', 'humor', 'joke', 'fun'],
        'media': ['media', 'images', 'pics', 'photos', 'gallery', 'share']
    }

    # Get all text channels in the guild
    detected_count = 0
    for channel in guild.text_channels:
        if not channel.permissions_for(guild.me).view_channel:
            continue  # Skip channels bot can't see

        channel_name_lower = channel.name.lower()
        # Enhanced cleaning - remove emojis, special chars, but keep essential separators
        clean_name = ''.join(c for c in channel_name_lower if c.isalnum() or c in ['-', '_', ' '])

        # Split by common separators for better word matching
        name_words = clean_name.replace('-', ' ').replace('_', ' ').split()

        # Check each pattern category with enhanced matching
        for category, patterns in channel_patterns.items():
            if category in channels:  # Skip if already found
                continue

            for pattern in patterns:
                # Multiple matching strategies
                if (pattern in clean_name or
                    pattern in channel_name_lower or
                    any(pattern in word for word in name_words) or
                    any(word.startswith(pattern) for word in name_words) or
                    any(word.endswith(pattern) for word in name_words)):

                    channels[category] = channel.id
                    print(f"  ✅ Detected {category}: #{channel.name} (ID: {channel.id})")
                    detected_count += 1
                    break

    # Also detect by channel position/category for common patterns
    for category in guild.categories:
        cat_name = category.name.lower()
        if 'support' in cat_name and 'support' not in channels:
            for channel in category.text_channels:
                if channel.permissions_for(guild.me).view_channel:
                    channels['support'] = channel.id
                    print(f"  ✅ Detected support (by category): #{channel.name}")
                    detected_count += 1
                    break

    print(f"  📊 Total channels detected: {detected_count}")
    return channels

def get_key_members(guild):
    """Auto-detect key members (staff, moderators, admins, etc.)"""
    key_members = {
        'owner': None,
        'admins': [],
        'moderators': [],
        'staff': [],
        'bots': [],
        'active_members': [],
        'new_members': []
    }

    if not guild:
        return key_members

    try:
        # Get guild owner
        if guild.owner:
            key_members['owner'] = {
                'id': guild.owner.id,
                'name': guild.owner.display_name,
                'username': str(guild.owner),
                'joined': guild.owner.joined_at.isoformat() if guild.owner.joined_at else None
            }
            print(f"  👑 Owner: {guild.owner.display_name}")

        # Analyze members by roles and permissions
        admin_count = 0
        mod_count = 0
        staff_count = 0
        bot_count = 0

        for member in guild.members:
            try:
                # Skip if can't access member data
                if not member:
                    continue

                member_data = {
                    'id': member.id,
                    'name': member.display_name,
                    'username': str(member),
                    'joined': member.joined_at.isoformat() if member.joined_at else None,
                    'roles': [role.name for role in member.roles if role.name != '@everyone']
                }

                # Categorize bots
                if member.bot:
                    key_members['bots'].append(member_data)
                    bot_count += 1
                    continue

                # Check for admin permissions
                if member.guild_permissions.administrator and not member.bot:
                    key_members['admins'].append(member_data)
                    admin_count += 1
                    print(f"  🛡️ Admin: {member.display_name}")

                # Check for moderator permissions
                elif (member.guild_permissions.manage_messages or
                      member.guild_permissions.manage_channels or
                      member.guild_permissions.kick_members) and not member.bot:
                    key_members['moderators'].append(member_data)
                    mod_count += 1
                    print(f"  🔨 Moderator: {member.display_name}")

                # Check for staff roles by name
                elif any(role.name.lower() in ['staff', 'helper', 'support', 'team']
                         for role in member.roles) and not member.bot:
                    key_members['staff'].append(member_data)
                    staff_count += 1
                    print(f"  👥 Staff: {member.display_name}")

                # Detect active members (recent joiners or high role count)
                elif len(member.roles) > 3 and not member.bot:
                    key_members['active_members'].append(member_data)

                # Detect new members (joined recently)
                elif member.joined_at and not member.bot:
                    from datetime import datetime, timedelta
                    if datetime.now(member.joined_at.tzinfo) - member.joined_at < timedelta(days=7):
                        key_members['new_members'].append(member_data)

            except Exception as e:
                # Skip members that cause errors (permissions, etc.)
                continue

        print(f"  Member Analysis:")
        print(f"    👑 Owner: 1")
        print(f"    🛡️ Admins: {admin_count}")
        print(f"    🔨 Moderators: {mod_count}")
        print(f"    👥 Staff: {staff_count}")
        print(f"    🤖 Bots: {bot_count}")
        print(f"    ⭐ Active Members: {len(key_members['active_members'])}")
        print(f"    🆕 New Members: {len(key_members['new_members'])}")
        print(f"    📈 Total Members: {guild.member_count}")

    except Exception as e:
        print(f"  ⚠️ Error analyzing members: {e}")

    return key_members

def analyze_guild_structure(guild):
    """Comprehensive guild analysis"""
    if not guild:
        return {}

    try:
        analysis = {
            'guild_info': {
                'name': guild.name,
                'id': guild.id,
                'member_count': guild.member_count,
                'created_at': guild.created_at.isoformat() if guild.created_at else None,
                'verification_level': str(guild.verification_level),
                'boost_count': guild.premium_subscription_count or 0,
                'boost_tier': guild.premium_tier or 0,
                'features': list(guild.features) if hasattr(guild, 'features') and guild.features else []
            },
            'channels': {
                'total_text': len(guild.text_channels),
                'total_voice': len(guild.voice_channels),
                'total_categories': len(guild.categories),
                'detected_channels': get_channels_by_name(guild)
            },
            'roles': {
                'total_roles': len(guild.roles),
                'role_hierarchy': [{'name': role.name, 'members': len(role.members), 'permissions': len([p for p, v in role.permissions if v])}
                                 for role in sorted(guild.roles, key=lambda r: r.position, reverse=True)[:10]]
            },
            'members': get_key_members(guild)
        }
    except Exception as analysis_error:
        print(f"⚠️ Error in guild analysis: {analysis_error}")
        # Return minimal analysis on error
        analysis = {
            'guild_info': {
                'name': guild.name,
                'id': guild.id,
                'member_count': guild.member_count,
                'features': []
            },
            'channels': {
                'total_text': len(guild.text_channels),
                'total_voice': len(guild.voice_channels),
                'total_categories': len(guild.categories),
                'detected_channels': get_channels_by_name(guild)
            },
            'roles': {'total_roles': len(guild.roles), 'role_hierarchy': []},
            'members': {'owner': None, 'admins': [], 'moderators': [], 'staff': [], 'bots': [], 'active_members': [], 'new_members': []}
        }

    return analysis

# Global variables to store detected data
CHANNELS = {}
GUILD_ANALYSIS = {}

# Role IDs
STAFF_ROLE_ID = 1407347171795406919  # Admin role
OWNER_ROLE_ID = 1407347171056943214  # Owner role

# Ticket counter and data storage
TICKET_COUNTER = 1
ACTIVE_TICKETS = {}
ACTIVE_ORDER_TICKETS = {}
NEWS_DATA = {"title": "📰 Latest News", "content": "No news updates yet.", "last_updated": None}

# Load data from file if exists
def load_data():
    global TICKET_COUNTER, ACTIVE_TICKETS, ACTIVE_ORDER_TICKETS, NEWS_DATA
    try:
        if os.path.exists('bot_data.json'):
            with open('bot_data.json', 'r') as f:
                data = json.load(f)
                TICKET_COUNTER = data.get('ticket_counter', 1)
                ACTIVE_TICKETS = data.get('active_tickets', {})
                ACTIVE_ORDER_TICKETS = data.get('active_order_tickets', {})
                NEWS_DATA = data.get('news_data', NEWS_DATA)
    except Exception as e:
        print(f"Error loading data: {e}")

def save_data():
    try:
        data = {
            'ticket_counter': TICKET_COUNTER,
            'active_tickets': ACTIVE_TICKETS,
            'active_order_tickets': ACTIVE_ORDER_TICKETS,
            'news_data': NEWS_DATA
        }
        with open('bot_data.json', 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving data: {e}")

# Shop data
WEAPONS = [
    "GoldenButton", "GreenSwitch", "BlueTips/Switch", "OrangeButton", "BinaryTrigger",
    "YellowButtonSwitch", "FullyARP", "FullyDraco", "Fully-MicroAR", "Cyanbutton",
    "100RndTanG19", "300ARG", "VP9Scope", "MasterPiece30", "GSwitch",
    "G17WittaButton", "G19Switch", "G20Switch", "G21Switch", "G22 Switch",
    "G23 Switch", "G40 Switch", "G42 Switch", "Fully-FN", "BinaryARP",
    "BinaryDraco", "CustomAR9"
]

WATCHES = [
    "Cartier", "BlueFaceCartier", "White Richard Millie", "PinkRichard", "GreenRichard",
    "RedRichard", "BluRichard", "BlackOutMillie", "Red AP", "AP Watch", "Gold AP",
    "Red AP Watch", "CubanG AP", "CubanP AP", "CubanB AP", "Iced AP"
]

# New shop view with purchase and calculator buttons
class NewShopView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='Calculate your order then purchase', style=discord.ButtonStyle.primary, emoji='🧮', custom_id='new_shop_calculator')
    async def calculator(self, interaction: discord.Interaction, button: discord.ui.Button):
        calculator_view = CalculatorView()
        embed = discord.Embed(
            title="🛒 ZSupply Cart & Calculator",
            description="**Add items to your cart:**\n\n🛒 **Cart Total: $0.00**",
            color=0x00ff00
        )
        embed.add_field(
            name="🛒 Your Cart:",
            value="No items in cart yet",
            inline=False
        )
        embed.add_field(
            name="📝 How It Works:",
            value="1️⃣ Add items to your cart using buttons below\n2️⃣ Click 'Purchase Cart' when ready\n3️⃣ Your cart items will be sent in your ticket",
            inline=False
        )
        embed.set_footer(text="Add items to cart, then click Purchase Cart to order!")
        await interaction.response.send_message(embed=embed, view=calculator_view, ephemeral=True)

# Cart purchase modal for calculator orders
class CartPurchaseModal(discord.ui.Modal, title='Purchase Cart Items'):
    def __init__(self, cart_items, cart_total, cart_summary):
        super().__init__()
        self.cart_items = cart_items
        self.cart_total = cart_total
        self.cart_summary = cart_summary

    special_notes = discord.ui.TextInput(
        label='Any special requests or notes?',
        placeholder='Custom requirements, preferred delivery time, etc...',
        style=discord.TextStyle.paragraph,
        max_length=500,
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        global TICKET_COUNTER
        ticket_number = TICKET_COUNTER
        TICKET_COUNTER += 1

        # Create private ticket in specified channel
        PRIVATE_TICKET_CHANNEL_ID = 1408167680317325434
        ticket_channel = interaction.guild.get_channel(PRIVATE_TICKET_CHANNEL_ID)

        if not ticket_channel:
            await interaction.response.send_message("❌ Private ticket channel not found! Please contact an administrator.", ephemeral=True)
            return

        # Store ticket data
        ticket_id = f"cart_{ticket_number:04d}_{interaction.user.id}"
        ACTIVE_ORDER_TICKETS[ticket_id] = {
            'user_id': interaction.user.id,
            'ticket_number': ticket_number,
            'cart_items': self.cart_items,
            'cart_total': self.cart_total,
            'cart_summary': self.cart_summary,
            'special_notes': self.special_notes.value,
            'created_at': datetime.now().isoformat(),
            'channel_id': ticket_channel.id
        }
        save_data()

        # Create order embed for private channel
        embed = discord.Embed(
            title=f"🛒 Cart Order #{ticket_number:04d}",
            description=f"**Customer:** {interaction.user.mention} ({interaction.user.display_name})\n**User ID:** {interaction.user.id}",
            color=0x00ff00,
            timestamp=datetime.now()
        )

        embed.add_field(
            name="🛒 Cart Items & Total",
            value=f"```{self.cart_summary}```",
            inline=False
        )

        if self.special_notes.value:
            embed.add_field(
                name="📝 Special Notes",
                value=f"```{self.special_notes.value}```",
                inline=False
            )

        embed.add_field(
            name="💳 Payment Instructions",
            value=f"**Total Amount: ${self.cart_total:.2f}**\n\n**Send payment to:**\n• **CashApp:** https://cash.app/$EthanCreel1\n• **Apple Pay:** 7656156371\n\n**After payment, let us know in this ticket!**",
            inline=False
        )

        embed.add_field(
            name="📋 Next Steps",
            value="1️⃣ Send payment using methods above\n2️⃣ Confirm payment in this channel\n3️⃣ Staff will process your order\n4️⃣ Receive your items instantly",
            inline=False
        )

        embed.set_footer(text="ZSupply Cart Order System • Staff will assist you")

        # Create control view for staff
        view = PrivateTicketControlView(ticket_id)
        view.add_item(CalculatorButton())

        message = await ticket_channel.send(f"🔥 **NEW CART ORDER - Customer:** {interaction.user.mention}", embed=embed, view=view)

        # Store message ID
        ACTIVE_ORDER_TICKETS[ticket_id]['message_id'] = message.id
        save_data()

        await interaction.response.send_message(f"✅ Cart order created! Staff will assist you in the private channel.", ephemeral=True)

# New purchase modal for private tickets
class NewPurchaseModal(discord.ui.Modal, title='Create Purchase Order'):
    def __init__(self):
        super().__init__()

    item_selection = discord.ui.TextInput(
        label='What would you like to purchase?',
        placeholder='List the items/services you want to buy...',
        style=discord.TextStyle.paragraph,
        max_length=1000,
        required=True
    )

    special_notes = discord.ui.TextInput(
        label='Any special requests or notes?',
        placeholder='Custom requirements, preferred delivery time, etc...',
        style=discord.TextStyle.paragraph,
        max_length=500,
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        global TICKET_COUNTER
        ticket_number = TICKET_COUNTER
        TICKET_COUNTER += 1

        # Create private ticket in specified channel
        PRIVATE_TICKET_CHANNEL_ID = 1408167680317325434
        ticket_channel = interaction.guild.get_channel(PRIVATE_TICKET_CHANNEL_ID)

        if not ticket_channel:
            await interaction.response.send_message("❌ Private ticket channel not found! Please contact an administrator.", ephemeral=True)
            return

        # Store ticket data
        ticket_id = f"purchase_{ticket_number:04d}_{interaction.user.id}"
        ACTIVE_ORDER_TICKETS[ticket_id] = {
            'user_id': interaction.user.id,
            'ticket_number': ticket_number,
            'items': self.item_selection.value,
            'special_notes': self.special_notes.value,
            'created_at': datetime.now().isoformat(),
            'channel_id': ticket_channel.id
        }
        save_data()

        # Create order embed for private channel
        embed = discord.Embed(
            title=f"🎫 Purchase Order #{ticket_number:04d}",
            description=f"**Customer:** {interaction.user.mention} ({interaction.user.display_name})\n**User ID:** {interaction.user.id}",
            color=0x00ff00,
            timestamp=datetime.now()
        )

        embed.add_field(
            name="🛍️ Requested Items",
            value=f"```{self.item_selection.value}```",
            inline=False
        )

        if self.special_notes.value:
            embed.add_field(
                name="📝 Special Notes",
                value=f"```{self.special_notes.value}```",
                inline=False
            )

        embed.add_field(
            name="💳 Payment Instructions",
            value="**Please send payment to:**\n• **CashApp:** https://cash.app/$EthanCreel1\n• **Apple Pay:** 7656156371\n\n**After payment, type what you want in this ticket!**",
            inline=False
        )

        embed.add_field(
            name="📋 Next Steps",
            value="1️⃣ Calculate total using calculator button\n2️⃣ Send payment using methods above\n3️⃣ Type exactly what you want in this channel\n4️⃣ Staff will process your order",
            inline=False
        )

        embed.set_footer(text="ZSupply Private Order System • Staff will assist you")

        # Create control view for staff
        view = PrivateTicketControlView(ticket_id)
        view.add_item(CalculatorButton())

        message = await ticket_channel.send(f"🔥 **NEW ORDER - Customer:** {interaction.user.mention}", embed=embed, view=view)

        # Store message ID
        ACTIVE_ORDER_TICKETS[ticket_id]['message_id'] = message.id
        save_data()

        await interaction.response.send_message(f"✅ Private order ticket created! Staff will assist you in the private channel.", ephemeral=True)

# Calculator system
class CalculatorView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.total = 0.0
        self.items = []

    async def update_embed(self, interaction):
        embed = discord.Embed(
            title="🛒 ZSupply Cart & Calculator",
            description=f"**Add items to your cart:**\n\n🛒 **Cart Total: ${self.total:.2f}**",
            color=0x00ff00
        )

        if self.items:
            items_list = "\n".join([f"• {item['name']} - ${item['price']:.2f}" for item in self.items])
        else:
            items_list = "No items in cart yet"

        embed.add_field(
            name="🛒 Your Cart:",
            value=items_list,
            inline=False
        )
        
        embed.add_field(
            name="📝 How It Works:",
            value="1️⃣ Add items to your cart using buttons below\n2️⃣ Click 'Purchase Cart' when ready\n3️⃣ Your cart items will be sent in your ticket",
            inline=False
        )
        
        embed.set_footer(text="Add items to cart, then click Purchase Cart to order!")

        try:
            await interaction.response.edit_message(embed=embed, view=self)
        except:
            await interaction.edit_original_response(embed=embed, view=self)

    @discord.ui.button(label='Watch $1', style=discord.ButtonStyle.secondary)
    async def add_watch(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.items.append({"name": "Watch", "price": 1.0})
        self.total += 1.0
        await self.update_embed(interaction)

    @discord.ui.button(label='TB3 990k Bank $1', style=discord.ButtonStyle.secondary)
    async def add_tb3_990k_bank(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.items.append({"name": "TB3 990k Bank", "price": 1.0})
        self.total += 1.0
        await self.update_embed(interaction)

    @discord.ui.button(label='TB3 990k Clean $1', style=discord.ButtonStyle.secondary)
    async def add_tb3_990k_clean(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.items.append({"name": "TB3 990k Clean", "price": 1.0})
        self.total += 1.0
        await self.update_embed(interaction)

    @discord.ui.button(label='TB3 1.6M Bank (GP) $2', style=discord.ButtonStyle.secondary)
    async def add_tb3_16m_bank_gp(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.items.append({"name": "TB3 1.6M Bank (Gamepass Only)", "price": 2.0})
        self.total += 2.0
        await self.update_embed(interaction)

    @discord.ui.button(label='TB3 1.6M Clean (GP) $2', style=discord.ButtonStyle.secondary)
    async def add_tb3_16m_clean_gp(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.items.append({"name": "TB3 1.6M Clean (Gamepass Only)", "price": 2.0})
        self.total += 2.0
        await self.update_embed(interaction)

    @discord.ui.button(label='PS2 Million $1', style=discord.ButtonStyle.secondary)
    async def add_ps2_money(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.items.append({"name": "PS2 Money (1M)", "price": 1.0})
        self.total += 1.0
        await self.update_embed(interaction)

    @discord.ui.button(label='Safe Package $5', style=discord.ButtonStyle.secondary)
    async def add_safe_package(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.items.append({"name": "Safe Package", "price": 5.0})
        self.total += 5.0
        await self.update_embed(interaction)

    @discord.ui.button(label='Bag Package $3', style=discord.ButtonStyle.secondary)
    async def add_bag_package(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.items.append({"name": "Bag Package", "price": 3.0})
        self.total += 3.0
        await self.update_embed(interaction)

    @discord.ui.button(label='Trunk Package $2', style=discord.ButtonStyle.secondary)
    async def add_trunk_package(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.items.append({"name": "Trunk Package", "price": 2.0})
        self.total += 2.0
        await self.update_embed(interaction)

    @discord.ui.button(label='Max Account $3', style=discord.ButtonStyle.secondary)
    async def add_max_account(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.items.append({"name": "Max Account", "price": 3.0})
        self.total += 3.0
        await self.update_embed(interaction)

    @discord.ui.button(label='Stats + Money $6', style=discord.ButtonStyle.secondary)
    async def add_stats_money(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.items.append({"name": "Stats + Money", "price": 6.0})
        self.total += 6.0
        await self.update_embed(interaction)

    @discord.ui.button(label='Fully Stacked $8', style=discord.ButtonStyle.secondary)
    async def add_fully_stacked(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.items.append({"name": "Fully Stacked Account", "price": 8.0})
        self.total += 8.0
        await self.update_embed(interaction)

    @discord.ui.button(label='Rollback Account $10', style=discord.ButtonStyle.secondary)
    async def add_rollback(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.items.append({"name": "Rollback Account", "price": 10.0})
        self.total += 10.0
        await self.update_embed(interaction)

    @discord.ui.button(label='🗑️ Clear All', style=discord.ButtonStyle.danger, row=4)
    async def clear_all(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.items = []
        self.total = 0.0
        await self.update_embed(interaction)

    @discord.ui.button(label='↩️ Remove Last', style=discord.ButtonStyle.danger, row=4)
    async def remove_last(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.items:
            removed = self.items.pop()
            self.total -= removed['price']
            if self.total < 0:
                self.total = 0
        await self.update_embed(interaction)

    @discord.ui.button(label='🛒 Purchase Cart', style=discord.ButtonStyle.success, row=4)
    async def purchase_cart(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.items:
            await interaction.response.send_message("❌ Your cart is empty! Add items first.", ephemeral=True)
            return
        
        # Create cart summary for the modal
        cart_summary = "\n".join([f"• {item['name']} - ${item['price']:.2f}" for item in self.items])
        cart_summary += f"\n\nTotal: ${self.total:.2f}"
        
        # Pass cart data to purchase modal
        modal = CartPurchaseModal(self.items, self.total, cart_summary)
        await interaction.response.send_modal(modal)

# Calculator button for tickets
class CalculatorButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label='🧮 Calculator', style=discord.ButtonStyle.primary, emoji='🧮')

    async def callback(self, interaction: discord.Interaction):
        calculator_view = CalculatorView()
        embed = discord.Embed(
            title="🛒 ZSupply Cart & Calculator",
            description="**Add items to your cart:**\n\n🛒 **Cart Total: $0.00**",
            color=0x00ff00
        )
        embed.add_field(
            name="🛒 Your Cart:",
            value="No items in cart yet",
            inline=False
        )
        embed.add_field(
            name="📝 How It Works:",
            value="1️⃣ Add items to your cart using buttons below\n2️⃣ Click 'Purchase Cart' when ready\n3️⃣ Your cart items will be sent in your ticket",
            inline=False
        )
        embed.set_footer(text="Add items to cart, then click Purchase Cart to order!")
        await interaction.response.send_message(embed=embed, view=calculator_view, ephemeral=True)

# Private ticket control view
class PrivateTicketControlView(discord.ui.View):
    def __init__(self, ticket_id):
        super().__init__(timeout=None)
        self.ticket_id = ticket_id

    @discord.ui.button(label='Complete Order', style=discord.ButtonStyle.success, emoji='✅', custom_id='private_complete_order')
    async def complete_order(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._close_ticket(interaction, "completed")

    @discord.ui.button(label='Close Ticket', style=discord.ButtonStyle.danger, emoji='🔒', custom_id='private_close_ticket')
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._close_ticket(interaction, "closed")

    async def _close_ticket(self, interaction, action_type):
        """Handle ticket closing"""
        # Get ticket data
        ticket_data = ACTIVE_ORDER_TICKETS.get(self.ticket_id)
        if not ticket_data:
            await interaction.response.send_message("❌ Ticket data not found.", ephemeral=True)
            return

        # Create closure summary embed
        closure_embed = discord.Embed(
            title=f"🔒 Purchase Order #{ticket_data['ticket_number']:04d} - {action_type.title()}",
            description=f"**Customer:** <@{ticket_data['user_id']}>\n**Status:** {action_type.title()}",
            color=0x00ff00 if action_type == "completed" else 0xff0000,
            timestamp=datetime.now()
        )

        # Handle different ticket types
        if 'cart_summary' in ticket_data:
            closure_embed.add_field(
                name="🛒 Cart Order",
                value=f"```{ticket_data.get('cart_summary', 'No cart data')}```",
                inline=False
            )
        else:
            closure_embed.add_field(
                name="🛍️ Ordered Items",
                value=f"```{ticket_data.get('items', 'No items listed')}```",
                inline=False
            )

        if ticket_data.get('special_notes'):
            closure_embed.add_field(
                name="📝 Special Notes",
                value=f"```{ticket_data['special_notes']}```",
                inline=False
            )

        closure_embed.add_field(
            name="📊 Ticket Information",
            value=f"**Created:** <t:{int(datetime.fromisoformat(ticket_data['created_at']).timestamp())}:R>\n**Closed:** <t:{int(datetime.now().timestamp())}:R>\n**Handled By:** {interaction.user.mention}",
            inline=False
        )

        closure_embed.set_footer(text=f"ZSupply Order System • Ticket {action_type}")

        # Remove from active tickets
        if self.ticket_id in ACTIVE_ORDER_TICKETS:
            del ACTIVE_ORDER_TICKETS[self.ticket_id]
            save_data()

        # Send confirmation in same channel
        status_embed = discord.Embed(
            title=f"✅ Order {action_type.title()}",
            description=f"This order has been {action_type}. Thank you for using ZSupply!",
            color=0x00ff00 if action_type == "completed" else 0xff0000
        )

        # Update the original message to remove buttons
        try:
            await interaction.response.edit_message(embed=status_embed, view=None)
        except:
            await interaction.response.send_message(embed=status_embed)

# Keep old ShopMainView for backward compatibility
class ShopMainView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='🛒 Create Order', style=discord.ButtonStyle.success, emoji='🛒', custom_id='shop_create_order')
    async def create_order(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(PurchaseTicketModal("ZSupply Shop", "All Games Available"))

    @discord.ui.button(label='🎫 Support Ticket', style=discord.ButtonStyle.primary, emoji='🎫', custom_id='shop_support_ticket')
    async def support_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketModal())

    @discord.ui.button(label='⚔️ Join STK Gang', style=discord.ButtonStyle.secondary, emoji='⚔️', custom_id='shop_join_gang')
    async def join_gang(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            embed = discord.Embed(
                title="🎉 Welcome to STK Gang!",
                description="**You're about to join one of the most elite gangs!**\n\nMake sure you're ready to represent STK across all games.",
                color=0x00ff00
            )
            embed.add_field(
                name="👕 Remember Your Outfit",
                value="**SHIRT:** Green Varsity\n**PANTS:** Green Ripped Jeans",
                inline=False
            )
            embed.add_field(
                name="🔗 Join Our Gang Discord",
                value="**Click here to join:** https://discord.gg/7rG6jVTVmX",
                inline=False
            )
            embed.set_footer(text="STK Gang • Elite Members Only • Wear your colors with pride!")

            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            try:
                await interaction.response.send_message("✅ STK Gang link: https://discord.gg/7rG6jVTVmX", ephemeral=True)
            except:
                pass

# Purchase ticket system
class PurchaseTicketModal(discord.ui.Modal, title='Create Purchase Order'):
    def __init__(self, shop_name, product_info):
        super().__init__()
        self.shop_name = shop_name
        self.product_info = product_info

    product_selection = discord.ui.TextInput(
        label='What would you like to purchase?',
        placeholder='List the items/services you want to buy...',
        style=discord.TextStyle.paragraph,
        max_length=1000,
        required=True
    )

    special_requests = discord.ui.TextInput(
        label='Any special requests or notes?',
        placeholder='Custom requirements, preferred delivery time, etc...',
        style=discord.TextStyle.paragraph,
        max_length=500,
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        global TICKET_COUNTER
        ticket_number = TICKET_COUNTER
        TICKET_COUNTER += 1

        # Create order ticket channel
        ORDER_TICKET_CHANNEL_ID = 1407347196906573889
        ticket_channel = interaction.guild.get_channel(ORDER_TICKET_CHANNEL_ID)

        if not ticket_channel:
            await interaction.response.send_message("❌ Order channel not found! Please contact an administrator.", ephemeral=True)
            return

        # Store ticket data
        ticket_id = f"purchase_{ticket_number:04d}_{interaction.user.id}"
        ACTIVE_ORDER_TICKETS[ticket_id] = {
            'user_id': interaction.user.id,
            'ticket_number': ticket_number,
            'shop': self.shop_name,
            'products': self.product_selection.value,
            'special_requests': self.special_requests.value,
            'created_at': datetime.now().isoformat(),
            'channel_id': ticket_channel.id
        }
        save_data()

        # Create order embed
        embed = discord.Embed(
            title=f"🛒 Purchase Order #{ticket_number:04d}",
            description=f"**Customer:** {interaction.user.mention}\n**Shop:** {self.shop_name}",
            color=0x00ff00,
            timestamp=datetime.now()
        )

        embed.add_field(
            name="🛍️ Requested Products/Services",
            value=f"```{self.product_selection.value}```",
            inline=False
        )

        if self.special_requests.value:
            embed.add_field(
                name="📝 Special Requests",
                value=f"```{self.special_requests.value}```",
                inline=False
            )

        embed.add_field(
            name="💳 Payment Methods",
            value="• **CashApp:** https://cash.app/$EthanCreel1\n• **Apple Pay:** 7656156371\n• **PayPal:** Coming Soon (broken)",
            inline=False
        )

        embed.add_field(
            name="📋 Next Steps",
            value="1️⃣ Owner/Admin will calculate your total\n2️⃣ Complete payment using methods above\n3️⃣ Receive your order instantly\n4️⃣ Get setup support if needed",
            inline=False
        )

        embed.set_footer(text="ZSupply Order System • Owner/Admin will assist you")

        # Ping owner and admins
        ping_message = "**🔥 NEW PURCHASE ORDER - Owner/Admin assistance needed!**\n\n"
        if OWNER_ROLE_ID:
            ping_message += f"<@&{OWNER_ROLE_ID}> "
        if STAFF_ROLE_ID:
            ping_message += f"<@&{STAFF_ROLE_ID}>"

        view = OrderTicketControlView(ticket_id)
        message = await ticket_channel.send(ping_message, embed=embed, view=view)

        # Store message ID
        ACTIVE_ORDER_TICKETS[ticket_id]['message_id'] = message.id
        save_data()

        await interaction.response.send_message(f"✅ Purchase order created! Check {ticket_channel.mention} - Owner/Admin will assist you shortly!", ephemeral=True)

# Removed ShopPurchaseView - now using simple embeds with ticket system instructions

# Support ticket system
class TicketModal(discord.ui.Modal, title='Create Support Ticket'):
    def __init__(self):
        super().__init__()

    support_reason = discord.ui.TextInput(
        label='What do you need support with?',
        placeholder='Please describe your issue in detail...',
        style=discord.TextStyle.paragraph,
        max_length=1000,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        # Anti-spam check (basic)
        content = self.support_reason.value.lower()
        spam_keywords = ['spam', 'test', 'lol', 'hi', 'hello', 'test123']
        if any(keyword in content and len(content) < 10 for keyword in spam_keywords):
            await interaction.response.send_message("❌ Your ticket appears to be spam. Please provide a detailed description of your issue.", ephemeral=True)
            return

        global TICKET_COUNTER
        ticket_number = TICKET_COUNTER
        TICKET_COUNTER += 1

        # Create ticket channel
        guild = interaction.guild
        category = discord.utils.get(guild.categories, name="Support Tickets")
        if not category:
            category = await guild.create_category("Support Tickets")

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        # Add staff and owner permissions
        if STAFF_ROLE_ID:
            staff_role = guild.get_role(STAFF_ROLE_ID)
            if staff_role:
                overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        if OWNER_ROLE_ID:
            owner_role = guild.get_role(OWNER_ROLE_ID)
            if owner_role:
                overwrites[owner_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        ticket_channel = await guild.create_text_channel(
            f"ticket-{ticket_number:04d}",
            category=category,
            overwrites=overwrites
        )

        # Store ticket data
        ACTIVE_TICKETS[str(ticket_channel.id)] = {
            'user_id': interaction.user.id,
            'ticket_number': ticket_number,
            'reason': self.support_reason.value,
            'created_at': datetime.now().isoformat()
        }
        save_data()

        # Create ticket embed
        embed = discord.Embed(
            title=f"🎫 Support Ticket #{ticket_number:04d}",
            description=f"**User:** {interaction.user.mention}\n**Issue:**\n{self.support_reason.value}",
            color=0x00ff00,
            timestamp=datetime.now()
        )
        embed.set_footer(text="ZSells Support System")

        # Ping roles
        ping_message = ""
        if STAFF_ROLE_ID:
            ping_message += f"<@&{STAFF_ROLE_ID}> "
        if OWNER_ROLE_ID:
            ping_message += f"<@&{OWNER_ROLE_ID}>"

        view = TicketControlView(ticket_channel.id)
        await ticket_channel.send(ping_message, embed=embed, view=view)

        await interaction.response.send_message(f"✅ Ticket created! Please check {ticket_channel.mention}", ephemeral=True)

class SupportView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='Create Ticket', style=discord.ButtonStyle.primary, emoji='🎫', custom_id='support_create_ticket')
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketModal())

class OrderTicketControlView(discord.ui.View):
    def __init__(self, ticket_id):
        super().__init__(timeout=None)
        self.ticket_id = ticket_id

    @discord.ui.button(label='Complete Order', style=discord.ButtonStyle.success, emoji='✅', custom_id='order_complete')
    async def complete_order(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._close_ticket(interaction, "completed")

    @discord.ui.button(label='Close Ticket', style=discord.ButtonStyle.danger, emoji='🔒', custom_id='order_close')
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._close_ticket(interaction, "closed")

    async def _close_ticket(self, interaction, action_type):
        """Handle ticket closing and moving to closed channel"""
        CLOSED_TICKET_CHANNEL_ID = 1407347198366191798

        # Get ticket data
        ticket_data = ACTIVE_ORDER_TICKETS.get(self.ticket_id)
        if not ticket_data:
            await interaction.response.send_message("❌ Ticket data not found.", ephemeral=True)
            return

        # Get closed tickets channel
        closed_channel = interaction.guild.get_channel(CLOSED_TICKET_CHANNEL_ID)
        if not closed_channel:
            await interaction.response.send_message("❌ Closed tickets channel not found.", ephemeral=True)
            return

        # Create closure summary embed
        closure_embed = discord.Embed(
            title=f"🔒 Purchase Order #{ticket_data['ticket_number']:04d} - {action_type.title()}",
            description=f"**Customer:** <@{ticket_data['user_id']}>\n**Shop:** {ticket_data['shop']}\n**Status:** {action_type.title()}",
            color=0x00ff00 if action_type == "completed" else 0xff0000,
            timestamp=datetime.now()
        )

        closure_embed.add_field(
            name="🛍️ Ordered Products",
            value=f"```{ticket_data.get('products', 'No products listed')}```",
            inline=False
        )

        if ticket_data.get('special_requests'):
            closure_embed.add_field(
                name="📝 Special Requests",
                value=f"```{ticket_data['special_requests']}```",
                inline=False
            )

        closure_embed.add_field(
            name="📊 Ticket Information",
            value=f"**Created:** <t:{int(datetime.fromisoformat(ticket_data['created_at']).timestamp())}:R>\n**Closed:** <t:{int(datetime.now().timestamp())}:R>\n**Handled By:** {interaction.user.mention}",
            inline=False
        )

        closure_embed.set_footer(text=f"ZSupply Order System • Ticket {action_type}")

        # Send to closed channel
        await closed_channel.send(embed=closure_embed)

        # Remove from active tickets
        if self.ticket_id in ACTIVE_ORDER_TICKETS:
            del ACTIVE_ORDER_TICKETS[self.ticket_id]
            save_data()

        # Send confirmation
        status_embed = discord.Embed(
            title=f"✅ Order {action_type.title()}",
            description=f"This order has been {action_type}. Thank you for using ZSupply!",
            color=0x00ff00 if action_type == "completed" else 0xff0000
        )

        # Update the original message to remove buttons
        try:
            await interaction.response.edit_message(embed=status_embed, view=None)
        except:
            await interaction.response.send_message(embed=status_embed)

class TicketControlView(discord.ui.View):
    def __init__(self, channel_id):
        super().__init__(timeout=None)
        self.channel_id = channel_id

    @discord.ui.button(label='Close Ticket', style=discord.ButtonStyle.danger, emoji='🔒', custom_id='ticket_close')
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(self.channel_id) in ACTIVE_TICKETS:
            del ACTIVE_TICKETS[str(self.channel_id)]
            save_data()

        embed = discord.Embed(
            title="🔒 Ticket Closed",
            description="This ticket has been closed. The channel will be deleted in 10 seconds.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

        import asyncio
        await asyncio.sleep(10)
        await interaction.followup.delete_message(interaction.message.id)
        await interaction.channel.delete()

# Gang recruitment view
class GangRecruitmentView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='Join STK Gang', style=discord.ButtonStyle.success, emoji='⚔️', custom_id='gang_join_stk')
    async def join_gang(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if interaction.response.is_done():
                return

            embed = discord.Embed(
                title="🎉 Welcome to STK Gang!",
                description="**You're about to join one of the most elite gangs!**\n\nMake sure you're ready to represent STK across all games.",
                color=0x00ff00
            )
            embed.add_field(
                name="👕 Remember Your Outfit",
                value="**SHIRT:** Green Varsity\n**PANTS:** Green Ripped Jeans",
                inline=False
            )
            embed.add_field(
                name="🔗 Join Our Gang Discord",
                value="**Click here to join:** https://discord.gg/7rG6jVTVmX",
                inline=False
            )
            embed.set_footer(text="STK Gang • Elite Members Only • Wear your colors with pride!")

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except discord.NotFound:
            pass  # Interaction expired, ignore silently
        except discord.InteractionResponded:
            pass  # Already responded, ignore
        except discord.HTTPException as e:
            if e.status != 404:  # Don't log 404 errors (interaction not found)
                print(f"⚠️ HTTP error in gang recruitment: {e}")
        except Exception as e:
            print(f"⚠️ Error in gang recruitment: {e}")

# Create eye-catching shop embeds
def create_tb3_showcase_embed():
    embed = discord.Embed(
        title="🗽 **THE BRONX 3** 🗽",
        description="═══════════════════════════════════════\n🔥 **PREMIUM TB3 SERVICES** 🔥\n═══════════════════════════════════════",
        color=0x00ff00,
        timestamp=datetime.now()
    )

    # Add animated-looking banner
    embed.add_field(
        name="💫 ═══ FEATURED PRODUCTS ═══ 💫",
        value="```css\n🔫 ELITE WEAPONS COLLECTION\n💰 MONEY & BANK SERVICES\n⌚ LUXURY WATCHES COLLECTION\n📦 SPECIAL PACKAGES```",
        inline=False
    )

    # Weapons showcase
    weapons_display = ""
    featured_weapons = WEAPONS[:12]  # Show first 12 weapons
    for i, weapon in enumerate(featured_weapons, 1):
        weapons_display += f"`{i:02d}.` **{weapon}**\n"

    embed.add_field(
        name="🔫 ═══ PREMIUM WEAPONS ═══ 🔫",
        value=weapons_display + f"\n*...and {len(WEAPONS)-12} more weapons available!*",
        inline=True
    )

    # Money services
    embed.add_field(
        name="💰 ═══ MONEY SERVICES ═══ 💰",
        value="```yaml\n🏦 Bank 990k - $1.00\n💵 Clean 990k - $1.00\n💎 Bank 1.6M (GP) - $2.00\n✨ Clean 1.6M (GP) - $2.00\n\n🚀 INSTANT DELIVERY\n✨ 24/7 SUPPORT```",
        inline=True
    )

    # Watches showcase  
    watches_display = ""
    featured_watches = WATCHES[:8]
    for watch in featured_watches:
        watches_display += f"⌚ **{watch}**\n"

    embed.add_field(
        name="⌚ ═══ LUXURY WATCHES ═══ ⌚",
        value=watches_display + f"\n*...and {len(WATCHES)-8} more watches!*\n\n💰 **Only $1.00 each**",
        inline=False
    )

    # Pricing packages
    embed.add_field(
        name="📦 ═══ WEAPON PACKAGES ═══ 📦",
        value="```diff\n+ SAFE PACKAGE - $3.00 per weapon\n+ BAG PACKAGE - $2.00 per weapon  \n+ TRUNK PACKAGE - $1.00 per weapon\n\n! BULK DISCOUNTS AVAILABLE```",
        inline=False
    )

    embed.add_field(
        name="🎯 ═══ WHY CHOOSE US? ═══ 🎯",
        value="```css\n✅ INSTANT DELIVERY\n✅ PREMIUM QUALITY  \n✅ 24/7 CUSTOMER SUPPORT\n✅ SECURE TRANSACTIONS\n✅ MONEY-BACK GUARANTEE\n✅ TRUSTED BY 1000+ CUSTOMERS```",
        inline=False
    )

    embed.add_field(
        name="🛒 ═══ HOW TO ORDER ═══ 🛒",
        value="```yaml\n📝 Create a support ticket in #support\n💬 Tell us what you want to buy\n💳 Complete payment via our methods\n🚀 Receive your order instantly!\n\n💰 PAYMENT METHODS:\n• CashApp: https://cash.app/$EthanCreel1\n• Apple Pay: 7656156371\n• PayPal: Coming Soon```",
        inline=False
    )

    embed.set_footer(text="🔥 ZSupply TB3 • Create a support ticket to place your order! 🔥")
    return embed

def create_philly_showcase_embed():
    embed = discord.Embed(
        title="🦅 **PHILLY STREETS 2** 🦅",
        description="═══════════════════════════════════════\n⚡ **ULTIMATE PS2 PARADISE** ⚡\n═══════════════════════════════════════",
        color=0x00ff00,
        timestamp=datetime.now()
    )

    embed.add_field(
        name="💎 ═══ MONEY SERVICES ═══ 💎",
        value="```css\n🔥 $1 PER MILLION - BEST RATES!\n💰 Minimum: 1 Million ($1.00)\n💎 Maximum: 10 Million ($10.00)\n🚀 INSTANT DELIVERY GUARANTEED\n\n[1M] [2M] [3M] [4M] [5M]\n[6M] [7M] [8M] [9M] [10M]```",
        inline=False
    )

    embed.add_field(
        name="🎮 ═══ PREMIUM ACCOUNTS ═══ 🎮",
        value="```yaml\n💰 MAX MONEY ACCOUNT - $3.00\n   └ 5M Cash + 5M Bank + 200+ Days\n\n📊 MODDED STATS + MAX MONEY - $6.00\n   └ Enhanced Stats + Max Money\n\n⭐ FULLY STACKED ACCOUNT - $8.00\n   └ Max Money + Custom Name + Stats\n\n♾️ PERM INF MONEY ACCOUNT - $10.00\n   └ Unlimited Money Transfers```",
        inline=False
    )

    embed.add_field(
        name="🌟 ═══ EXCLUSIVE FEATURES ═══ 🌟",
        value="```diff\n+ AUTO-CALCULATED PRICING\n+ REAL-TIME MONEY DELIVERY\n+ CUSTOM NAME CHANGES\n+ MODDED STATISTICS\n+ UNLIMITED BANK TRANSFERS\n+ FROZEN MONEY PROTECTION```",
        inline=True
    )

    embed.add_field(
        name="⚡ ═══ SPEED & QUALITY ═══ ⚡",
        value="```css\n🚀 DELIVERY: INSTANT\n🛡️ SECURITY: MAXIMUM\n💎 QUALITY: PREMIUM\n⏰ SUPPORT: 24/7\n📈 SUCCESS RATE: 99.9%\n🔥 CUSTOMER RATING: 5/5```",
        inline=True
    )

    embed.add_field(
        name="🛒 ═══ HOW TO ORDER ═══ 🛒",
        value="```yaml\n📝 Create a support ticket in #support\n💬 Specify what you want to purchase\n💳 Complete payment via our methods\n🚀 Receive your order instantly!\n\n💰 PAYMENT METHODS:\n• CashApp: https://cash.app/$EthanCreel1\n• Apple Pay: 7656156371\n• PayPal: Coming Soon```",
        inline=False
    )

    embed.set_footer(text="⚡ ZSupply PS2 • Create a support ticket to place your order! ⚡")
    return embed

def create_south_bronx_showcase_embed():
    embed = discord.Embed(
        title="🔥 **SOUTH BRONX THE TRENCHES** 🔥",
        description="═══════════════════════════════════════\n💀 **THE ULTIMATE MODDED ACCOUNT** 💀\n═══════════════════════════════════════",
        color=0xff0000,
        timestamp=datetime.now()
    )

    embed.add_field(
        name="💀 ═══ LEGENDARY ACCOUNT ═══ 💀",
        value="```css\n🔥 ONLY $3.00 - INSANE VALUE!\n\n💰 CLEAN MONEY: 1.750M\n🏦 BANK MONEY: 1.750M  \n📊 TOTAL VALUE: 3.5M\n⏰ ACCOUNT AGE: 200+ DAYS\n🎰 LUCKY WEAPONS: INCLUDED*```",
        inline=False
    )

    embed.add_field(
        name="🎯 ═══ WHAT YOU GET ═══ 🎯",
        value="```diff\n+ 200+ DAY OLD ROBLOX ACCOUNT\n+ MAXIMUM MONEY (3.5M TOTAL)\n+ ACCOUNT USERNAME & PASSWORD\n+ COMPLETE SETUP INSTRUCTIONS\n+ 24/7 PREMIUM SUPPORT\n+ INSTANT DELIVERY\n\n! *WEAPONS IF YOU'RE LUCKY!```",
        inline=False
    )

    embed.add_field(
        name="⚡ ═══ UNBEATABLE VALUE ═══ ⚡",
        value="```yaml\nRegular Price: $15.00\nOUR PRICE: $3.00\nYOU SAVE: $12.00\n\nTHAT'S 80% OFF!\n\n🔥 LIMITED TIME OFFER\n⭐ BEST DEAL GUARANTEED```",
        inline=True
    )

    embed.add_field(
        name="🛡️ ═══ QUALITY PROMISE ═══ 🛡️",
        value="```css\n✅ AGED ACCOUNT GUARANTEED\n✅ MONEY PRE-LOADED\n✅ INSTANT ACCESS\n✅ NO HIDDEN FEES\n✅ FULL CUSTOMER SUPPORT\n✅ SATISFACTION GUARANTEED```",
        inline=True
    )

    embed.add_field(
        name="🛒 ═══ HOW TO ORDER ═══ 🛒",
        value="```yaml\n📝 Create a support ticket in #support\n💬 Request South Bronx account\n💳 Complete payment via our methods\n🚀 Receive your account instantly!\n\n💰 PAYMENT METHODS:\n• CashApp: https://cash.app/$EthanCreel1\n• Apple Pay: 7656156371\n• PayPal: Coming Soon```",
        inline=False
    )

    embed.set_footer(text="💀 ZSupply SB • Create a support ticket to claim your account! 💀")
    return embed

def create_roblox_alts_showcase_embed():
    embed = discord.Embed(
        title="🎮 **ROBLOX ALTS SHOP** 🎮",
        description="═══════════════════════════════════════\n🌟 **PREMIUM AGED ACCOUNTS** 🌟\n═══════════════════════════════════════",
        color=0x7289da,
        timestamp=datetime.now()
    )

    embed.add_field(
        name="🔥 ═══ ACCOUNT FEATURES ═══ 🔥",
        value="```css\n⏰ AGE: 200+ DAYS GUARANTEED\n🎮 STATUS: FULLY STACKED\n💎 QUALITY: HAND-PICKED PREMIUM\n🚀 DELIVERY: INSTANT ACCESS\n🛡️ SECURITY: MAXIMUM PROTECTION```",
        inline=False
    )

    embed.add_field(
        name="🎯 ═══ AVAILABLE GAMES ═══ 🎯",
        value="```yaml\n🗽 THE BRONX 3 ACCOUNT - $3.00\n   └ Max money + Premium items\n\n🦅 PHILLY STREETS 2 ACCOUNT - $3.00\n   └ Stacked cash + Lucky weapons\n\n🔥 SOUTH BRONX ACCOUNT - $3.00\n   └ 3.5M money + Elite status```",
        inline=False
    )

    embed.add_field(
        name="📦 ═══ INCLUDED WITH EVERY ACCOUNT ═══ 📦",
        value="```diff\n+ ACCOUNT USERNAME & PASSWORD\n+ STACKED IN-GAME MONEY\n+ PREMIUM ITEMS & WEAPONS\n+ COMPLETE SETUP GUIDE\n+ BACKUP EMAIL ACCESS\n+ 24/7 CUSTOMER SUPPORT\n+ SATISFACTION GUARANTEE```",
        inline=False
    )

    embed.add_field(
        name="⭐ ═══ WHY CHOOSE OUR ALTS? ═══ ⭐",
        value="```css\n🔸 200+ DAYS OLD = TRUSTED\n🔸 HAND-PICKED = QUALITY\n🔸 PRE-LOADED = READY TO PLAY\n🔸 INSTANT = NO WAITING\n🔸 SUPPORT = ALWAYS AVAILABLE\n🔸 GUARANTEE = YOUR SATISFACTION```",
        inline=False
    )

    embed.add_field(
        name="🛒 ═══ HOW TO ORDER ═══ 🛒",
        value="```yaml\n📝 Create a support ticket in #support\n💬 Specify which game account you want\n💳 Complete payment via our methods\n🚀 Receive your account instantly!\n\n💰 PAYMENT METHODS:\n• CashApp: https://cash.app/$EthanCreel1\n• Apple Pay: 7656156371\n• PayPal: Coming Soon```",
        inline=False
    )

    embed.set_footer(text="🎮 ZSupply Roblox Alts • Create a support ticket to get your account! 🎮")
    return embed

# Embed creation functions for other content
def create_support_embed():
    embed = discord.Embed(
        title="🎫 ZSells Support Center",
        description="**Need help? Our support team is here to assist you 24/7!**",
        color=0x3498db,
        timestamp=datetime.now()
    )
    embed.add_field(
        name="📞 What we can help with:",
        value="• Order issues\n• Payment problems\n• Product questions\n• Technical support\n• General inquiries",
        inline=False
    )
    embed.add_field(
        name="📋 How it works",
        value="1. Click the Create Ticket button below\n2. Describe your issue in detail\n3. Our staff will respond promptly\n4. Get the help you need!",
        inline=False
    )
    embed.add_field(
        name="⏰ Response Time",
        value="• **Average:** 15 minutes\n• **Maximum:** 2 hours\n• **24/7 availability**",
        inline=True
    )
    embed.add_field(
        name="⭐ Support Quality",
        value="• Expert staff\n• Quick resolutions\n• 99% satisfaction rate",
        inline=True
    )
    embed.set_footer(text="ZSells Support Center • Click below to create a ticket")
    return embed

def create_gang_embed():
    embed = discord.Embed(
        title="⚔️ STK Gang Recruitment",
        description="**Join the Elite STK Gang!**\n\nWe're recruiting skilled players for our elite gang across multiple games.",
        color=0x00ff00,
        timestamp=datetime.now()
    )
    embed.add_field(
        name="🎮 Available Games",
        value="• **The Bronx 3**\n• **Philly Streets 2**\n• **South Bronx The Trenches**",
        inline=False
    )
    embed.add_field(
        name="👕 Required Outfit",
        value="**Must wear when representing STK:**\n• **SHIRT:** Green Varsity\n• **PANTS:** Green Ripped Jeans",
        inline=False
    )
    embed.add_field(
        name="📋 Requirements",
        value="• Active player in any of our games\n• Follow gang dress code\n• Be respectful to other members\n• Participate in gang activities",
        inline=False
    )
    embed.add_field(
        name="🌟 Gang Benefits",
        value="• Elite gang members\n• Skilled teammates\n• Exclusive gang discord\n• Special privileges\n• Gang protection",
        inline=False
    )
    embed.set_footer(text="STK Gang • Elite recruitment across all games")
    return embed

def create_tos_embed():
    embed = discord.Embed(
        title="📋 Terms of Service",
        description="**ZSells Terms of Service - Please Read Carefully**\n\nBy using our services, you agree to the following terms:",
        color=0x3498db,
        timestamp=datetime.now()
    )
    embed.add_field(
        name="💳 Account & Payment",
        value="• All sales are final\n• No refunds on digital goods\n• Payment required before delivery\n• Account sharing prohibited\n• Valid payment methods only",
        inline=False
    )
    embed.add_field(
        name="📦 Product Delivery",
        value="• Delivery within 24 hours\n• Customer must be online for delivery\n• Products delivered as described\n• No guarantee on in-game performance\n• Contact support for delivery issues",
        inline=False
    )
    embed.add_field(
        name="⚖️ Legal & Compliance",
        value="• Must be 18+ or have parental consent\n• Use products responsibly\n• No reselling without permission\n• Comply with game terms of service\n• Report issues promptly",
        inline=False
    )
    embed.add_field(
        name="🚫 Prohibited Activities",
        value="• Chargebacks result in permanent ban\n• No abuse of support system\n• No sharing account credentials\n• No harassment of staff\n• No fraudulent activities",
        inline=False
    )
    embed.set_footer(text="ZSells • By using our services, you agree to these terms")
    return embed

def create_rules_embed():
    embed = discord.Embed(
        title="📜 Server Rules",
        description="**Welcome to ZSells Community!**\n\nPlease follow these rules to maintain a safe environment:",
        color=0xe74c3c,
        timestamp=datetime.now()
    )
    embed.add_field(
        name="1️⃣ Strictly 16+ Only",
        value="This server is for adults only. You must be 16 years or older to be here. Lying about your age will result in an immediate and permanent ban.",
        inline=False
    )
    embed.add_field(
        name="2️⃣ No Discussion of Real-World Violence or Harm",
        value="This is a service hub for digital goods, not a place to discuss real-world activities. Any talk of real violence, weapons, or causing physical harm is strictly forbidden and will result in a ban.",
        inline=False
    )
    embed.add_field(
        name="3️⃣ Be Clear & Professional in Business Deals",
        value="When buying or selling, state exactly what you are offering or looking for. Be clear on prices, payment methods, and account details. Do not try to scam or mislead other members.",
        inline=False
    )
    embed.add_field(
        name="4️⃣ Use the Correct Channels",
        value="Post your offers, questions, and deals only in the channels meant for them. Keep general chat clean and on-topic. Do not spam the same message across multiple channels.",
        inline=False
    )
    embed.add_field(
        name="5️⃣ No Chargebacks or Fraudulent Payments",
        value="Once a deal is complete, it is final. Filing a chargeback or using fraudulent payment methods (stolen cards, etc.) will result in a permanent ban and being publicly blacklisted.",
        inline=False
    )
    embed.set_footer(text="ZSells Community • More rules available - Contact staff for questions")
    return embed

def create_welcome_embed():
    embed = discord.Embed(
        title="🎉 Welcome to ZSells Community!",
        description="**Welcome to our amazing community!**\n\nWe're excited to have you here. Get started by exploring our channels and services!",
        color=0x00ff00,
        timestamp=datetime.now()
    )
    embed.add_field(
        name="🚀 Getting Started",
        value="• Read our rules and guidelines\n• Check out our shop for premium items\n• Join our STK Gang for exclusive perks\n• Create a support ticket if you need help",
        inline=False
    )
    embed.add_field(
        name="🌟 Community Benefits",
        value="• Premium services\n• 24/7 support\n• Exclusive deals\n• Elite gang access\n• Trusted community",
        inline=False
    )
    embed.add_field(
        name="🔗 Quick Links",
        value="• **Shop** - Premium products\n• **Support** - Get help instantly\n• **STK Gang** - Join the elite\n• **Rules** - Community guidelines",
        inline=False
    )
    embed.set_footer(text="ZSells Community • Your premium gaming destination!")
    return embed

# Utility functions
def check_channel_permissions(channel):
    """Check if bot has required permissions in a specific channel"""
    if not channel or not hasattr(channel, 'guild'):
        return False

    permissions = channel.permissions_for(channel.guild.me)
    return (permissions.view_channel and
            permissions.send_messages and
            permissions.embed_links and
            permissions.read_message_history)

@bot.event
async def on_ready():
    global CHANNELS, GUILD_ANALYSIS
    load_data()

    # Add persistent views
    bot.add_view(SupportView())
    bot.add_view(GangRecruitmentView())
    bot.add_view(ShopMainView())
    bot.add_view(NewShopView())

    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash commands")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")

    print(f'🤖 {bot.user} has connected to Discord!')
    print('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
    print('🔍 COMPREHENSIVE AUTO-DETECTION SYSTEM ACTIVATED')
    print('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')

    # Auto-setup all embeds in their respective channels
    await auto_setup_all_embeds()

    print('\n🤖 Pure Discord Bot Running - No Web Interface')

async def auto_setup_all_embeds():
    """Automatically setup all embeds in their respective channels"""
    try:
        # Setup support panel
        if 'support' in CHANNELS:
            support_channel = bot.get_channel(CHANNELS['support'])
            if support_channel and check_channel_permissions(support_channel):
                try:
                    embed = create_support_embed()
                    view = SupportView()
                    await support_channel.send(embed=embed, view=view)
                    print("✅ Support panel auto-setup complete!")
                except discord.Forbidden:
                    print(f"❌ No permission to send messages in #{support_channel.name}")
                except Exception as e:
                    print(f"❌ Error setting up support panel: {e}")

        # Setup gang recruitment
        if 'stk' in CHANNELS:
            stk_channel = bot.get_channel(CHANNELS['stk'])
            if stk_channel and check_channel_permissions(stk_channel):
                try:
                    embed = create_gang_embed()
                    view = GangRecruitmentView()
                    await stk_channel.send(embed=embed, view=view)
                    print("✅ Gang recruitment panel auto-setup complete!")
                except discord.Forbidden:
                    print(f"❌ No permission to send messages in #{stk_channel.name}")
                except Exception as e:
                    print(f"❌ Error setting up gang recruitment: {e}")

        # Setup ToS
        if 'tos' in CHANNELS:
            tos_channel = bot.get_channel(CHANNELS['tos'])
            if tos_channel and check_channel_permissions(tos_channel):
                try:
                    embed = create_tos_embed()
                    await tos_channel.send(embed=embed)
                    print("✅ Terms of Service auto-setup complete!")
                except discord.Forbidden:
                    print(f"❌ No permission to send messages in #{tos_channel.name}")
                except Exception as e:
                    print(f"❌ Error setting up ToS: {e}")

        # Setup Rules
        if 'rules' in CHANNELS:
            rules_channel = bot.get_channel(CHANNELS['rules'])
            if rules_channel and check_channel_permissions(rules_channel):
                try:
                    embed = create_rules_embed()
                    await rules_channel.send(embed=embed)
                    print("✅ Server rules auto-setup complete!")
                except discord.Forbidden:
                    print(f"❌ No permission to send messages in #{rules_channel.name}")
                except Exception as e:
                    print(f"❌ Error setting up rules: {e}")

        # Setup News
        if 'news' in CHANNELS:
            news_channel = bot.get_channel(CHANNELS['news'])
            if news_channel and check_channel_permissions(news_channel):
                try:
                    if not NEWS_DATA["last_updated"]:
                        NEWS_DATA["last_updated"] = datetime.now().isoformat()
                        save_data()
                    print("✅ News channel detected")
                except Exception as e:
                    print(f"❌ Error with news setup: {e}")

    except Exception as e:
        print(f"Error in auto-setup: {e}")

# Utility functions
def is_authorized_user(user_id):
    """Check if user is authorized to run spawn commands"""
    return user_id == 1385239185006268457

# New ZSupply shop spawn command with ticket system and calculator
@bot.tree.command(name="spawn_shops", description="Spawn ZSupply shop with ticket system")
async def spawn_shops(interaction: discord.Interaction):
    """Spawn new ZSupply shop with working ticket system and calculator"""
    try:
        # Check authorization
        if not is_authorized_user(interaction.user.id):
            await interaction.response.send_message("❌ You are not authorized to use this command.", ephemeral=True)
            return

        # First respond privately to confirm command
        await interaction.response.send_message("✅ ZSupply shop spawned successfully!", ephemeral=True)

        # Create new ZSupply shop embed
        embed = discord.Embed(
            title="⚡ ZSELLS ⚡",
            description="**Trusted By 50+ • Best Prices • 24/7 SUPPORT**",
            color=0x000000,
            timestamp=datetime.now()
        )
        
        # Add header image
        embed.set_image(url="https://cdn.discordapp.com/attachments/1407347218951700534/1409618120515260570/Electric_Fury_of_ZSELLS.png?ex=68ae08ad&is=68acb72d&hm=c2de3ae059568166e9faa9f459b01819e279c00f654fdc3a6bfbd7e531cac28f&")

        embed.add_field(
            name="🗽 THE BRONX 3",
            value="**Dupe of your choice**\n• Watches: **$1 each**\n• Money 990k (Bank/Clean): **$1 each**\n• Money 1.6M (Gamepass Only): **$2 each**\n• Packages:\n  - Safe Package: **$5**\n  - Bag Package: **$3**\n  - Trunk Package: **$2**",
            inline=True
        )

        embed.add_field(
            name="🦅 PHILLY STREETS 2",
            value="• Money: **$1 per Million**\n• Max Account: **$3**\n• Stats + Money: **$6**\n• Fully Stacked Account: **$8**\n• ROLLBACK! ACCOUNT: **$10**",
            inline=True
        )

        embed.add_field(
            name="⚡ HOW TO ORDER",
            value="**Click the button below to:**\n🧮 Calculate your order then purchase\n\n**Fast Delivery • Secure Payment**",
            inline=False
        )

        embed.set_footer(text="⚡ BUY HERE ⚡")
        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1407347218951700534/1409618121051865168/Lightning-Powered__BUY_HERE__Design.png?ex=68ae08ad&is=68acb72d&hm=30c3b2adf6aa6a0cc489a309df85b9f5b1e44067f9b3170d0437b7297a05930f&")

        # Create view with new buttons
        view = NewShopView()
        await interaction.channel.send(embed=embed, view=view)

    except Exception as e:
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"Error spawning shops: {e}", ephemeral=True)
            else:
                await interaction.followup.send(f"Error spawning shops: {e}", ephemeral=True)
        except:
            pass

@bot.tree.command(name="spawn_support", description="Spawn support ticket panel")
async def spawn_support(interaction: discord.Interaction):
    """Spawn support ticket interface"""
    try:
        # Check authorization
        if not is_authorized_user(interaction.user.id):
            await interaction.response.send_message("❌ You are not authorized to use this command.", ephemeral=True)
            return

        # First respond privately to confirm command
        await interaction.response.send_message("✅ Support panel spawned successfully!", ephemeral=True)

        # Then send the public panel directly to the channel
        embed = create_support_embed()
        view = SupportView()
        await interaction.channel.send(embed=embed, view=view)
    except Exception as e:
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"Error spawning support panel: {e}", ephemeral=True)
            else:
                await interaction.followup.send(f"Error spawning support panel: {e}", ephemeral=True)
        except:
            pass

@bot.tree.command(name="spawn_gang", description="Spawn gang recruitment panel")
async def spawn_gang(interaction: discord.Interaction):
    """Spawn gang recruitment interface"""
    try:
        # Check authorization
        if not is_authorized_user(interaction.user.id):
            await interaction.response.send_message("❌ You are not authorized to use this command.", ephemeral=True)
            return

        # First respond privately to confirm command
        await interaction.response.send_message("✅ Gang recruitment panel spawned successfully!", ephemeral=True)

        # Then send the public panel directly to the channel
        embed = create_gang_embed()
        view = GangRecruitmentView()
        await interaction.channel.send(embed=embed, view=view)
    except discord.NotFound:
        pass
    except discord.InteractionResponded:
        pass
    except Exception as e:
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"Error spawning gang panel: {e}", ephemeral=True)
            else:
                await interaction.followup.send(f"Error spawning gang panel: {e}", ephemeral=True)
        except (discord.NotFound, discord.InteractionResponded):
            pass

@bot.tree.command(name="spawn_tos", description="Spawn Terms of Service")
async def spawn_tos(interaction: discord.Interaction):
    """Spawn Terms of Service embed"""
    try:
        # Check authorization
        if not is_authorized_user(interaction.user.id):
            await interaction.response.send_message("❌ You are not authorized to use this command.", ephemeral=True)
            return

        # First respond privately to confirm command
        await interaction.response.send_message("✅ Terms of Service spawned successfully!", ephemeral=True)

        # Then send the public panel directly to the channel
        embed = create_tos_embed()
        await interaction.channel.send(embed=embed)
    except discord.NotFound:
        pass
    except discord.InteractionResponded:
        pass
    except Exception as e:
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"Error spawning TOS: {e}", ephemeral=True)
            else:
                await interaction.followup.send(f"Error spawning TOS: {e}", ephemeral=True)
        except (discord.NotFound, discord.InteractionResponded):
            pass

@bot.tree.command(name="spawn_rules", description="Spawn server rules")
async def spawn_rules(interaction: discord.Interaction):
    """Spawn server rules embed"""
    try:
        # Check authorization
        if not is_authorized_user(interaction.user.id):
            await interaction.response.send_message("❌ You are not authorized to use this command.", ephemeral=True)
            return

        # First respond privately to confirm command
        await interaction.response.send_message("✅ Server rules spawned successfully!", ephemeral=True)

        # Then send the public panel directly to the channel
        embed = create_rules_embed()
        await interaction.channel.send(embed=embed)
    except discord.NotFound:
        pass
    except discord.InteractionResponded:
        pass
    except Exception as e:
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"Error spawning rules: {e}", ephemeral=True)
            else:
                await interaction.followup.send(f"Error spawning rules: {e}", ephemeral=True)
        except (discord.NotFound, discord.InteractionResponded):
            pass

@bot.tree.command(name="spawn_welcome", description="Spawn welcome message")
async def spawn_welcome(interaction: discord.Interaction):
    """Spawn welcome message embed"""
    try:
        # Check authorization
        if not is_authorized_user(interaction.user.id):
            await interaction.response.send_message("❌ You are not authorized to use this command.", ephemeral=True)
            return

        # First respond privately to confirm command
        await interaction.response.send_message("✅ Welcome message spawned successfully!", ephemeral=True)

        # Then send the public panel directly to the channel
        embed = create_welcome_embed()
        await interaction.channel.send(embed=embed)
    except discord.NotFound:
        pass
    except discord.InteractionResponded:
        pass
    except Exception as e:
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"Error spawning welcome: {e}", ephemeral=True)
            else:
                await interaction.followup.send(f"Error spawning welcome: {e}", ephemeral=True)
        except (discord.NotFound, discord.InteractionResponded):
            pass

@bot.tree.command(name="news", description="Spawn news update")
async def news(interaction: discord.Interaction, title: str = None, content: str = None):
    """Spawn news update in the news channel"""
    try:
        # Check authorization
        if not is_authorized_user(interaction.user.id):
            await interaction.response.send_message("❌ You are not authorized to use this command.", ephemeral=True)
            return

        # Use provided content or default news
        news_title = title or "📰 Latest News Update"
        news_content = content or "Stay tuned for important announcements and updates!"

        embed = discord.Embed(
            title=news_title,
            description=news_content,
            color=0xff6b6b,
            timestamp=datetime.now()
        )
        embed.add_field(
            name="📢 Important Information",
            value="• Check back regularly for updates\n• Follow server announcements\n• Contact support if you have questions",
            inline=False
        )
        embed.set_footer(text="ZSells News • Stay informed")

        # Send directly to the channel where command was used
        await interaction.channel.send(embed=embed)

        # Private confirmation
        await interaction.response.send_message("✅ News posted successfully!", ephemeral=True)

        # Update news data
        global NEWS_DATA
        NEWS_DATA = {
            "title": news_title,
            "content": news_content,
            "last_updated": datetime.now().isoformat()
        }
        save_data()

    except discord.NotFound:
        pass
    except discord.InteractionResponded:
        pass
    except Exception as e:
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"Error posting news: {e}", ephemeral=True)
            else:
                await interaction.followup.send(f"Error posting news: {e}", ephemeral=True)
        except (discord.NotFound, discord.InteractionResponded):
            pass

@bot.tree.command(name="reminder", description="Set a reminder")
async def reminder(interaction: discord.Interaction, time: str, message: str):
    """Set a reminder for a specific time"""
    try:
        await interaction.response.defer(ephemeral=True)

        import re

        # Parse time (simple format: 5m, 1h, 30s)
        time_pattern = r'^(\d+)([smh])$'
        match = re.match(time_pattern, time.lower())

        if not match:
            await interaction.followup.send("❌ Invalid time format! Use: 30s, 5m, 1h", ephemeral=True)
            return

        duration = int(match.group(1))
        unit = match.group(2)

        # Convert to seconds
        if unit == 's':
            seconds = duration
        elif unit == 'm':
            seconds = duration * 60
        elif unit == 'h':
            seconds = duration * 3600

        if seconds > 86400:  # Max 24 hours
            await interaction.followup.send("❌ Maximum reminder time is 24 hours!", ephemeral=True)
            return

        # Create reminder embed
        embed = discord.Embed(
            title="⏰ Reminder Set",
            description=f"I'll remind you in **{time}** about:\n\n*{message}*",
            color=0x00ff00,
            timestamp=datetime.now()
        )
        embed.set_footer(text="ZSupply Reminder System")

        await interaction.followup.send(embed=embed, ephemeral=True)

        # Wait and send reminder
        await asyncio.sleep(seconds)

        reminder_embed = discord.Embed(
            title="🔔 Reminder",
            description=f"**You asked me to remind you:**\n\n*{message}*",
            color=0xff9500,
            timestamp=datetime.now()
        )
        reminder_embed.set_footer(text="ZSupply Reminder System")

        try:
            await interaction.followup.send(f"{interaction.user.mention}", embed=reminder_embed)
        except:
            # Fallback to DM if followup fails
            try:
                await interaction.user.send(embed=reminder_embed)
            except:
                pass  # User has DMs disabled

    except discord.NotFound:
        pass
    except discord.InteractionResponded:
        pass
    except Exception as e:
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"Error setting reminder: {e}", ephemeral=True)
            else:
                await interaction.followup.send(f"Error setting reminder: {e}", ephemeral=True)
        except (discord.NotFound, discord.InteractionResponded):
            pass

# Run the bot
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
if TOKEN:
    bot.run(TOKEN)
else:
    print("❌ DISCORD_BOT_TOKEN not found in environment variables")
    print("Please add your Discord bot token to the environment variables.")