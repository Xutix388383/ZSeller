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

# --- Dynamic Role and Category Detection Functions ---

def get_staff_roles(guild):
    """Dynamically detect staff roles based on common names and permissions."""
    staff_roles = []
    if not guild:
        return staff_roles

    for role in guild.roles:
        role_name_lower = role.name.lower()
        # Check for common staff keywords and essential permissions
        if (any(keyword in role_name_lower for keyword in ['staff', 'admin', 'mod', 'moderator', 'helper', 'manager']) or
                role.permissions.administrator or
                role.permissions.manage_guild or
                role.permissions.manage_roles):
            staff_roles.append(role)
    return staff_roles

def get_shop_ticket_category(guild):
    """Dynamically find or suggest a shop ticket category ID."""
    if not guild:
        return None

    # Prioritize existing categories with specific keywords
    for cat in guild.categories:
        cat_name_lower = cat.name.lower()
        if any(keyword in cat_name_lower for keyword in ['shop', 'order', 'ticket', 'support', 'transactions']):
            return cat.id

    # If no suitable category found, return None, suggesting creation or a fallback
    return None

# Enhanced channel and member detection functions
def get_channels_by_name(guild):
    """Auto-detect channels by name patterns with enhanced matching"""
    channels = {}

    if not guild:
        return channels

    # Define comprehensive channel name patterns
    channel_patterns = {
        'support': ['support', 'help', 'ticket', 'tickets', '𝐭𝐢𝐜𝐤𝐞𝐭', '𝐓𝐢𝐜𝐤𝐞𝐭', 'assistance', 'staff', 'admin', 'mod', 'report', 'contact'],
        'general': ['general', 'main', 'lobby', 'entrance', 'start', 'begin', 'intro', 'recruitment', 'join', 'member', 'recruit', 'crew', 'team', 'clan'],
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

        # Enhanced cleaning - remove emojis, special chars, but keep essential separators and Unicode letters
        clean_name = ''.join(c for c in channel_name_lower if c.isalnum() or c in ['-', '_', ' '] or ord(c) > 127)

        # Also check original name for Unicode styled text like 𝐓𝐢𝐜𝐤𝐞𝐭𝐬
        original_name = channel.name

        # Split by common separators for better word matching
        name_words = clean_name.replace('-', ' ').replace('_', ' ').split()

        # Check each pattern category with enhanced matching
        for category, patterns in channel_patterns.items():
            if category in channels:  # Skip if already found
                continue

            for pattern in patterns:
                # Multiple matching strategies including Unicode styled text
                if (pattern in clean_name or
                    pattern in channel_name_lower or
                    pattern in original_name.lower() or
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

# Role IDs - These will be dynamically detected or configured if necessary
# STAFF_ROLE_ID = 1409693493206581300  # Admin role (Example, not used directly with dynamic detection)
# OWNER_ROLE_ID = 1409693493206581300  # Owner role (Example, not used directly with dynamic detection)

# Ticket category ID for shop orders - This will be dynamically detected
# SHOP_TICKET_CATEGORY_ID = 1407347196906573889 # (Example, not used directly with dynamic detection)

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

        # Create ticket channel in the shop category (auto-detected)
        guild = interaction.guild
        category_id = get_shop_ticket_category(guild)
        category = None

        if category_id:
            category = guild.get_channel(category_id)

        if not category:
            # Try to find any category with shop/ticket keywords - do not create new ones
            for cat in guild.categories:
                if any(keyword in cat.name.lower() for keyword in ['shop', 'ticket', 'order', 'support']):
                    category = cat
                    break

            if not category:
                # Use the hardcoded category ID: 1409942998615199764
                category = guild.get_channel(1409942998615199764)
                if not category:
                    await interaction.response.send_message("❌ Shop category not found! Please contact an administrator.", ephemeral=True)
                    return

        # Create ticket channel with proper permissions
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        # Add staff permissions dynamically
        staff_roles = get_staff_roles(guild)
        for staff_role in staff_roles:
            overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        ticket_channel = await guild.create_text_channel(
            f"order-{ticket_number:04d}-{interaction.user.display_name}",
            category=category,
            overwrites=overwrites
        )

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

        embed.set_footer(text="RIA Gang Cart Order System • Staff will assist you")

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

        # Create ticket channel in the shop category (auto-detected)
        guild = interaction.guild
        category_id = get_shop_ticket_category(guild)
        category = None

        if category_id:
            category = guild.get_channel(category_id)

        if not category:
            # Try to find any category with shop/ticket keywords - do not create new ones
            for cat in guild.categories:
                if any(keyword in cat.name.lower() for keyword in ['shop', 'ticket', 'order', 'support']):
                    category = cat
                    break

            if not category:
                # Use the hardcoded category ID: 1409942998615199764
                category = guild.get_channel(1409942998615199764)
                if not category:
                    await interaction.response.send_message("❌ Shop category not found! Please contact an administrator.", ephemeral=True)
                    return

        # Create ticket channel with proper permissions
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        # Add staff permissions dynamically
        staff_roles = get_staff_roles(guild)
        for staff_role in staff_roles:
            overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        ticket_channel = await guild.create_text_channel(
            f"order-{ticket_number:04d}-{interaction.user.display_name}",
            category=category,
            overwrites=overwrites
        )

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
            value="**Please send payment to:**\n• **CashApp:** https://cash.app/$EthanCreel1\n• **Apple Pay:** 7656156371\n\n**After payment, let us know in this ticket!**",
            inline=False
        )

        embed.add_field(
            name="📋 Next Steps",
            value="1️⃣ Calculate total using calculator button\n2️⃣ Send payment using methods above\n3️⃣ Type exactly what you want in this channel\n4️⃣ Staff will process your order",
            inline=False
        )

        embed.set_footer(text="RIA Gang Private Order System • Staff will assist you")

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
            title="🛒 RIA Gang Cart & Calculator",
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
            title="🛒 RIA Gang Cart & Calculator",
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

        closure_embed.set_footer(text="RIA Gang Order System • Ticket {action_type}")

        # Remove from active tickets
        if self.ticket_id in ACTIVE_ORDER_TICKETS:
            del ACTIVE_ORDER_TICKETS[self.ticket_id]
            save_data()

        # Send confirmation in same channel
        status_embed = discord.Embed(
            title=f"✅ Order {action_type.title()}",
            description=f"This order has been {action_type}. Thank you for using RIA Gang!",
            color=0x00ff00 if action_type == "completed" else 0xff0000
        )

        # Update the original message to remove buttons
        try:
            await interaction.response.edit_message(embed=status_embed, view=None)
        except:
            await interaction.response.send_message(embed=status_embed)





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
        # First try to find a suitable category and then create the channel
        guild = interaction.guild
        category = None

        # Dynamically find or create the shop/ticket category
        category_id = get_shop_ticket_category(guild)
        if category_id:
            category = guild.get_channel(category_id)

        if not category:
            # Try to find any category with shop/ticket keywords - do not create new ones
            for cat in guild.categories:
                if any(keyword in cat.name.lower() for keyword in ['shop', 'ticket', 'order', 'support']):
                    category = cat
                    break

            if not category:
                # Use the hardcoded category ID: 1409942998615199764
                category = guild.get_channel(1409942998615199764)
                if not category:
                    await interaction.response.send_message("❌ Shop category not found! Please contact an administrator.", ephemeral=True)
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
            'channel_id': category.channels[0].id if category.channels else None # Fallback if no channels in category yet
        }
        save_data()

        # Create ticket channel with proper permissions
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        # Add staff permissions dynamically
        staff_roles = get_staff_roles(guild)
        for staff_role in staff_roles:
            overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        ticket_channel = await guild.create_text_channel(
            f"order-{ticket_number:04d}-{interaction.user.display_name}",
            category=category,
            overwrites=overwrites
        )
        ACTIVE_ORDER_TICKETS[ticket_id]['channel_id'] = ticket_channel.id # Update with actual channel ID

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

        embed.set_footer(text="RIA Gang Order System • Owner/Admin will assist you")

        # Ping owner and admins
        ping_message = "**🔥 NEW PURCHASE ORDER - Owner/Admin assistance needed!**\n\n"
        # Dynamically ping staff roles
        staff_roles = get_staff_roles(guild)
        if staff_roles:
            for role in staff_roles:
                ping_message += f"<@&{role.id}> "

        view = OrderTicketControlView(ticket_id)
        message = await ticket_channel.send(ping_message, embed=embed, view=view)

        # Store message ID
        ACTIVE_ORDER_TICKETS[ticket_id]['message_id'] = message.id
        save_data()

        await interaction.response.send_message(f"✅ Purchase order created! Check {ticket_channel.mention} - Owner/Admin will assist you shortly!", ephemeral=True)

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
        category = None

        # Dynamically find or create the support ticket category
        support_category_name = "Support Tickets"
        for cat in guild.categories:
            if cat.name == support_category_name:
                category = cat
                break
        if not category:
            try:
                category = await guild.create_category(support_category_name)
            except Exception as e:
                await interaction.response.send_message(f"❌ Could not create or find support category: {e}", ephemeral=True)
                return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        # Add staff permissions dynamically
        staff_roles = get_staff_roles(guild)
        for staff_role in staff_roles:
            overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

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
        embed.set_footer(text="RIA Gang Support System")

        # Ping roles
        ping_message = ""
        # Dynamically ping staff roles
        staff_roles = get_staff_roles(guild)
        if staff_roles:
            for role in staff_roles:
                ping_message += f"<@&{role.id}> "

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
        # Dynamically find the closed ticket channel ID
        CLOSED_TICKET_CHANNEL_ID = None # Default to None, will try to find dynamically
        guild = interaction.guild
        for channel in guild.text_channels:
            if any(keyword in channel.name.lower() for keyword in ['closed', 'archive', 'logs', 'history']):
                CLOSED_TICKET_CHANNEL_ID = channel.id
                break

        if not CLOSED_TICKET_CHANNEL_ID:
            await interaction.response.send_message("❌ Closed tickets channel not found. Please create one or contact an admin.", ephemeral=True)
            return

        # Get ticket data
        ticket_data = ACTIVE_ORDER_TICKETS.get(self.ticket_id)
        if not ticket_data:
            await interaction.response.send_message("❌ Ticket data not found.", ephemeral=True)
            return

        # Get closed tickets channel
        closed_channel = interaction.guild.get_channel(CLOSED_TICKET_CHANNEL_ID)
        if not closed_channel:
            await interaction.response.send_message("❌ Closed tickets channel not found or inaccessible.", ephemeral=True)
            return

        # Create closure summary embed
        closure_embed = discord.Embed(
            title=f"🔒 Purchase Order #{ticket_data['ticket_number']:04d} - {action_type.title()}",
            description=f"**Customer:** <@{ticket_data['user_id']}>\n**Shop:** {ticket_data.get('shop', 'N/A')}\n**Status:** {action_type.title()}",
            color=0x00ff00 if action_type == "completed" else 0xff0000,
            timestamp=datetime.now()
        )

        if 'cart_summary' in ticket_data:
            closure_embed.add_field(
                name="🛒 Cart Order",
                value=f"```{ticket_data.get('cart_summary', 'No cart data')}```",
                inline=False
            )
        else:
            closure_embed.add_field(
                name="🛍️ Ordered Items",
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

        closure_embed.set_footer(text="RIA Gang Order System • Ticket {action_type}")

        # Send to closed channel
        await closed_channel.send(embed=closure_embed)

        # Remove from active tickets
        if self.ticket_id in ACTIVE_ORDER_TICKETS:
            del ACTIVE_ORDER_TICKETS[self.ticket_id]
            save_data()

        # Send confirmation
        status_embed = discord.Embed(
            title=f"✅ Order {action_type.title()}",
            description=f"This order has been {action_type}. Thank you for using RIA Gang!",
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

    @discord.ui.button(label='Join RIA Gang', style=discord.ButtonStyle.success, emoji='⚔️', custom_id='gang_join_ria')
    async def join_gang(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if interaction.response.is_done():
                return

            embed = discord.Embed(
                title="🎉 Welcome to RIA Gang!",
                description="**You're about to join one of the most elite gangs for Philly Streets!**\n\nMake sure you're ready to represent RIA by risking it all.",
                color=0x00ff00
            )
            embed.add_field(
                name="👕 Remember Your Outfit",
                value="**SHIRT:** Green Varsity\n**PANTS:** Green Ripped Jeans",
                inline=False
            )
            embed.add_field(
                name="🔗 Join Our Gang Discord",
                value="**Click here to join:** https://discord.gg/7rG6jVTVmX", # Replace with actual RIA Gang Discord link if available
                inline=False
            )
            embed.set_footer(text="RIA Gang • Risking it all for Philly Streets • Wear your colors with pride!")

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

# --- Dynamic Authorization Function ---
def is_authorized_user(user_id, guild):
    """
    Checks if a user is authorized to use specific commands.
    Authorization is based on having administrator permissions or a role identified as staff.
    """
    if not guild:
        return False # Cannot authorize without a guild context

    member = guild.get_member(user_id)
    if not member:
        return False # Member not found in guild

    # Check for administrator permissions
    if member.guild_permissions.administrator:
        return True

    # Check if the member has any of the dynamically detected staff roles
    staff_roles = get_staff_roles(guild)
    for role in member.roles:
        if role in staff_roles:
            return True

    return False # User is not authorized

@bot.event
async def on_ready():
    global CHANNELS, GUILD_ANALYSIS
    load_data()

    # Add persistent views
    bot.add_view(SupportView())
    bot.add_view(GangRecruitmentView())

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

    # Auto-detect channels for each guild the bot is in
    for guild in bot.guilds:
        print(f"\n🏰 Analyzing guild: {guild.name} (ID: {guild.id})")
        detected_channels = get_channels_by_name(guild)
        CHANNELS.update(detected_channels)

        # Perform full guild analysis
        GUILD_ANALYSIS[guild.id] = analyze_guild_structure(guild)

    # Auto-setup disabled - only ticket creation enabled
    print("✅ Auto-setup disabled - only ticket creation enabled")

# --- Slash Commands ---

@bot.tree.command(name="ria_info", description="Display information about RIA gang and head members")
async def ria_info(interaction: discord.Interaction):
    """Display RIA gang information and head members"""
    try:
        # Check authorization using dynamic detection
        if not is_authorized_user(interaction.user.id, interaction.guild):
            await interaction.response.send_message("❌ You are not authorized to use this command. You need administrator permissions or an admin role.", ephemeral=True)
            return

        # Create RIA info embed
        embed = discord.Embed(
            title="💜 RIA GANG - RISKING IT ALL 💜",
            description="**Welcome to RIA Gang - Where legends are made and fear is earned.**\n\nRIA stands for **Risking It All** - we're the most respected and feared organization running the streets of Philadelphia. When you see purple, you know you're in RIA territory.",
            color=0x8A2BE2,
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="👑 THE LEADERSHIP",
            value="**Boss:** <@1099478092625477672>\n**Underboss:** <@1401979784623554743>\n**Underboss:** <@1385239185006268457>",
            inline=False
        )
        
        embed.add_field(
            name="🎯 WHAT WE CONTROL",
            value="• **Our Territory:** Dead end behind the gas station - RIA turf\n• **Full Philly Streets Shop:** Complete inventory for verified sellers\n• **The Money:** Business moves fast when you're with us\n• **The Respect:** Our name carries weight on these streets\n• **The Family:** Blood in, blood out - we protect our own",
            inline=False
        )
        
        embed.add_field(
            name="💜 GANG COLORS & REQUIREMENTS",
            value="**MANDATORY:** Purple Flag 🏴\n**COLORS:** Purple everything when you're repping\n**NO EXCEPTIONS:** You wear purple, you ARE RIA\n\n*Purple is power. Purple is respect. Purple is RIA.*",
            inline=False
        )
        
        embed.add_field(
            name="📜 THE CODE",
            value="• **Loyalty Above All:** Your crew comes first, always\n• **Respect the Purple:** Wear your colors with pride\n• **Stay Active:** Dead weight gets cut loose\n• **Handle Business:** When RIA calls, you answer\n• **One Family:** We ride together, we die together",
            inline=False
        )
        
        embed.add_field(
            name="💪 WHY YOU NEED RIA",
            value="• **Protection:** Nobody touches RIA family\n• **Resources:** Money, connections, power\n• **Reputation:** Fear and respect follow our name\n• **Success:** We turn soldiers into bosses\n• **Legacy:** Join something bigger than yourself",
            inline=False
        )
        
        embed.set_footer(text="RIA Gang • Purple Reign • Respect Earned, Never Given")

        await interaction.response.send_message(embed=embed)

    except Exception as e:
        await interaction.response.send_message(f"Error displaying RIA info: {e}", ephemeral=True)

# Run the bot
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
if TOKEN:
    bot.run(TOKEN)
else:
    print("❌ DISCORD_BOT_TOKEN not found in environment variables")
    print("Please add your Discord bot token to the environment variables.")