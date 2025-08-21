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

        print(f"  📊 Member Analysis:")
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

# Cart system functions
def get_user_cart(user_id):
    """Get user's cart, create if doesn't exist"""
    if user_id not in USER_CARTS:
        USER_CARTS[user_id] = {
            'items': [],
            'shop': None,
            'total': 0.0
        }
    return USER_CARTS[user_id]

def add_to_cart(user_id, item_name, price, shop_name):
    """Add item to user's cart"""
    cart = get_user_cart(user_id)
    cart['items'].append({
        'name': item_name,
        'price': price,
        'shop': shop_name
    })
    cart['shop'] = shop_name
    cart['total'] += price

def clear_cart(user_id):
    """Clear user's cart"""
    if user_id in USER_CARTS:
        USER_CARTS[user_id] = {
            'items': [],
            'shop': None,
            'total': 0.0
        }

def create_cart_embed(user_id):
    """Create cart display embed"""
    cart = get_user_cart(user_id)

    if not cart['items']:
        embed = discord.Embed(
            title="🛒 Your Cart",
            description="**Your cart is empty**\n\nAdd items from any shop to get started!",
            color=0x95a5a6,
            timestamp=datetime.now()
        )
        embed.set_footer(text="ZSupply Cart System")
        return embed

    embed = discord.Embed(
        title="🛒 Your Cart",
        description=f"**Shop:** {cart['shop']}\n**Items:** {len(cart['items'])}",
        color=0x3498db,
        timestamp=datetime.now()
    )

    # Group items by name for cleaner display
    item_counts = {}
    for item in cart['items']:
        if item['name'] in item_counts:
            item_counts[item['name']]['count'] += 1
            item_counts[item['name']]['total_price'] += item['price']
        else:
            item_counts[item['name']] = {
                'count': 1,
                'price': item['price'],
                'total_price': item['price']
            }

    cart_display = []
    for item_name, details in item_counts.items():
        if details['count'] > 1:
            cart_display.append(f"• {item_name} x{details['count']} - ${details['total_price']:.2f}")
        else:
            cart_display.append(f"• {item_name} - ${details['price']:.2f}")

    # Split into chunks for display
    item_chunks = [cart_display[i:i+8] for i in range(0, len(cart_display), 8)]

    for i, chunk in enumerate(item_chunks):
        embed.add_field(
            name=f"📦 Items {i+1}" if len(item_chunks) > 1 else "📦 Cart Items",
            value="\n".join(chunk),
            inline=False
        )

    embed.add_field(
        name="💰 Cart Total",
        value=f"**${cart['total']:.2f}**",
        inline=False
    )

    embed.set_footer(text="ZSupply Cart • Ready for checkout")
    return embed

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

# Shop data and cart system
WEAPONS = [
    "GoldenButton", "GreenSwitch", "BlueTips/Switch", "OrangeButton", "BinaryTrigger",
    "YellowButtonSwitch", "FullyARP", "FullyDraco", "Fully-MicroAR", "Cyanbutton",
    "100RndTanG19", "300ARG", "VP9Scope", "MasterPiece30", "GSwitch",
    "G17WittaButton", "G19Switch", "G20Switch", "G21Switch", "G22 Switch",
    "G23 Switch", "G40 Switch", "G42 Switch", "Fully-FN", "BinaryARP",
    "BinaryDraco", "CustomAR9"
]

# Global cart system for all shops
USER_CARTS = {}

PACKAGES = {
    "safe": {"name": "Safe Package", "price": 3.00, "emoji": "🔒"},
    "bag": {"name": "Bag Package", "price": 2.00, "emoji": "🎒"},
    "trunk": {"name": "Trunk Package", "price": 1.00, "emoji": "📦"}
}

MONEY_OPTIONS = {
    "regular": [
        {"name": "Max Money 990k", "price": 1.00, "emoji": "💰"},
        {"name": "Max Bank 990k", "price": 1.00, "emoji": "🏦"}
    ],
    "gamepass": [
        {"name": "Max Money 1.6M (Extra Money Pass)", "price": 2.00, "emoji": "💎"},
        {"name": "Max Bank 1.6M (Extra Bank Pass)", "price": 2.00, "emoji": "💳"}
    ]
}

WATCHES = [
    "Cartier", "BlueFaceCartier", "White Richard Millie", "PinkRichard", "GreenRichard",
    "RedRichard", "BluRichard", "BlackOutMillie", "Red AP", "AP Watch", "Gold AP",
    "Red AP Watch", "CubanG AP", "CubanP AP", "CubanB AP", "Iced AP"
]

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

async def create_private_order_ticket(interaction, shop_name, cart_items, total_amount):
    """Create a private order ticket for purchases"""
    global TICKET_COUNTER
    ticket_number = TICKET_COUNTER
    TICKET_COUNTER += 1

    # Use specified channel for order tickets
    ORDER_TICKET_CHANNEL_ID = 1407347196906573889
    ticket_channel = interaction.guild.get_channel(ORDER_TICKET_CHANNEL_ID)
    
    if not ticket_channel:
        await interaction.response.send_message("❌ Order ticket channel not found! Please contact an administrator.", ephemeral=True)
        return

    # Store ticket data with unique ticket ID
    ticket_id = f"order_{ticket_number:04d}_{interaction.user.id}"
    ACTIVE_ORDER_TICKETS[ticket_id] = {
        'user_id': interaction.user.id,
        'ticket_number': ticket_number,
        'shop': shop_name,
        'items': cart_items,
        'total': total_amount,
        'created_at': datetime.now().isoformat(),
        'channel_id': ticket_channel.id
    }
    save_data()

    # Create cart summary for ticket
    item_summary = []
    for item in cart_items:
        item_summary.append(f"• {item['name']} - ${item['price']:.2f}")

    cart_details = "\n".join(item_summary[:10])  # Show first 10 items
    if len(cart_items) > 10:
        cart_details += f"\n... and {len(cart_items) - 10} more items"

    # Create order ticket embed
    embed = discord.Embed(
        title=f"🛒 Order Ticket #{ticket_number:04d}",
        description=f"**Customer:** {interaction.user.mention}\n**Shop:** {shop_name}\n**Items:** {len(cart_items)}",
        color=0x00ff00,
        timestamp=datetime.now()
    )

    embed.add_field(
        name="📦 Order Details",
        value=cart_details,
        inline=False
    )

    embed.add_field(
        name="💰 Total Amount",
        value=f"**${total_amount:.2f}**",
        inline=True
    )

    embed.add_field(
        name="💳 Payment Methods",
        value="• **CashApp:** https://cash.app/$EthanCreel1\n• **Apple Pay:** 7656156371\n• **PayPal:** Coming Soon (broken)",
        inline=False
    )

    embed.add_field(
        name="📋 Next Steps",
        value="1️⃣ Owner/Admin will be with you shortly\n2️⃣ Complete payment using methods above\n3️⃣ Receive your order instantly\n4️⃣ Get setup support if needed",
        inline=False
    )

    embed.set_footer(text="ZSupply Order System • Owner/Admin will assist you")

    # Ping owner and admins
    ping_message = "**New Order - Owner/Admin assistance needed!**\n\n"
    if OWNER_ROLE_ID:
        ping_message += f"<@&{OWNER_ROLE_ID}> "
    if STAFF_ROLE_ID:
        ping_message += f"<@&{STAFF_ROLE_ID}>"

    view = OrderTicketControlView(ticket_id)
    message = await ticket_channel.send(ping_message, embed=embed, view=view)
    
    # Store message ID for reference
    ACTIVE_ORDER_TICKETS[ticket_id]['message_id'] = message.id
    save_data()

    await interaction.response.send_message(f"✅ Order ticket created! Please check {ticket_channel.mention} - Owner/Admin will be with you shortly!", ephemeral=True)

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

        # Create item summary for closure embed
        item_summary = "No items found"
        if 'items' in ticket_data and ticket_data['items']:
            items_list = []
            for item in ticket_data['items']:
                items_list.append(f"• {item['name']} - ${item['price']:.2f}")
            item_summary = "\n".join(items_list[:5])  # Show first 5 items
            if len(ticket_data['items']) > 5:
                item_summary += f"\n... and {len(ticket_data['items']) - 5} more items"

        # Create closure summary embed
        closure_embed = discord.Embed(
            title=f"🔒 Order Ticket #{ticket_data['ticket_number']:04d} - {action_type.title()}",
            description=f"**Customer:** <@{ticket_data['user_id']}>\n**Shop:** {ticket_data['shop']}\n**Status:** {action_type.title()}",
            color=0x00ff00 if action_type == "completed" else 0xff0000,
            timestamp=datetime.now()
        )
        
        closure_embed.add_field(
            name="📦 Order Items",
            value=item_summary,
            inline=False
        )

        if 'total' in ticket_data:
            closure_embed.add_field(
                name="💰 Total Amount",
                value=f"${ticket_data['total']:.2f}",
                inline=True
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

        # Send confirmation and remove buttons
        status_embed = discord.Embed(
            title=f"✅ Order {action_type.title()}",
            description=f"This ticket has been {action_type}. Thank you for using ZSupply!",
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
        await interaction.response.send_message(embed=embed)

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

# Views for existing shop (keeping original functionality)
class MainShopView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label='Weapons', style=discord.ButtonStyle.primary, emoji='🔫')
    async def weapons_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_weapons_embed(), view=WeaponsView())

    @discord.ui.button(label='Money', style=discord.ButtonStyle.success, emoji='💰')
    async def money_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_money_embed(), view=MoneyView())

    @discord.ui.button(label='Watches', style=discord.ButtonStyle.secondary, emoji='⌚')
    async def watches_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_watches_embed(), view=WatchesView())

    @discord.ui.button(label='View Cart', style=discord.ButtonStyle.primary, emoji='🛒')
    async def view_cart_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        cart_embed = create_cart_embed(interaction.user.id)
        await interaction.response.edit_message(embed=cart_embed, view=CartView(interaction.user.id, "The Bronx 3"))

    @discord.ui.button(label='Contact Info', style=discord.ButtonStyle.danger, emoji='📞')
    async def contact_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_contact_embed(), view=ContactView("The Bronx 3"))

class WeaponsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.select(
        placeholder="Choose weapons to add to cart...",
        options=[discord.SelectOption(label=weapon, value=weapon, emoji="🔫") for weapon in WEAPONS[:25]],
        max_values=len(WEAPONS[:25])
    )
    async def weapon_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        selected_weapons = select.values
        embed = discord.Embed(
            title="🔫 Add Weapons to Cart",
            description=f"**Selected Weapons:** {len(selected_weapons)} items\n\nChoose your package type to add to cart:",
            color=0xff6b6b,
            timestamp=datetime.now()
        )

        if len(selected_weapons) <= 5:
            embed.add_field(
                name="🎯 Selected Items",
                value="\n".join([f"• {weapon}" for weapon in selected_weapons]),
                inline=False
            )
        else:
            embed.add_field(
                name="🎯 Selected Items",
                value=f"• {len(selected_weapons)} weapons selected",
                inline=False
            )

        embed.add_field(
            name="📦 Package Options",
            value="• **Safe Package** - $3.00 per weapon\n• **Bag Package** - $2.00 per weapon\n• **Trunk Package** - $1.00 per weapon",
            inline=False
        )

        embed.set_footer(text="ZSupply TB3 • Choose package to add to cart")
        view = WeaponPackageView(selected_weapons)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label='Back', style=discord.ButtonStyle.secondary)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_main_shop_embed(), view=MainShopView())

class WeaponPackageView(discord.ui.View):
    def __init__(self, weapons):
        super().__init__(timeout=300)
        self.weapons = weapons if isinstance(weapons, list) else [weapons]

    @discord.ui.button(label='Add Safe Package - $3.00', style=discord.ButtonStyle.primary)
    async def safe_package(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Add each weapon with safe package to cart
        for weapon in self.weapons:
            add_to_cart(interaction.user.id, f"{weapon} (Safe Package)", 3.00, "The Bronx 3")

        embed = discord.Embed(
            title="✅ Added to Cart!",
            description=f"**{len(self.weapons)} weapons** with Safe Package added to cart!\n\n**Added:** ${len(self.weapons) * 3.00:.2f}",
            color=0x00ff00
        )
        await interaction.response.edit_message(embed=embed, view=AddedToCartView("weapons"))

    @discord.ui.button(label='Add Bag Package - $2.00', style=discord.ButtonStyle.success)
    async def bag_package(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Add each weapon with bag package to cart
        for weapon in self.weapons:
            add_to_cart(interaction.user.id, f"{weapon} (Bag Package)", 2.00, "The Bronx 3")

        embed = discord.Embed(
            title="✅ Added to Cart!",
            description=f"**{len(self.weapons)} weapons** with Bag Package added to cart!\n\n**Added:** ${len(self.weapons) * 2.00:.2f}",
            color=0x00ff00
        )
        await interaction.response.edit_message(embed=embed, view=AddedToCartView("weapons"))

    @discord.ui.button(label='Add Trunk Package - $1.00', style=discord.ButtonStyle.secondary)
    async def trunk_package(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Add each weapon with trunk package to cart
        for weapon in self.weapons:
            add_to_cart(interaction.user.id, f"{weapon} (Trunk Package)", 1.00, "The Bronx 3")

        embed = discord.Embed(
            title="✅ Added to Cart!",
            description=f"**{len(self.weapons)} weapons** with Trunk Package added to cart!\n\n**Added:** ${len(self.weapons) * 1.00:.2f}",
            color=0x00ff00
        )
        await interaction.response.edit_message(embed=embed, view=AddedToCartView("weapons"))

    @discord.ui.button(label='Back', style=discord.ButtonStyle.danger)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_weapons_embed(), view=WeaponsView())

class MoneyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label='Add Regular Money - $1.00', style=discord.ButtonStyle.primary, emoji='💵')
    async def regular_money(self, interaction: discord.Interaction, button: discord.ui.Button):
        add_to_cart(interaction.user.id, "Max Money 990k", 1.00, "The Bronx 3")
        embed = discord.Embed(
            title="✅ Added to Cart!",
            description="**Max Money 990k** added to cart!\n\n**Added:** $1.00",
            color=0x00ff00
        )
        await interaction.response.edit_message(embed=embed, view=AddedToCartView("money"))

    @discord.ui.button(label='Add Regular Bank - $1.00', style=discord.ButtonStyle.primary, emoji='🏦')
    async def regular_bank(self, interaction: discord.Interaction, button: discord.ui.Button):
        add_to_cart(interaction.user.id, "Max Bank 990k", 1.00, "The Bronx 3")
        embed = discord.Embed(
            title="✅ Added to Cart!",
            description="**Max Bank 990k** added to cart!\n\n**Added:** $1.00",
            color=0x00ff00
        )
        await interaction.response.edit_message(embed=embed, view=AddedToCartView("money"))

    @discord.ui.button(label='Add Gamepass Money - $2.00', style=discord.ButtonStyle.success, emoji='💎')
    async def gamepass_money(self, interaction: discord.Interaction, button: discord.ui.Button):
        add_to_cart(interaction.user.id, "Max Money 1.6M (Extra Money Pass)", 2.00, "The Bronx 3")
        embed = discord.Embed(
            title="✅ Added to Cart!",
            description="**Max Money 1.6M (Extra Money Pass)** added to cart!\n\n**Added:** $2.00",
            color=0x00ff00
        )
        await interaction.response.edit_message(embed=embed, view=AddedToCartView("money"))

    @discord.ui.button(label='Add Gamepass Bank - $2.00', style=discord.ButtonStyle.success, emoji='💳')
    async def gamepass_bank(self, interaction: discord.Interaction, button: discord.ui.Button):
        add_to_cart(interaction.user.id, "Max Bank 1.6M (Extra Bank Pass)", 2.00, "The Bronx 3")
        embed = discord.Embed(
            title="✅ Added to Cart!",
            description="**Max Bank 1.6M (Extra Bank Pass)** added to cart!\n\n**Added:** $2.00",
            color=0x00ff00
        )
        await interaction.response.edit_message(embed=embed, view=AddedToCartView("money"))

    @discord.ui.button(label='Back', style=discord.ButtonStyle.secondary, emoji='⬅️')
    async def back_to_bronx3(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_main_shop_embed(), view=MainShopView())

class WatchesView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.select(
        placeholder="Choose watches to add to cart...",
        options=[discord.SelectOption(label=watch, value=watch, emoji="⌚") for watch in WATCHES],
        max_values=len(WATCHES)
    )
    async def watch_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        selected_watches = select.values
        # Add each watch to cart
        for watch in selected_watches:
            add_to_cart(interaction.user.id, watch, 1.00, "The Bronx 3")

        total_price = len(selected_watches) * 1.00
        embed = discord.Embed(
            title="✅ Added to Cart!",
            description=f"**{len(selected_watches)} watches** added to cart!\n\n**Added:** ${total_price:.2f}",
            color=0x00ff00
        )
        if len(selected_watches) <= 5:
            embed.add_field(
                name="⌚ Added Watches",
                value="\n".join([f"• {watch}" for watch in selected_watches]),
                inline=False
            )
        await interaction.response.edit_message(embed=embed, view=AddedToCartView("watches"))

    @discord.ui.button(label='Back', style=discord.ButtonStyle.secondary)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_main_shop_embed(), view=MainShopView())

class ContactView(discord.ui.View):
    def __init__(self, shop_name=None):
        super().__init__(timeout=300)
        self.shop_name = shop_name

    @discord.ui.button(label='Back to Shop', style=discord.ButtonStyle.secondary, emoji='⬅️')
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.shop_name == "The Bronx 3":
            await interaction.response.edit_message(embed=create_main_shop_embed(), view=MainShopView())
        elif self.shop_name == "Philly Streets 2":
            await interaction.response.edit_message(embed=create_philly_shop_embed(), view=PhillyShopView())
        elif self.shop_name == "South Bronx The Trenches":
            await interaction.response.edit_message(embed=create_south_bronx_shop_embed(), view=SouthBronxShopView())
        else:
            await interaction.response.edit_message(embed=create_shop_selection_embed(), view=ShopSelectionView())

# Cart Views
class AddedToCartView(discord.ui.View):
    def __init__(self, category):
        super().__init__(timeout=300)
        self.category = category

    @discord.ui.button(label='Continue Shopping', style=discord.ButtonStyle.primary, emoji='🛍️')
    async def continue_shopping(self, interaction: discord.Interaction, button: discord.ui.Button):
        # TB3 Categories
        if self.category == "weapons":
            await interaction.response.edit_message(embed=create_weapons_embed(), view=WeaponsView())
        elif self.category == "money":
            await interaction.response.edit_message(embed=create_money_embed(), view=MoneyView())
        elif self.category == "watches":
            await interaction.response.edit_message(embed=create_watches_embed(), view=WatchesView())
        # Philly Categories
        elif self.category == "philly_weapons":
            await interaction.response.edit_message(embed=create_philly_weapons_embed(), view=PhillyWeaponsView())
        elif self.category == "philly_money":
            await interaction.response.edit_message(embed=create_philly_money_embed(), view=PhillyMoneyView())
        elif self.category == "philly_special":
            await interaction.response.edit_message(embed=create_philly_special_embed(), view=PhillySpecialView())
        # South Bronx Categories
        elif self.category == "sb_weapons":
            await interaction.response.edit_message(embed=create_south_bronx_shop_embed(), view=SouthBronxShopView())
        elif self.category == "sb_money":
            await interaction.response.edit_message(embed=create_south_bronx_shop_embed(), view=SouthBronxShopView())
        elif self.category == "sb_survival":
            await interaction.response.edit_message(embed=create_south_bronx_shop_embed(), view=SouthBronxShopView())
        elif self.category == "sb_account":
            await interaction.response.edit_message(embed=create_south_bronx_shop_embed(), view=SouthBronxShopView())
        elif self.category == "roblox_account":
            await interaction.response.edit_message(embed=create_roblox_alts_embed(), view=RobloxAltsView())
        else:
            await interaction.response.edit_message(embed=create_shop_selection_embed(), view=ShopSelectionView())

    @discord.ui.button(label='View Cart', style=discord.ButtonStyle.success, emoji='🛒')
    async def view_cart(self, interaction: discord.Interaction, button: discord.ui.Button):
        cart_embed = create_cart_embed(interaction.user.id)
        # Determine shop based on category
        if self.category.startswith("philly"):
            shop_name = "Philly Streets 2"
        elif self.category.startswith("sb"):
            shop_name = "South Bronx The Trenches"
        elif self.category == "roblox_account":
            shop_name = "Roblox Alts Shop"
        else:
            shop_name = "The Bronx 3"
        await interaction.response.edit_message(embed=cart_embed, view=CartView(interaction.user.id, shop_name))

    @discord.ui.button(label='Back to Shop', style=discord.ButtonStyle.secondary, emoji='🏠')
    async def back_to_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.category.startswith("philly"):
            await interaction.response.edit_message(embed=create_philly_shop_embed(), view=PhillyShopView())
        elif self.category.startswith("sb"):
            await interaction.response.edit_message(embed=create_south_bronx_shop_embed(), view=SouthBronxShopView())
        elif self.category == "roblox_account":
            await interaction.response.edit_message(embed=create_roblox_alts_embed(), view=RobloxAltsView())
        else:
            await interaction.response.edit_message(embed=create_main_shop_embed(), view=MainShopView())

class CartView(discord.ui.View):
    def __init__(self, user_id, shop_name):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.shop_name = shop_name

    @discord.ui.button(label='Checkout', style=discord.ButtonStyle.success, emoji='💳')
    async def checkout(self, interaction: discord.Interaction, button: discord.ui.Button):
        cart = get_user_cart(self.user_id)

        if not cart['items']:
            await interaction.response.send_message("❌ Your cart is empty!", ephemeral=True)
            return

        # Create order ticket with cart details
        await create_private_order_ticket(interaction, self.shop_name, cart['items'], cart['total'])

        # Clear cart after checkout
        clear_cart(self.user_id)

    @discord.ui.button(label='Clear Cart', style=discord.ButtonStyle.danger, emoji='🗑️')
    async def clear_cart_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        clear_cart(self.user_id)
        embed = discord.Embed(
            title="🗑️ Cart Cleared",
            description="Your cart has been cleared!",
            color=0xff6b6b
        )
        await interaction.response.edit_message(embed=embed, view=ClearedCartView())

    @discord.ui.button(label='Back to Shop', style=discord.ButtonStyle.secondary, emoji='🏠')
    async def back_to_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.shop_name == "The Bronx 3":
            await interaction.response.edit_message(embed=create_main_shop_embed(), view=MainShopView())
        elif self.shop_name == "Philly Streets 2":
            await interaction.response.edit_message(embed=create_philly_shop_embed(), view=PhillyShopView())
        elif self.shop_name == "South Bronx The Trenches":
            await interaction.response.edit_message(embed=create_south_bronx_shop_embed(), view=SouthBronxShopView())
        else:
            await interaction.response.edit_message(embed=create_shop_selection_embed(), view=ShopSelectionView())

class ClearedCartView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label='Back to Shop', style=discord.ButtonStyle.primary, emoji='🏠')
    async def back_to_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_shop_selection_embed(), view=ShopSelectionView())

class OrderInfoView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label='Back to Shop', style=discord.ButtonStyle.primary, emoji='🏠')
    async def back_to_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_main_shop_embed(), view=MainShopView())

# NEW SHOP LOGIC START
# Placeholder functions for new shop logic
def create_shop_selection_embed():
    embed = discord.Embed(
        title="🛒 ZSupply - Choose Your Location",
        description="Select a shop location to browse products:",
        color=0x3498db,
        timestamp=datetime.now()
    )
    embed.add_field(
        name="📍 Locations",
        value="• The Bronx 3\n• Philly Streets 2\n• South Bronx The Trenches",
        inline=False
    )
    embed.add_field(
        name="🎮 Roblox Services",
        value="• Roblox Alts Shop - Premium aged accounts",
        inline=False
    )
    embed.set_footer(text="ZSupply • Select a location to proceed")
    return embed

class ShopSelectionView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label='The Bronx 3', style=discord.ButtonStyle.primary, emoji='🗽')
    async def bronx3_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_main_shop_embed(), view=MainShopView())

    @discord.ui.button(label='Philly Streets 2', style=discord.ButtonStyle.success, emoji='🦅')
    async def philly_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_philly_shop_embed(), view=PhillyShopView(show_back=True))

    @discord.ui.button(label='South Bronx The Trenches', style=discord.ButtonStyle.danger, emoji='🔥')
    async def south_bronx_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_south_bronx_shop_embed(), view=SouthBronxShopView(show_back=True))

    @discord.ui.button(label='Roblox Alts Shop', style=discord.ButtonStyle.secondary, emoji='🎮')
    async def roblox_alts_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_roblox_alts_embed(), view=RobloxAltsView())

# PHILLY STREETS 2 SHOP LOGIC START
def create_philly_shop_embed():
    embed = discord.Embed(
        title="🦅 Philly Streets 2 - Money Services",
        description="**Welcome to Philly Streets 2 Shop**\n\nPremium money services - $1 per million!",
        color=0x00ff00,
        timestamp=datetime.now()
    )
    embed.add_field(
        name="💰 Money Services Available",
        value="✅ **$1 per Million** - Best rates guaranteed\n✅ **Minimum Order: 1 Million**\n✅ **Maximum Order: 10 Million**\n✅ **Instant Delivery** - Fast & reliable",
        inline=False
    )
    embed.add_field(
        name="🔫 Weapons Status",
        value="🚧 **Weapons Coming Soon!**\nWeapons will be available for purchase soon. Stay tuned for updates!",
        inline=True
    )
    embed.add_field(
        name="🚀 Features",
        value="✅ **Best Rates** - $1 per million\n✅ **24/7 Support** - Always here\n✅ **Secure Payment** - Safe deals\n✅ **Quality Guaranteed** - Trusted service",
        inline=True
    )
    embed.add_field(
        name="📊 Pricing Examples",
        value="• **1 Million** - $1.00\n• **5 Million** - $5.00\n• **10 Million** - $10.00 (Max order)",
        inline=False
    )
    embed.set_footer(text="ZSupply Philly Streets 2 • Order money below")
    return embed

class PhillyShopView(discord.ui.View):
    def __init__(self, show_back=False):
        super().__init__(timeout=300)
        self.show_back = show_back

        # Add back button only if there are other tabs
        if self.show_back:
            self.add_item(self.create_back_button())

    def create_back_button(self):
        back_button = discord.ui.Button(label='Back', style=discord.ButtonStyle.secondary, emoji='⬅️')
        async def back_callback(interaction):
            await interaction.response.edit_message(embed=create_shop_selection_embed(), view=ShopSelectionView())
        back_button.callback = back_callback
        return back_button

    @discord.ui.button(label='Order Money ($1/Million)', style=discord.ButtonStyle.success, emoji='💰')
    async def philly_money_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_philly_money_embed(), view=PhillyMoneyView())

    @discord.ui.button(label='View Cart', style=discord.ButtonStyle.primary, emoji='🛒')
    async def view_cart_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        cart_embed = create_cart_embed(interaction.user.id)
        await interaction.response.edit_message(embed=cart_embed, view=CartView(interaction.user.id, "Philly Streets 2"))

    @discord.ui.button(label='Contact Info', style=discord.ButtonStyle.danger, emoji='📞')
    async def contact_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_contact_embed(), view=ContactView("Philly Streets 2"))

def create_philly_weapons_embed():
    embed = discord.Embed(
        title="🔫 Philly Streets 2 - Weapons",
        description="**Premium weapon collection for Philly Streets 2**\n\nAll weapons come with fast delivery!",
        color=0xff6b6b,
        timestamp=datetime.now()
    )
    embed.add_field(
        name="🔥 Featured Weapons",
        value="• Glock Package - $2.50\n• AK-47 Setup - $3.00\n• AR-15 Kit - $3.50\n• Pistol Collection - $2.00\n• SMG Bundle - $2.75",
        inline=False
    )
    embed.add_field(
        name="💰 Pricing",
        value="**Starting from $2.00**\nBulk orders get discounts!",
        inline=True
    )
    embed.add_field(
        name="📦 What's Included",
        value="✅ Weapon delivery\n✅ Setup assistance\n✅ 24/7 support\n✅ Quality guarantee",
        inline=True
    )
    embed.set_footer(text="ZSupply PS2 Weapons • Contact us to order")
    return embed

class PhillyWeaponsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label='Add to Cart', style=discord.ButtonStyle.success, emoji='🛒')
    async def add_weapons_to_cart(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Show weapon selection modal or add default package
        add_to_cart(interaction.user.id, "Philly Weapons Package", 3.00, "Philly Streets 2")
        embed = discord.Embed(
            title="✅ Added to Cart!",
            description="**Philly Weapons Package** added to cart!\n\n**Added:** $3.00",
            color=0x00ff00
        )
        await interaction.response.edit_message(embed=embed, view=AddedToCartView("philly_weapons"))

    @discord.ui.button(label='Back', style=discord.ButtonStyle.secondary, emoji='⬅️')
    async def back_to_philly_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_philly_shop_embed(), view=PhillyShopView())

def create_philly_money_embed():
    embed = discord.Embed(
        title="💰 Philly Streets 2 - Money Orders",
        description="**$1 per Million - Best Rates Available!**\n\nUse the slider below to select your amount from 1M to 10M",
        color=0xffd700,
        timestamp=datetime.now()
    )
    embed.add_field(
        name="💵 Pricing Structure",
        value="**$1.00 per 1 Million**\n• Minimum Order: 1 Million ($1.00)\n• Maximum Order: 10 Million ($10.00)\n• Real-time price calculation",
        inline=False
    )
    embed.add_field(
        name="🎯 How to Order",
        value="1️⃣ Use the dropdown below to select your amount\n2️⃣ Price will be calculated automatically\n3️⃣ Add to cart when ready\n4️⃣ Proceed to checkout",
        inline=True
    )
    embed.add_field(
        name="🚀 Features",
        value="✅ Instant delivery\n✅ Safe & secure\n✅ 24/7 support\n✅ Auto-calculation\n✅ Best rates guaranteed",
        inline=True
    )
    embed.set_footer(text="ZSupply PS2 Money • Select amount below - $1 per million")
    return embed

class PhillyMoneyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.select(
        placeholder="Select money amount (1M - 10M)",
        options=[
            discord.SelectOption(label=f"{i} Million - ${i}.00", value=str(i), emoji="💰", description=f"Get {i} million PS2 money for ${i}.00")
            for i in range(1, 11)
        ],
        min_values=1,
        max_values=1
    )
    async def money_amount_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        selected_amount = int(select.values[0])
        price = float(selected_amount)
        
        # Create confirmation embed
        embed = discord.Embed(
            title="💰 Confirm Your Order",
            description=f"**Selected Amount:** {selected_amount} Million PS2 Money\n**Price:** ${price:.2f}\n\nReady to add to cart?",
            color=0x3498db,
            timestamp=datetime.now()
        )
        embed.add_field(
            name="📦 Order Details",
            value=f"**Product:** PS2 Money\n**Amount:** {selected_amount} Million\n**Price:** ${price:.2f}\n**Rate:** $1.00 per million",
            inline=True
        )
        embed.add_field(
            name="🚀 What's Included",
            value="✅ Instant delivery\n✅ Safe transfer\n✅ Setup support\n✅ Money guarantee",
            inline=True
        )
        embed.set_footer(text="ZSupply PS2 Money • Confirm to add to cart")
        
        view = PhillyMoneyConfirmView(selected_amount, price)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label='Back', style=discord.ButtonStyle.secondary, emoji='⬅️')
    async def back_to_philly_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_philly_shop_embed(), view=PhillyShopView())

class PhillyMoneyConfirmView(discord.ui.View):
    def __init__(self, amount, price):
        super().__init__(timeout=300)
        self.amount = amount
        self.price = price

    @discord.ui.button(label='Add to Cart', style=discord.ButtonStyle.success, emoji='🛒')
    async def confirm_add_to_cart(self, interaction: discord.Interaction, button: discord.ui.Button):
        add_to_cart(interaction.user.id, f"PS2 Money ({self.amount} Million)", self.price, "Philly Streets 2")
        embed = discord.Embed(
            title="✅ Added to Cart!",
            description=f"**{self.amount} Million PS2 Money** added to cart!\n\n**Added:** ${self.price:.2f}",
            color=0x00ff00
        )
        await interaction.response.edit_message(embed=embed, view=AddedToCartView("philly_money"))

    @discord.ui.button(label='Select Different Amount', style=discord.ButtonStyle.primary, emoji='🔄')
    async def select_different_amount(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_philly_money_embed(), view=PhillyMoneyView())

    @discord.ui.button(label='Back to Shop', style=discord.ButtonStyle.secondary, emoji='🏠')
    async def back_to_philly_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_philly_shop_embed(), view=PhillyShopView())

def create_philly_special_embed():
    embed = discord.Embed(
        title="⭐ Philly Streets 2 - Special Items",
        description="**Exclusive special items for PS2**\n\nUnique items you won't find anywhere else!",
        color=0x9b59b6,
        timestamp=datetime.now()
    )
    embed.add_field(
        name="✨ Special Items",
        value="• VIP Status - $5.00\n• Custom Vehicle - $4.50\n• Exclusive Outfit - $3.00\n• Special Abilities - $6.00\n• Rare Collections - $7.50",
        inline=False
    )
    embed.add_field(
        name="🎯 Features",
        value="✅ Exclusive access\n✅ Rare items\n✅ VIP treatment\n✅ Special privileges",
        inline=True
    )
    embed.set_footer(text="ZSupply PS2 Special • Limited availability")
    return embed

class PhillySpecialView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label='Add VIP Status - $5.00', style=discord.ButtonStyle.primary, emoji='👑')
    async def add_vip_status(self, interaction: discord.Interaction, button: discord.ui.Button):
        add_to_cart(interaction.user.id, "PS2 VIP Status", 5.00, "Philly Streets 2")
        embed = discord.Embed(title="✅ Added to Cart!", description="**PS2 VIP Status** added!\n\n**Added:** $5.00", color=0x00ff00)
        await interaction.response.edit_message(embed=embed, view=AddedToCartView("philly_special"))

    @discord.ui.button(label='Add Custom Vehicle - $4.50', style=discord.ButtonStyle.success, emoji='🚗')
    async def add_custom_vehicle(self, interaction: discord.Interaction, button: discord.ui.Button):
        add_to_cart(interaction.user.id, "PS2 Custom Vehicle", 4.50, "Philly Streets 2")
        embed = discord.Embed(title="✅ Added to Cart!", description="**PS2 Custom Vehicle** added!\n\n**Added:** $4.50", color=0x00ff00)
        await interaction.response.edit_message(embed=embed, view=AddedToCartView("philly_special"))

    @discord.ui.button(label='Add Special Abilities - $6.00', style=discord.ButtonStyle.danger, emoji='⚡')
    async def add_special_abilities(self, interaction: discord.Interaction, button: discord.ui.Button):
        add_to_cart(interaction.user.id, "PS2 Special Abilities", 6.00, "Philly Streets 2")
        embed = discord.Embed(title="✅ Added to Cart!", description="**PS2 Special Abilities** added!\n\n**Added:** $6.00", color=0x00ff00)
        await interaction.response.edit_message(embed=embed, view=AddedToCartView("philly_special"))

    @discord.ui.button(label='Back', style=discord.ButtonStyle.secondary, emoji='⬅️')
    async def back_to_philly_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_philly_shop_embed(), view=PhillyShopView())

# SOUTH BRONX THE TRENCHES SHOP LOGIC START
def create_south_bronx_shop_embed():
    embed = discord.Embed(
        title="🔥 South Bronx The Trenches - Modded Account",
        description="**Premium Modded Account - Only $2.00**\n\nGet a fully loaded 200+ day old account with maximum money!",
        color=0xff0000,
        timestamp=datetime.now()
    )
    embed.add_field(
        name="💰 Money Included",
        value="✅ **Clean Money: 1.750M** - Max clean money\n✅ **Bank Money: 1.750M** - Max bank money\n✅ **Total Value: 3.5M** - Fully stacked account",
        inline=False
    )
    embed.add_field(
        name="🎮 Account Features",
        value="✅ **200+ Days Old** - Trusted & aged account\n✅ **Maximum Money** - Fully stacked with cash\n✅ **Lucky Weapons** - Get weapons if you're lucky!\n✅ **Instant Delivery** - Fast & reliable",
        inline=True
    )
    
    embed.add_field(
        name="🎯 What You Get",
        value="🔸 200+ day old Roblox account\n🔸 1.750M clean + 1.750M bank money\n🔸 Weapons (if you get lucky!)\n🔸 Account credentials\n🔸 Setup instructions",
        inline=False
    )
    embed.set_footer(text="ZSupply South Bronx Trenches • Best value modded account for $2!")
    return embed

class SouthBronxShopView(discord.ui.View):
    def __init__(self, show_back=False):
        super().__init__(timeout=300)
        self.show_back = show_back

        # Add back button only if there are other tabs
        if self.show_back:
            self.add_item(self.create_back_button())

    def create_back_button(self):
        back_button = discord.ui.Button(label='Back', style=discord.ButtonStyle.secondary, emoji='⬅️')
        async def back_callback(interaction):
            await interaction.response.edit_message(embed=create_shop_selection_embed(), view=ShopSelectionView())
        back_button.callback = back_callback
        return back_button

    @discord.ui.button(label='South Bronx Modded Account - $2.00', style=discord.ButtonStyle.success, emoji='🎮')
    async def sb_modded_account_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        add_to_cart(interaction.user.id, "South Bronx Modded Account (1.750M Clean + 1.750M Bank + Lucky Weapons)", 2.00, "South Bronx The Trenches")
        embed = discord.Embed(
            title="✅ Added to Cart!",
            description="**South Bronx Modded Account** added to cart!\n\n**Added:** $2.00",
            color=0x00ff00
        )
        await interaction.response.edit_message(embed=embed, view=AddedToCartView("sb_account"))

    @discord.ui.button(label='View Cart', style=discord.ButtonStyle.primary, emoji='🛒')
    async def view_cart_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        cart_embed = create_cart_embed(interaction.user.id)
        await interaction.response.edit_message(embed=cart_embed, view=CartView(interaction.user.id, "South Bronx The Trenches"))

    @discord.ui.button(label='Contact Info', style=discord.ButtonStyle.danger, emoji='📞')
    async def contact_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_contact_embed(), view=ContactView("South Bronx The Trenches"))

# ROBLOX ALTS SHOP LOGIC START
def create_roblox_alts_embed():
    embed = discord.Embed(
        title="🎮 Roblox Alts Shop - Premium Aged Accounts",
        description="**Premium Roblox Accounts - 200+ Days Old**\n\nAll accounts come fully stacked for your chosen game!",
        color=0xff6b6b,
        timestamp=datetime.now()
    )
    embed.add_field(
        name="🔥 Account Features",
        value="✅ **200+ Days Old** - Trusted & Aged\n✅ **Fully Stacked** - Game-ready setup\n✅ **Premium Quality** - Hand-picked accounts\n✅ **Instant Delivery** - Fast & reliable",
        inline=False
    )
    embed.add_field(
        name="💰 Pricing",
        value="**$3.00 per account**\nIncludes full money & items for your game!",
        inline=True
    )
    embed.add_field(
        name="🎯 Available Games",
        value="• The Bronx 3\n• Philly Streets 2\n• South Bronx The Trenches",
        inline=True
    )
    embed.add_field(
        name="📦 What's Included",
        value="🔸 200+ day old Roblox account\n🔸 Stacked money & items\n🔸 Account credentials\n🔸 Setup instructions\n🔸 24/7 support",
        inline=False
    )
    embed.set_footer(text="ZSupply Roblox Alts • Select your game below")
    return embed

class RobloxAltsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label='TB3 Modded Account', style=discord.ButtonStyle.primary, emoji='🗽')
    async def tb3_account(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_roblox_account_info_embed("The Bronx 3"), view=RobloxOrderView("TB3"))

    @discord.ui.button(label='Philly Streets 2 Account', style=discord.ButtonStyle.success, emoji='🦅')
    async def philly_account(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_roblox_account_info_embed("Philly Streets 2"), view=RobloxOrderView("Philly"))

    @discord.ui.button(label='South Bronx Account', style=discord.ButtonStyle.danger, emoji='🔥')
    async def south_bronx_account(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_roblox_account_info_embed("South Bronx The Trenches"), view=RobloxOrderView("South Bronx"))

    @discord.ui.button(label='Back to Shop Selection', style=discord.ButtonStyle.secondary, emoji='🏠')
    async def back_to_shop_selection(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_shop_selection_embed(), view=ShopSelectionView())


def create_roblox_account_info_embed(game_name):
    embed = discord.Embed(
        title=f"🎮 {game_name} - Premium Account",
        description=f"**Premium Roblox Account for {game_name}**\n\nReady to play with stacked money and items!",
        color=0x7289da,
        timestamp=datetime.now()
    )

    # Set price based on game
    price = "$2.00" if game_name == "South Bronx The Trenches" else "$3.00"
    
    embed.add_field(
        name="🔥 Account Specifications",
        value=f"**Age:** 200+ Days Old\n**Game:** {game_name}\n**Status:** Fully Stacked\n**Price:** {price}",
        inline=True
    )

    embed.add_field(
        name="💰 Account Features",
        value="🔸 Maximum Money\n🔸 Stacked Items\n🔸 Lucky Weapons\n🔸 Premium Status\n🔸 Elite Access\n🔸 Full Support",
        inline=True
    )

    embed.add_field(
        name="📦 What You Get",
        value="✅ Account Username & Password\n✅ Stacked money & items\n✅ Setup guide\n✅ Backup email access\n✅ 24/7 customer support",
        inline=False
    )

    embed.add_field(
        name="⚠️ Important Notes",
        value="• Use responsibly\n• Account age guaranteed 200+ days\n• Money and items pre-loaded\n• Instant delivery after payment",
        inline=False
    )

    embed.set_footer(text="ZSupply • Premium Quality")
    return embed

class RobloxOrderView(discord.ui.View):
    def __init__(self, game_type):
        super().__init__(timeout=300)
        self.game_type = game_type

    @discord.ui.button(label='Add to Cart', style=discord.ButtonStyle.success, emoji='🛒')
    async def order_account(self, interaction: discord.Interaction, button: discord.ui.Button):
        game_names = {
            "TB3": "The Bronx 3",
            "Philly": "Philly Streets 2",
            "South Bronx": "South Bronx The Trenches"
        }
        game_name = game_names.get(self.game_type, self.game_type)
        
        # Set price based on game
        price = 2.00 if self.game_type == "South Bronx" else 3.00
        
        add_to_cart(interaction.user.id, f"Premium {game_name} Account (200+ Days Old)", price, f"Roblox Alts - {game_name}")
        
        embed = discord.Embed(
            title="✅ Added to Cart!",
            description=f"**Premium {game_name} Account** added to cart!\n\n**Added:** ${price:.2f}",
            color=0x00ff00
        )
        await interaction.response.edit_message(embed=embed, view=AddedToCartView("roblox_account"))

    @discord.ui.button(label='Back to Roblox Shop', style=discord.ButtonStyle.secondary, emoji='🎮')
    async def back_to_roblox_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_roblox_alts_embed(), view=RobloxAltsView())

    @discord.ui.button(label='Back to Shop Selection', style=discord.ButtonStyle.secondary, emoji='🏠')
    async def back_to_main_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_shop_selection_embed(), view=ShopSelectionView())

# Embed creation functions for shops
def create_main_shop_embed():
    embed = discord.Embed(
        title="🗽 The Bronx 3 - Premium Shop",
        description="**Welcome to The Bronx 3 Premium Shop**\n\nYour one-stop destination for all TB3 needs!",
        color=0x00ff00,
        timestamp=datetime.now()
    )
    embed.add_field(
        name="🔫 Available Products",
        value="• Premium Weapons Collection\n• Money & Bank Services\n• Luxury Watches\n• Special Packages",
        inline=False
    )
    embed.add_field(
        name="💰 Pricing",
        value="**Competitive prices for all items**\nBulk orders get discounts!",
        inline=True
    )
    embed.add_field(
        name="🚀 Features",
        value="✅ **Instant Delivery** - Fast & reliable\n✅ **24/7 Support** - Always here to help\n✅ **Secure Payment** - Safe transactions\n✅ **Quality Guaranteed** - Premium products",
        inline=True
    )
    embed.set_footer(text="ZSupply The Bronx 3 • Select your category below")
    return embed

def create_weapons_embed():
    embed = discord.Embed(
        title="🔫 The Bronx 3 - Weapons",
        description="**Premium weapon collection for The Bronx 3**\n\nChoose from our extensive arsenal!",
        color=0xff6b6b,
        timestamp=datetime.now()
    )

    # Split weapons into chunks for display
    weapon_chunks = [WEAPONS[i:i+10] for i in range(0, len(WEAPONS), 10)]

    for i, chunk in enumerate(weapon_chunks[:3]):  # Show first 3 chunks
        embed.add_field(
            name=f"🔥 Weapons Collection {i+1}",
            value="\n".join([f"• {weapon}" for weapon in chunk]),
            inline=True
        )

    embed.add_field(
        name="💰 Package Pricing",
        value="• **Safe Package** - $3.00\n• **Bag Package** - $2.00\n• **Trunk Package** - $1.00",
        inline=False
    )
    embed.set_footer(text="ZSupply TB3 Weapons • Select weapons below")
    return embed

def create_money_embed():
    embed = discord.Embed(
        title="💰 The Bronx 3 - Money Services",
        description="**Fast and secure money services for TB3**\n\nGet rich quick with our money packages!",
        color=0xffd700,
        timestamp=datetime.now()
    )
    embed.add_field(
        name="💵 Regular Services",
        value="• **Max Money 990k** - $1.00\n• **Max Bank 990k** - $1.00",
        inline=True
    )
    embed.add_field(
        name="💎 Gamepass Services",
        value="• **Max Money 1.6M** - $2.00\n• **Max Bank 1.6M** - $2.00",
        inline=True
    )
    embed.add_field(
        name="🚀 Features",
        value="✅ Instant delivery\n✅ Safe transactions\n✅ 24/7 support\n✅ Money guarantee",
        inline=False
    )
    embed.set_footer(text="ZSupply TB3 Money • Select your option below")
    return embed

def create_watches_embed():
    embed = discord.Embed(
        title="⌚ The Bronx 3 - Luxury Watches",
        description="**Premium watch collection for TB3**\n\nChoose from our exclusive luxury watches!",
        color=0x9b59b6,
        timestamp=datetime.now()
    )

    # Split watches into chunks for display
    watch_chunks = [WATCHES[i:i+8] for i in range(0, len(WATCHES), 8)]

    for i, chunk in enumerate(watch_chunks[:2]):  # Show first 2 chunks
        embed.add_field(
            name=f"⌚ Watch Collection {i+1}",
            value="\n".join([f"• {watch}" for watch in chunk]),
            inline=True
        )

    embed.add_field(
        name="💰 Pricing",
        value="**$1.00 per watch**\nMultiple watches available!",
        inline=False
    )
    embed.set_footer(text="ZSupply TB3 Watches • Select watches below")
    return embed

def create_contact_embed():
    embed = discord.Embed(
        title="📞 Contact Information",
        description="**Ready to place your order or need assistance?**",
        color=0xe74c3c,
        timestamp=datetime.now()
    )
    embed.add_field(
        name="📞 Contact Information",
        value="**Contact:** zpofe\n**Response Time:** Instant\n**Availability:** 24/7",
        inline=False
    )
    embed.add_field(
        name="💳 Payment Methods",
        value="• **CashApp:** https://cash.app/$EthanCreel1\n• **Apple Pay:** 7656156371\n• **PayPal:** Coming Soon (broken)",
        inline=False
    )
    embed.add_field(
        name="🚀 Delivery Information",
        value="• Instant delivery after payment\n• Setup assistance included\n• Full customer support\n• Quality guaranteed",
        inline=False
    )
    embed.set_footer(text="ZSupply • Contact us to complete your order!")
    return embed

# Create missing embed functions
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

def create_verify_embed():
    embed = discord.Embed(
        title="🛡️ Server Verification",
        description="**Welcome to the server!**\n\nTo access all channels and features, you need to complete verification.",
        color=0x00ff00,
        timestamp=datetime.now()
    )
    embed.add_field(
        name="📋 How to verify:",
        value="1. Click the Verify button below\n2. Copy the verification code shown\n3. Enter the code in the modal\n4. Submit to complete verification",
        inline=False
    )
    embed.add_field(
        name="🎯 What happens after verification?",
        value="• Access to all server channels\n• Ability to participate in discussions\n• Full server permissions\n• Welcome to the community!",
        inline=False
    )
    embed.set_footer(text="ZSells Verification • Click below to verify")
    return embed

class VerifyModal(discord.ui.Modal, title='Server Verification'):
    def __init__(self, verification_code):
        super().__init__()
        self.verification_code = verification_code

    code_input = discord.ui.TextInput(
        label='Enter Verification Code',
        placeholder='Enter the code shown above...',
        style=discord.TextStyle.short,
        max_length=10,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        if self.code_input.value == self.verification_code:
            # Add verified role (you may need to adjust the role name/ID)
            guild = interaction.guild
            verified_role = discord.utils.get(guild.roles, name="Verified")

            if not verified_role:
                # Create verified role if it doesn't exist
                try:
                    verified_role = await guild.create_role(name="Verified", color=0x00ff00)
                    print(f"✅ Created Verified role")
                except:
                    pass

            if verified_role:
                try:
                    await interaction.user.add_roles(verified_role)
                    embed = discord.Embed(
                        title="✅ Verification Successful!",
                        description="You have been successfully verified and now have access to all server channels!",
                        color=0x00ff00
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                except:
                    embed = discord.Embed(
                        title="✅ Verification Complete!",
                        description="You have been verified! Welcome to the server!",
                        color=0x00ff00
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                embed = discord.Embed(
                    title="✅ Verification Complete!",
                    description="You have been verified! Welcome to the server!",
                    color=0x00ff00
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            embed = discord.Embed(
                title="❌ Verification Failed",
                description="Incorrect verification code. Please try again.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='Verify', style=discord.ButtonStyle.success, emoji='✅', custom_id='server_verify')
    async def verify_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        import random
        import string

        # Generate random verification code
        verification_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

        # Show the code first
        embed = discord.Embed(
            title="🔐 Verification Code",
            description=f"**Your verification code is:**\n\n`{verification_code}`\n\nCopy this code and enter it in the next step.",
            color=0x3498db
        )
        embed.set_footer(text="Copy the code above and click OK to continue")

        # Create a simple continue view
        continue_view = ContinueVerifyView(verification_code)
        await interaction.response.send_message(embed=embed, view=continue_view, ephemeral=True)

class ContinueVerifyView(discord.ui.View):
    def __init__(self, verification_code):
        super().__init__(timeout=300)
        self.verification_code = verification_code

    @discord.ui.button(label='Continue Verification', style=discord.ButtonStyle.primary, emoji='➡️')
    async def continue_verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = VerifyModal(self.verification_code)
        await interaction.response.send_modal(modal)

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
    bot.add_view(VerifyView())
    bot.add_view(OrderTicketControlView(None))

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

    # Comprehensive analysis for each guild
    for guild in bot.guilds:
        print(f"\n🏰 ANALYZING GUILD: {guild.name}")
        print(f"   Guild ID: {guild.id}")
        print(f"   Members: {guild.member_count}")
        print("─" * 50)

        # Perform full guild analysis
        try:
            analysis = analyze_guild_structure(guild)
            GUILD_ANALYSIS[guild.id] = analysis

            # Update global channels
            CHANNELS.update(analysis['channels']['detected_channels'])

            print(f"\n📊 GUILD STATISTICS:")
            print(f"   📝 Text Channels: {analysis['channels']['total_text']}")
            print(f"   🔊 Voice Channels: {analysis['channels']['total_voice']}")
            print(f"   📁 Categories: {analysis['channels']['total_categories']}")
            print(f"   🎭 Roles: {analysis['roles']['total_roles']}")
            print(f"   🔰 Boost Tier: {analysis['guild_info']['boost_tier']}")
            print(f"   🚀 Boost Count: {analysis['guild_info']['boost_count']}")

            if analysis['guild_info']['features']:
                print(f"   ✨ Features: {', '.join(analysis['guild_info']['features'][:5])}")

            print(f"\n👥 MEMBER HIERARCHY:")
            owner = analysis['members']['owner']
            if owner:
                print(f"   👑 Owner: {owner['name']}")
            print(f"   🛡️ Admins: {len(analysis['members']['admins'])}")
            print(f"   🔨 Moderators: {len(analysis['members']['moderators'])}")
            print(f"   👥 Staff: {len(analysis['members']['staff'])}")
            print(f"   🤖 Bots: {len(analysis['members']['bots'])}")

            print(f"\n🎯 DETECTED CHANNELS:")
            detected_channels = analysis['channels']['detected_channels']
            if detected_channels:
                for channel_type, channel_id in detected_channels.items():
                    channel = guild.get_channel(channel_id)
                    if channel:
                        perms = "✅" if check_channel_permissions(channel) else "❌"
                        print(f"   {perms} {channel_type}: #{channel.name}")
            else:
                print("   ⚠️ No channels auto-detected")
                print("   💡 Suggestion: Create channels with descriptive names")
                print("      Examples: #support, #rules, #announcements, #welcome")

        except Exception as e:
            print(f"   ⚠️ Error analyzing guild: {e}")

    print("\n" + "━" * 50)
    print("🚀 SYSTEM INITIALIZATION COMPLETE")
    print("━" * 50)

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

# Function to delete duplicate bot messages
async def delete_duplicate_shop_messages(channel, new_message):
    """Delete duplicate shop messages from bot in the same channel"""
    try:
        # Check last 20 messages for duplicates
        async for message in channel.history(limit=20):
            if (message.author.id == bot.user.id and
                message.id != new_message.id and
                message.embeds and new_message.embeds):
                # Check if both messages have shop embeds with same title
                old_title = message.embeds[0].title if message.embeds[0].title else ""
                new_title = new_message.embeds[0].title if new_message.embeds[0].title else ""

                # If both are shop embeds, delete the older one
                if any(shop in old_title for shop in ["Bronx 3", "Philly Streets 2", "South Bronx", "Roblox Alts"]) and \
                   any(shop in new_title for shop in ["Bronx 3", "Philly Streets 2", "South Bronx", "Roblox Alts"]):
                    try:
                        await message.delete()
                        print(f"🗑️ Deleted duplicate shop message in #{channel.name}")
                    except discord.NotFound:
                        pass  # Message already deleted
                    except discord.Forbidden:
                        pass  # No permission to delete
                    break
    except Exception as e:
        print(f"⚠️ Error checking for duplicates: {e}")

# Slash commands for spawning shops
@bot.tree.command(name="spawn_tb3", description="Spawn The Bronx 3 shop")
async def spawn_tb3(interaction: discord.Interaction):
    """Spawn The Bronx 3 shop interface"""
    try:
        # Acknowledge the interaction immediately
        await interaction.response.defer(ephemeral=True)
        
        embed = create_main_shop_embed()
        view = MainShopView()
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
    except discord.NotFound:
        # Interaction expired, ignore silently
        pass
    except discord.InteractionResponded:
        # Already responded, ignore
        pass
    except Exception as e:
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"Error spawning TB3 shop: {e}", ephemeral=True)
            else:
                await interaction.followup.send(f"Error spawning TB3 shop: {e}", ephemeral=True)
        except (discord.NotFound, discord.InteractionResponded):
            pass

@bot.tree.command(name="spawn_ps", description="Spawn Philly Streets 2 shop")
async def spawn_ps(interaction: discord.Interaction):
    """Spawn Philly Streets 2 shop interface"""
    try:
        # Acknowledge the interaction immediately
        await interaction.response.defer(ephemeral=True)
        
        embed = create_philly_shop_embed()
        view = PhillyShopView(show_back=False)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
    except discord.NotFound:
        # Interaction expired, ignore silently
        pass
    except discord.InteractionResponded:
        # Already responded, ignore
        pass
    except Exception as e:
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"Error spawning PS2 shop: {e}", ephemeral=True)
            else:
                await interaction.followup.send(f"Error spawning PS2 shop: {e}", ephemeral=True)
        except (discord.NotFound, discord.InteractionResponded):
            pass

@bot.tree.command(name="spawn_sb", description="Spawn South Bronx The Trenches shop")
async def spawn_sb(interaction: discord.Interaction):
    """Spawn South Bronx The Trenches shop interface"""
    try:
        # Acknowledge the interaction immediately
        await interaction.response.defer(ephemeral=True)
        
        embed = create_south_bronx_shop_embed()
        view = SouthBronxShopView(show_back=False)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
    except discord.NotFound:
        # Interaction expired, ignore silently
        pass
    except discord.InteractionResponded:
        # Already responded, ignore
        pass
    except Exception as e:
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"Error spawning SB shop: {e}", ephemeral=True)
            else:
                await interaction.followup.send(f"Error spawning SB shop: {e}", ephemeral=True)
        except (discord.NotFound, discord.InteractionResponded):
            # Ignore if interaction expired or already responded
            pass

@bot.tree.command(name="spawn_roblox", description="Spawn Roblox Alts shop")
async def spawn_roblox(interaction: discord.Interaction):
    """Spawn Roblox Alts shop interface"""
    try:
        # Acknowledge the interaction immediately
        await interaction.response.defer(ephemeral=True)
        
        embed = create_roblox_alts_embed()
        view = RobloxAltsView()
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
    except discord.NotFound:
        # Interaction expired, ignore silently
        pass
    except discord.InteractionResponded:
        # Already responded, ignore
        pass
    except Exception as e:
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"Error spawning Roblox shop: {e}", ephemeral=True)
            else:
                await interaction.followup.send(f"Error spawning Roblox shop: {e}", ephemeral=True)
        except (discord.NotFound, discord.InteractionResponded):
            pass

@bot.tree.command(name="spawn_support", description="Spawn support ticket panel")
async def spawn_support(interaction: discord.Interaction):
    """Spawn support ticket interface"""
    try:
        # Acknowledge the interaction immediately
        await interaction.response.defer()
        
        embed = create_support_embed()
        view = SupportView()
        await interaction.followup.send(embed=embed, view=view)
    except discord.NotFound:
        # Interaction expired, ignore silently
        pass
    except discord.InteractionResponded:
        # Already responded, ignore
        pass
    except Exception as e:
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"Error spawning support panel: {e}", ephemeral=True)
            else:
                await interaction.followup.send(f"Error spawning support panel: {e}", ephemeral=True)
        except (discord.NotFound, discord.InteractionResponded):
            pass

@bot.tree.command(name="spawn_gang", description="Spawn gang recruitment panel")
async def spawn_gang(interaction: discord.Interaction):
    """Spawn gang recruitment interface"""
    try:
        await interaction.response.defer()
        
        embed = create_gang_embed()
        view = GangRecruitmentView()
        await interaction.followup.send(embed=embed, view=view)
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
        await interaction.response.defer()
        
        embed = create_tos_embed()
        await interaction.followup.send(embed=embed)
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
        await interaction.response.defer()
        
        embed = create_rules_embed()
        await interaction.followup.send(embed=embed)
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
        await interaction.response.defer()
        
        embed = create_welcome_embed()
        await interaction.followup.send(embed=embed)
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
        await interaction.response.defer(ephemeral=True)
        
        news_channel_id = 1407347202329940000
        news_channel = bot.get_channel(news_channel_id)

        if not news_channel:
            await interaction.followup.send("❌ News channel not found!", ephemeral=True)
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

        # Send to news channel
        await news_channel.send(embed=embed)
        await interaction.followup.send(f"✅ News posted in {news_channel.mention}!", ephemeral=True)

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

@bot.tree.command(name="spawn_verify", description="Spawn verification panel")
async def spawn_verify(interaction: discord.Interaction):
    """Spawn server verification panel"""
    try:
        await interaction.response.defer()
        
        embed = create_verify_embed()
        view = VerifyView()
        await interaction.followup.send(embed=embed, view=view)
    except discord.NotFound:
        pass
    except discord.InteractionResponded:
        pass
    except Exception as e:
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"Error spawning verify panel: {e}", ephemeral=True)
            else:
                await interaction.followup.send(f"Error spawning verify panel: {e}", ephemeral=True)
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