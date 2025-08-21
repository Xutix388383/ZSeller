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

# Shop data (keeping existing shop functionality)
WEAPONS = [
    "GoldenButton", "GreenSwitch", "BlueTips/Switch", "OrangeButton", "BinaryTrigger",
    "YellowButtonSwitch", "FullyARP", "FullyDraco", "Fully-MicroAR", "Cyanbutton",
    "100RndTanG19", "300ARG", "VP9Scope", "MasterPiece30", "GSwitch",
    "G17WittaButton", "G19Switch", "G20Switch", "G21Switch", "G22 Switch",
    "G23 Switch", "G40 Switch", "G42 Switch", "Fully-FN", "BinaryARP",
    "BinaryDraco", "CustomAR9"
]

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

async def create_private_order_ticket(interaction, shop_name, category):
    """Create a private order ticket for purchases"""
    global TICKET_COUNTER
    ticket_number = TICKET_COUNTER
    TICKET_COUNTER += 1

    # Create ticket channel
    guild = interaction.guild
    category_obj = discord.utils.get(guild.categories, name="Order Tickets")
    if not category_obj:
        category_obj = await guild.create_category("Order Tickets")

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
        f"order-{ticket_number:04d}",
        category=category_obj,
        overwrites=overwrites
    )

    # Store ticket data
    ACTIVE_ORDER_TICKETS[str(ticket_channel.id)] = {
        'user_id': interaction.user.id,
        'ticket_number': ticket_number,
        'shop': shop_name,
        'category': category,
        'created_at': datetime.now().isoformat()
    }
    save_data()

    # Create order ticket embed
    embed = discord.Embed(
        title=f"🛒 Order Ticket #{ticket_number:04d}",
        description=f"**Customer:** {interaction.user.mention}\n**Shop:** {shop_name}\n**Product:** {category}",
        color=0x00ff00,
        timestamp=datetime.now()
    )

    embed.add_field(
        name="💳 Payment Methods",
        value="• **CashApp:** https://cash.app/$EthanCreel1\n• **Apple Pay:** 7656156371\n• **PayPal:** Coming Soon (broken)",
        inline=False
    )

    embed.add_field(
        name="📋 Next Steps",
        value="1️⃣ Zpofe will be with you shortly\n2️⃣ Complete payment using methods above\n3️⃣ Receive your order instantly\n4️⃣ Get setup support if needed",
        inline=False
    )

    embed.set_footer(text="ZSupply Order System • Zpofe will assist you")

    # Ping roles
    ping_message = "**Zpofe will be with you shortly!**\n\n"
    if STAFF_ROLE_ID:
        ping_message += f"<@&{STAFF_ROLE_ID}> "
    if OWNER_ROLE_ID:
        ping_message += f"<@&{OWNER_ROLE_ID}>"

    view = OrderTicketControlView(ticket_channel.id)
    await ticket_channel.send(ping_message, embed=embed, view=view)

    await interaction.response.send_message(f"✅ Order ticket created! Please check {ticket_channel.mention} - Zpofe will be with you shortly!", ephemeral=True)

class OrderTicketControlView(discord.ui.View):
    def __init__(self, channel_id):
        super().__init__(timeout=None)
        self.channel_id = channel_id

    @discord.ui.button(label='Complete Order', style=discord.ButtonStyle.success, emoji='✅', custom_id='order_complete')
    async def complete_order(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(self.channel_id) in ACTIVE_ORDER_TICKETS:
            del ACTIVE_ORDER_TICKETS[str(self.channel_id)]
            save_data()

        embed = discord.Embed(
            title="✅ Order Completed",
            description="Thank you for your purchase! This ticket will be closed in 10 seconds.",
            color=0x00ff00
        )
        await interaction.response.send_message(embed=embed)

        import asyncio
        await asyncio.sleep(10)
        await interaction.followup.delete_message(interaction.message.id)
        await interaction.channel.delete()

    @discord.ui.button(label='Close Ticket', style=discord.ButtonStyle.danger, emoji='🔒', custom_id='order_close')
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(self.channel_id) in ACTIVE_ORDER_TICKETS:
            del ACTIVE_ORDER_TICKETS[str(self.channel_id)]
            save_data()

        embed = discord.Embed(
            title="🔒 Order Ticket Closed",
            description="This order ticket has been closed. The channel will be deleted in 10 seconds.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed)

        import asyncio
        await asyncio.sleep(10)
        await interaction.followup.delete_message(interaction.message.id)
        await interaction.channel.delete()

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
                description="You're about to join one of the most elite gangs!\n\n**Click the link below to join:**\nhttps://discord.gg/C6agZhmhCA",
                color=0x7289da
            )
            embed.set_footer(text="STK Gang • Elite Members Only")

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

    @discord.ui.button(label='Contact Info', style=discord.ButtonStyle.danger, emoji='📞')
    async def contact_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_contact_embed(), view=ContactView())

class WeaponsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.select(
        placeholder="Choose weapons (multiple allowed)...",
        options=[discord.SelectOption(label=weapon, value=weapon, emoji="🔫") for weapon in WEAPONS[:25]],
        max_values=len(WEAPONS[:25])
    )
    async def weapon_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        selected_weapons = select.values
        if len(selected_weapons) == 1:
            embed = create_weapon_package_embed(selected_weapons[0])
        else:
            embed = create_multi_weapon_package_embed(selected_weapons)
        view = WeaponPackageView(selected_weapons)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label='Back to Shop', style=discord.ButtonStyle.secondary)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_main_shop_embed(), view=MainShopView())

class WeaponPackageView(discord.ui.View):
    def __init__(self, weapons):
        super().__init__(timeout=300)
        self.weapons = weapons if isinstance(weapons, list) else [weapons]

    @discord.ui.button(label='Safe Package - $3.00', style=discord.ButtonStyle.primary)
    async def safe_package(self, interaction: discord.Interaction, button: discord.ui.Button):
        weapons_text = ", ".join(self.weapons) if len(self.weapons) <= 5 else f"{len(self.weapons)} weapons selected"
        await create_private_order_ticket(interaction, "The Bronx 3", f"Weapons - Safe Package ({weapons_text})")

    @discord.ui.button(label='Bag Package - $2.00', style=discord.ButtonStyle.success)
    async def bag_package(self, interaction: discord.Interaction, button: discord.ui.Button):
        weapons_text = ", ".join(self.weapons) if len(self.weapons) <= 5 else f"{len(self.weapons)} weapons selected"
        await create_private_order_ticket(interaction, "The Bronx 3", f"Weapons - Bag Package ({weapons_text})")

    @discord.ui.button(label='Trunk Package - $1.00', style=discord.ButtonStyle.secondary)
    async def trunk_package(self, interaction: discord.Interaction, button: discord.ui.Button):
        weapons_text = ", ".join(self.weapons) if len(self.weapons) <= 5 else f"{len(self.weapons)} weapons selected"
        await create_private_order_ticket(interaction, "The Bronx 3", f"Weapons - Trunk Package ({weapons_text})")

    @discord.ui.button(label='Back', style=discord.ButtonStyle.danger)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_weapons_embed(), view=WeaponsView())

class MoneyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label='💵 Regular Money - $1.00', style=discord.ButtonStyle.primary)
    async def regular_money(self, interaction: discord.Interaction, button: discord.ui.Button):
        await create_private_order_ticket(interaction, "The Bronx 3", "Max Money 990k - $1.00")

    @discord.ui.button(label='🏦 Regular Bank - $1.00', style=discord.ButtonStyle.primary)
    async def regular_bank(self, interaction: discord.Interaction, button: discord.ui.Button):
        await create_private_order_ticket(interaction, "The Bronx 3", "Max Bank 990k - $1.00")

    @discord.ui.button(label='💎 Gamepass Money - $2.00', style=discord.ButtonStyle.success)
    async def gamepass_money(self, interaction: discord.Interaction, button: discord.ui.Button):
        await create_private_order_ticket(interaction, "The Bronx 3", "Max Money 1.6M (Extra Money Pass) - $2.00")

    @discord.ui.button(label='💳 Gamepass Bank - $2.00', style=discord.ButtonStyle.success)
    async def gamepass_bank(self, interaction: discord.Interaction, button: discord.ui.Button):
        await create_private_order_ticket(interaction, "The Bronx 3", "Max Bank 1.6M (Extra Bank Pass) - $2.00")

    @discord.ui.button(label='Back to Shop Selection', style=discord.ButtonStyle.secondary, emoji='🏠')
    async def back_to_shop_selection(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_shop_selection_embed(), view=ShopSelectionView())

    @discord.ui.button(label='Back to The Bronx 3', style=discord.ButtonStyle.secondary, emoji='🗽')
    async def back_to_bronx3(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_main_shop_embed(), view=MainShopView())

class WatchesView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.select(
        placeholder="Choose watches (multiple allowed)...",
        options=[discord.SelectOption(label=watch, value=watch, emoji="⌚") for watch in WATCHES],
        max_values=len(WATCHES)
    )
    async def watch_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        selected_watches = select.values
        watches_text = ", ".join(selected_watches) if len(selected_watches) <= 3 else f"{len(selected_watches)} watches selected"
        price = len(selected_watches) * 1.00
        await create_private_order_ticket(interaction, "The Bronx 3", f"Watches ({watches_text}) - ${price:.2f}")

    @discord.ui.button(label='Back to Shop Selection', style=discord.ButtonStyle.secondary, emoji='🏠')
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_shop_selection_embed(), view=ShopSelectionView())

    @discord.ui.button(label='Back to The Bronx 3', style=discord.ButtonStyle.secondary, emoji='🗽')
    async def back_to_bronx3(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_main_shop_embed(), view=MainShopView())

class ContactView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label='Back to Shop Selection', style=discord.ButtonStyle.secondary, emoji='🏠')
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_shop_selection_embed(), view=ShopSelectionView())

    @discord.ui.button(label='Back to The Bronx 3', style=discord.ButtonStyle.secondary, emoji='🗽')
    async def back_to_bronx3(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_main_shop_embed(), view=MainShopView())

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
        # Logic for Bronx 3 shop
        await interaction.response.edit_message(embed=create_main_shop_embed(), view=MainShopView()) # Revert to original shop for now

    @discord.ui.button(label='Philly Streets 2', style=discord.ButtonStyle.success, emoji='🦅')
    async def philly_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_philly_shop_embed(), view=PhillyShopView())

    @discord.ui.button(label='South Bronx The Trenches', style=discord.ButtonStyle.danger, emoji='🔥')
    async def south_bronx_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_south_bronx_shop_embed(), view=SouthBronxShopView())

    @discord.ui.button(label='Roblox Alts Shop', style=discord.ButtonStyle.secondary, emoji='🎮')
    async def roblox_alts_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Logic for Roblox Alts shop
        await interaction.response.edit_message(embed=create_roblox_alts_embed(), view=RobloxAltsView())

    @discord.ui.button(label='Back to Shop Selection', style=discord.ButtonStyle.secondary, emoji='🏠')
    async def back_to_shop_selection(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_shop_selection_embed(), view=ShopSelectionView())

    @discord.ui.button(label='Back to Main Shop', style=discord.ButtonStyle.secondary, emoji='🏠')
    async def back_to_main_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_shop_selection_embed(), view=ShopSelectionView())

# PHILLY STREETS 2 SHOP LOGIC START
def create_philly_shop_embed():
    embed = discord.Embed(
        title="🦅 Philly Streets 2 - Premium Shop",
        description="**Welcome to Philly Streets 2 Premium Shop**\n\nYour one-stop destination for all PS2 needs!",
        color=0x00ff00,
        timestamp=datetime.now()
    )
    embed.add_field(
        name="🔫 Available Products",
        value="• Premium Weapons Collection\n• Money & Bank Services\n• Luxury Items\n• Special Packages",
        inline=False
    )
    embed.add_field(
        name="💰 Pricing",
        value="**Competitive prices for all items**\nBulk discounts available!",
        inline=True
    )
    embed.add_field(
        name="🚀 Features",
        value="✅ **Instant Delivery** - Fast & reliable\n✅ **24/7 Support** - Always here to help\n✅ **Secure Payment** - Safe transactions\n✅ **Quality Guaranteed** - Premium products",
        inline=True
    )
    embed.add_field(
        name="📦 What's Included",
        value="🔸 High-quality game items\n🔸 Fast delivery service\n🔸 Customer support\n🔸 Setup assistance",
        inline=False
    )
    embed.set_footer(text="ZSupply Philly Streets 2 • Select your category below")
    return embed

class PhillyShopView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label='Weapons', style=discord.ButtonStyle.primary, emoji='🔫')
    async def philly_weapons_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_philly_weapons_embed(), view=PhillyWeaponsView())

    @discord.ui.button(label='Money Services', style=discord.ButtonStyle.success, emoji='💰')
    async def philly_money_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_philly_money_embed(), view=PhillyMoneyView())

    @discord.ui.button(label='Special Items', style=discord.ButtonStyle.secondary, emoji='⭐')
    async def philly_special_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_philly_special_embed(), view=PhillySpecialView())

    @discord.ui.button(label='Contact Info', style=discord.ButtonStyle.danger, emoji='📞')
    async def philly_contact_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_philly_contact_embed(), view=PhillyContactView())

    @discord.ui.button(label='Back to Shop Selection', style=discord.ButtonStyle.secondary, emoji='🏠')
    async def back_to_shop_selection(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_shop_selection_embed(), view=ShopSelectionView())

    @discord.ui.button(label='Back to Main Shop', style=discord.ButtonStyle.secondary, emoji='🏠')
    async def back_to_main_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_shop_selection_embed(), view=ShopSelectionView())

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

    @discord.ui.button(label='Order Weapons', style=discord.ButtonStyle.success, emoji='💳')
    async def order_weapons(self, interaction: discord.Interaction, button: discord.ui.Button):
        await create_private_order_ticket(interaction, "Philly Streets 2", "Weapons")

    @discord.ui.button(label='Back to PS2 Shop', style=discord.ButtonStyle.secondary, emoji='🦅')
    async def back_to_philly_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_philly_shop_embed(), view=PhillyShopView())

    @discord.ui.button(label='Back to Shop Selection', style=discord.ButtonStyle.secondary, emoji='🏠')
    async def back_to_shop_selection(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_shop_selection_embed(), view=ShopSelectionView())

    @discord.ui.button(label='Back to Main Shop', style=discord.ButtonStyle.secondary, emoji='🏠')
    async def back_to_main_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_shop_selection_embed(), view=ShopSelectionView())

def create_philly_money_embed():
    embed = discord.Embed(
        title="💰 Philly Streets 2 - Money Services",
        description="**Fast and secure money services for PS2**\n\nGet rich quick with our money packages!",
        color=0xffd700,
        timestamp=datetime.now()
    )
    embed.add_field(
        name="💵 Money Packages",
        value="• Basic Money - $1.50\n• Premium Money - $2.50\n• VIP Money - $4.00\n• Ultimate Package - $6.00",
        inline=False
    )
    embed.add_field(
        name="🏦 Bank Services",
        value="• Bank Protection - $1.00\n• Max Bank Fill - $2.00\n• Bank Security - $1.50",
        inline=False
    )
    embed.set_footer(text="ZSupply PS2 Money • Fast delivery guaranteed")
    return embed

class PhillyMoneyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label='Order Money Package', style=discord.ButtonStyle.success, emoji='💳')
    async def order_money(self, interaction: discord.Interaction, button: discord.ui.Button):
        await create_private_order_ticket(interaction, "Philly Streets 2", "Money Services")

    @discord.ui.button(label='Back to PS2 Shop', style=discord.ButtonStyle.secondary, emoji='🦅')
    async def back_to_philly_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_philly_shop_embed(), view=PhillyShopView())

    @discord.ui.button(label='Back to Shop Selection', style=discord.ButtonStyle.secondary, emoji='🏠')
    async def back_to_shop_selection(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_shop_selection_embed(), view=ShopSelectionView())

    @discord.ui.button(label='Back to Main Shop', style=discord.ButtonStyle.secondary, emoji='🏠')
    async def back_to_main_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_shop_selection_embed(), view=ShopSelectionView())

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

    @discord.ui.button(label='Order Special Items', style=discord.ButtonStyle.success, emoji='💳')
    async def order_special(self, interaction: discord.Interaction, button: discord.ui.Button):
        await create_private_order_ticket(interaction, "Philly Streets 2", "Special Items")

    @discord.ui.button(label='Back to PS2 Shop', style=discord.ButtonStyle.secondary, emoji='🦅')
    async def back_to_philly_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_philly_shop_embed(), view=PhillyShopView())

    @discord.ui.button(label='Back to Shop Selection', style=discord.ButtonStyle.secondary, emoji='🏠')
    async def back_to_shop_selection(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_shop_selection_embed(), view=ShopSelectionView())

    @discord.ui.button(label='Back to Main Shop', style=discord.ButtonStyle.secondary, emoji='🏠')
    async def back_to_main_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_shop_selection_embed(), view=ShopSelectionView())

def create_philly_contact_embed():
    embed = discord.Embed(
        title="📞 Philly Streets 2 - Contact Info",
        description="**Ready to place your PS2 order?**",
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
        value="• CashApp\n• Apple Pay\n• Secure & Fast",
        inline=True
    )
    embed.add_field(
        name="🚀 Delivery",
        value="• Instant delivery\n• Setup included\n• Full support",
        inline=True
    )
    embed.set_footer(text="ZSupply PS2 • Contact us to complete your order!")
    return embed

class PhillyContactView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label='Back to PS2 Shop', style=discord.ButtonStyle.secondary, emoji='🦅')
    async def back_to_philly_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_philly_shop_embed(), view=PhillyShopView())

    @discord.ui.button(label='Back to Shop Selection', style=discord.ButtonStyle.secondary, emoji='🏠')
    async def back_to_shop_selection(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_shop_selection_embed(), view=ShopSelectionView())

    @discord.ui.button(label='Back to Main Shop', style=discord.ButtonStyle.secondary, emoji='🏠')
    async def back_to_main_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_shop_selection_embed(), view=ShopSelectionView())

def create_philly_order_embed(category):
    embed = discord.Embed(
        title="📋 Philly Streets 2 - Order Information",
        description="**Ready to complete your PS2 order?**",
        color=0x00ff00,
        timestamp=datetime.now()
    )
    embed.add_field(
        name="🎮 Order Details",
        value=f"**Game:** Philly Streets 2\n**Category:** {category}\n**Status:** Ready to order",
        inline=False
    )
    embed.add_field(
        name="📞 Contact to Order",
        value="**Contact:** zpofe\n**Response:** Instant",
        inline=True
    )
    embed.add_field(
        name="💳 Payment Methods",
        value="• **CashApp:** https://cash.app/$EthanCreel1\n• **Apple Pay:** 7656156371\n• **PayPal:** Coming Soon (broken)",
        inline=False
    )
    embed.add_field(
        name="⚡ Order Process",
        value="1️⃣ Contact us with your selection\n2️⃣ Complete payment\n3️⃣ Receive your items instantly\n4️⃣ Get setup support\n5️⃣ Enjoy your PS2 experience!",
        inline=False
    )
    embed.set_footer(text="ZSupply PS2 • Contact us to complete your order!")
    return embed

class PhillyOrderView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label='Back to PS2 Shop', style=discord.ButtonStyle.primary, emoji='🦅')
    async def back_to_philly_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_philly_shop_embed(), view=PhillyShopView())

    @discord.ui.button(label='Back to Shop Selection', style=discord.ButtonStyle.secondary, emoji='🏠')
    async def back_to_shop_selection(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_shop_selection_embed(), view=ShopSelectionView())

    @discord.ui.button(label='Back to Main Shop', style=discord.ButtonStyle.secondary, emoji='🏠')
    async def back_to_main_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_shop_selection_embed(), view=ShopSelectionView())

# SOUTH BRONX THE TRENCHES SHOP LOGIC START
def create_south_bronx_shop_embed():
    embed = discord.Embed(
        title="🔥 South Bronx The Trenches - Elite Shop",
        description="**Welcome to South Bronx The Trenches Elite Shop**\n\nThe most hardcore shop for the toughest game!",
        color=0xff0000,
        timestamp=datetime.now()
    )
    embed.add_field(
        name="💀 Elite Products",
        value="• Hardcore Weapons Arsenal\n• Street Money Services\n• Survival Gear\n• Elite Packages",
        inline=False
    )
    embed.add_field(
        name="💰 Street Pricing",
        value="**Raw deals for raw streets**\nSurvival prices for survivors!",
        inline=True
    )
    embed.add_field(
        name="🔥 Trenches Features",
        value="✅ **Instant Drop** - Fast delivery\n✅ **24/7 Hustle** - Always available\n✅ **Street Secure** - Safe deals\n✅ **Elite Quality** - Hardcore gear",
        inline=True
    )
    embed.add_field(
        name="⚡ Survival Package",
        value="🔸 Combat-ready items\n🔸 Street survival gear\n🔸 Elite support network\n🔸 Trenches expertise",
        inline=False
    )
    embed.set_footer(text="ZSupply South Bronx Trenches • Elite survival gear")
    return embed

class SouthBronxShopView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label='Arsenal', style=discord.ButtonStyle.danger, emoji='💀')
    async def sb_weapons_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_sb_weapons_embed(), view=SBWeaponsView())

    @discord.ui.button(label='Street Money', style=discord.ButtonStyle.success, emoji='💵')
    async def sb_money_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_sb_money_embed(), view=SBMoneyView())

    @discord.ui.button(label='Survival Gear', style=discord.ButtonStyle.primary, emoji='🛡️')
    async def sb_survival_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_sb_survival_embed(), view=SBSurvivalView())

    @discord.ui.button(label='Contact', style=discord.ButtonStyle.secondary, emoji='📱')
    async def sb_contact_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_sb_contact_embed(), view=SBContactView())

    @discord.ui.button(label='Back to Shop Selection', style=discord.ButtonStyle.secondary, emoji='🏠')
    async def back_to_shop_selection(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_shop_selection_embed(), view=ShopSelectionView())

    @discord.ui.button(label='Back to Main Shop', style=discord.ButtonStyle.secondary, emoji='🏠')
    async def back_to_main_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_shop_selection_embed(), view=ShopSelectionView())

def create_sb_weapons_embed():
    embed = discord.Embed(
        title="💀 South Bronx Trenches - Arsenal",
        description="**Hardcore weapons for the streets**\n\nSurvive the trenches with elite firepower!",
        color=0x8b0000,
        timestamp=datetime.now()
    )
    embed.add_field(
        name="🔫 Street Arsenal",
        value="• Trenches Special - $4.00\n• Street Sweeper - $5.00\n• Survival Kit - $3.50\n• Elite Package - $7.00\n• Hardcore Bundle - $6.50",
        inline=False
    )
    embed.add_field(
        name="💰 Street Prices",
        value="**Starting from $3.50**\nReal prices for real gear!",
        inline=True
    )
    embed.add_field(
        name="⚡ Combat Ready",
        value="✅ Instant deployment\n✅ Street tested\n✅ Combat proven\n✅ Elite grade",
        inline=True
    )
    embed.set_footer(text="ZSupply SB Trenches • Combat grade arsenal")
    return embed

class SBWeaponsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label='Order Arsenal', style=discord.ButtonStyle.danger, emoji='💀')
    async def order_weapons(self, interaction: discord.Interaction, button: discord.ui.Button):
        await create_private_order_ticket(interaction, "South Bronx The Trenches", "Arsenal")

    @discord.ui.button(label='Back to SB Shop', style=discord.ButtonStyle.secondary, emoji='🔥')
    async def back_to_sb_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_south_bronx_shop_embed(), view=SouthBronxShopView())

    @discord.ui.button(label='Back to Shop Selection', style=discord.ButtonStyle.secondary, emoji='🏠')
    async def back_to_shop_selection(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_shop_selection_embed(), view=ShopSelectionView())

    @discord.ui.button(label='Back to Main Shop', style=discord.ButtonStyle.secondary, emoji='🏠')
    async def back_to_main_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_shop_selection_embed(), view=ShopSelectionView())

def create_sb_money_embed():
    embed = discord.Embed(
        title="💵 South Bronx Trenches - Street Money",
        description="**Street cash for street survival**\n\nGet paid in the trenches!",
        color=0x228b22,
        timestamp=datetime.now()
    )
    embed.add_field(
        name="💸 Street Cash",
        value="• Hustle Package - $2.00\n• Street Money - $3.50\n• Elite Cash - $5.00\n• Trenches VIP - $7.50",
        inline=False
    )
    embed.add_field(
        name="🏪 Street Banking",
        value="• Safe Stash - $1.50\n• Elite Vault - $3.00\n• Trenches Bank - $2.50",
        inline=False
    )
    embed.set_footer(text="ZSupply SB Trenches • Street money guaranteed")
    return embed

class SBMoneyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label='Order Street Money', style=discord.ButtonStyle.success, emoji='💵')
    async def order_money(self, interaction: discord.Interaction, button: discord.ui.Button):
        await create_private_order_ticket(interaction, "South Bronx The Trenches", "Street Money")

    @discord.ui.button(label='Back to SB Shop', style=discord.ButtonStyle.secondary, emoji='🔥')
    async def back_to_sb_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_south_bronx_shop_embed(), view=SouthBronxShopView())

    @discord.ui.button(label='Back to Shop Selection', style=discord.ButtonStyle.secondary, emoji='🏠')
    async def back_to_shop_selection(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_shop_selection_embed(), view=ShopSelectionView())

    @discord.ui.button(label='Back to Main Shop', style=discord.ButtonStyle.secondary, emoji='🏠')
    async def back_to_main_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_shop_selection_embed(), view=ShopSelectionView())

def create_sb_survival_embed():
    embed = discord.Embed(
        title="🛡️ South Bronx Trenches - Survival Gear",
        description="**Elite survival gear for the trenches**\n\nSurvive the streets with premium gear!",
        color=0x4169e1,
        timestamp=datetime.now()
    )
    embed.add_field(
        name="🔧 Survival Kit",
        value="• Street Armor - $4.50\n• Elite Protection - $6.00\n• Trenches Gear - $5.50\n• Survival Package - $8.00\n• Ultimate Kit - $10.00",
        inline=False
    )
    embed.add_field(
        name="⚡ Elite Features",
        value="✅ Combat tested\n✅ Street proven\n✅ Elite grade\n✅ Survival ready",
        inline=True
    )
    embed.set_footer(text="ZSupply SB Trenches • Survival guaranteed")
    return embed

class SBSurvivalView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label='Order Survival Gear', style=discord.ButtonStyle.primary, emoji='🛡️')
    async def order_survival(self, interaction: discord.Interaction, button: discord.ui.Button):
        await create_private_order_ticket(interaction, "South Bronx The Trenches", "Survival Gear")

    @discord.ui.button(label='Back to SB Shop', style=discord.ButtonStyle.secondary, emoji='🔥')
    async def back_to_sb_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_south_bronx_shop_embed(), view=SouthBronxShopView())

    @discord.ui.button(label='Back to Shop Selection', style=discord.ButtonStyle.secondary, emoji='🏠')
    async def back_to_shop_selection(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_shop_selection_embed(), view=ShopSelectionView())

    @discord.ui.button(label='Back to Main Shop', style=discord.ButtonStyle.secondary, emoji='🏠')
    async def back_to_main_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_shop_selection_embed(), view=ShopSelectionView())

def create_sb_contact_embed():
    embed = discord.Embed(
        title="📱 South Bronx Trenches - Contact",
        description="**Ready for street business?**",
        color=0x696969,
        timestamp=datetime.now()
    )
    embed.add_field(
        name="📞 Street Contact",
        value="**Contact:** zpofe\n**Response:** Instant\n**Available:** 24/7 Hustle",
        inline=False
    )
    embed.add_field(
        name="💳 Street Payment",
        value="• CashApp\n• Apple Pay\n• Fast & Secure",
        inline=True
    )
    embed.add_field(
        name="🚀 Street Delivery",
        value="• Instant drop\n• Street tested\n• Elite support",
        inline=True
    )
    embed.set_footer(text="ZSupply SB Trenches • Street business only")
    return embed

class SBContactView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label='Back to SB Shop', style=discord.ButtonStyle.secondary, emoji='🔥')
    async def back_to_sb_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_south_bronx_shop_embed(), view=SouthBronxShopView())

    @discord.ui.button(label='Back to Shop Selection', style=discord.ButtonStyle.secondary, emoji='🏠')
    async def back_to_shop_selection(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_shop_selection_embed(), view=ShopSelectionView())

    @discord.ui.button(label='Back to Main Shop', style=discord.ButtonStyle.secondary, emoji='🏠')
    async def back_to_main_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_shop_selection_embed(), view=ShopSelectionView())

def create_sb_order_embed(category):
    embed = discord.Embed(
        title="📋 South Bronx Trenches - Order Info",
        description="**Ready for street business?**",
        color=0xff4500,
        timestamp=datetime.now()
    )
    embed.add_field(
        name="🎮 Street Order",
        value=f"**Game:** South Bronx The Trenches\n**Category:** {category}\n**Status:** Ready for street business",
        inline=False
    )
    embed.add_field(
        name="📱 Street Contact",
        value="**Contact:** zpofe\n**Response:** Instant",
        inline=True
    )
    embed.add_field(
        name="💳 Street Payment",
        value="• **CashApp:** https://cash.app/$EthanCreel1\n• **Apple Pay:** 7656156371\n• **PayPal:** Coming Soon (broken)",
        inline=False
    )
    embed.add_field(
        name="⚡ Street Process",
        value="1️⃣ Hit us up with your order\n2️⃣ Handle payment\n3️⃣ Get your gear instantly\n4️⃣ Receive street support\n5️⃣ Dominate the trenches!",
        inline=False
    )
    embed.set_footer(text="ZSupply SB Trenches • Street business")
    return embed

class SBOrderView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label='Back to SB Shop', style=discord.ButtonStyle.primary, emoji='🔥')
    async def back_to_sb_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_south_bronx_shop_embed(), view=SouthBronxShopView())

    @discord.ui.button(label='Back to Shop Selection', style=discord.ButtonStyle.secondary, emoji='🏠')
    async def back_to_shop_selection(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_shop_selection_embed(), view=ShopSelectionView())

    @discord.ui.button(label='Back to Main Shop', style=discord.ButtonStyle.secondary, emoji='🏠')
    async def back_to_main_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_shop_selection_embed(), view=ShopSelectionView())

# ROBLOX ALTS SHOP LOGIC START
def create_roblox_alts_embed():
    embed = discord.Embed(
        title="🎮 Roblox Alts Shop - Premium Aged Accounts",
        description="**Premium Roblox Accounts - 200+ Days Old**\n\nAll accounts come fully modded for your chosen game!",
        color=0xff6b6b,
        timestamp=datetime.now()
    )
    embed.add_field(
        name="🔥 Account Features",
        value="✅ **200+ Days Old** - Trusted & Aged\n✅ **Fully Modded** - Game-ready setup\n✅ **Premium Quality** - Hand-picked accounts\n✅ **Instant Delivery** - Fast & reliable",
        inline=False
    )
    embed.add_field(
        name="💰 Pricing",
        value="**$3.00 per account**\nIncludes full mod setup for your game!",
        inline=True
    )
    embed.add_field(
        name="🎯 Available Games",
        value="• The Bronx 3 (TB3)\n• Philly Streets 2\n• South Bronx The Trenches",
        inline=True
    )
    embed.add_field(
        name="📦 What's Included",
        value="🔸 200+ day old Roblox account\n🔸 Full game mods installed\n🔸 Account credentials\n🔸 Setup instructions\n🔸 24/7 support",
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

    @discord.ui.button(label='Back to Roblox Shop', style=discord.ButtonStyle.secondary, emoji='🎮')
    async def back_to_roblox_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_roblox_alts_embed(), view=RobloxAltsView())

    @discord.ui.button(label='Back to Shop Selection', style=discord.ButtonStyle.secondary, emoji='🏠')
    async def back_to_main_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_shop_selection_embed(), view=ShopSelectionView())

def create_roblox_account_info_embed(game_name):
    embed = discord.Embed(
        title=f"🎮 {game_name} - Modded Account",
        description=f"**Premium Roblox Account for {game_name}**\n\nReady to dominate with full mods installed!",
        color=0x7289da,
        timestamp=datetime.now()
    )

    embed.add_field(
        name="🔥 Account Specifications",
        value=f"**Age:** 200+ Days Old\n**Game:** {game_name}\n**Status:** Fully Modded\n**Price:** $3.00",
        inline=True
    )

    embed.add_field(
        name="⚡ Mods Included",
        value="🔸 Speed Hack\n🔸 Jump Boost\n🔸 No Clip\n🔸 ESP (Players)\n🔸 Auto-Farm\n🔸 God Mode",
        inline=True
    )

    embed.add_field(
        name="📦 What You Get",
        value="✅ Account Username & Password\n✅ Pre-installed mods\n✅ Setup guide\n✅ Backup email access\n✅ 24/7 customer support",
        inline=False
    )

    embed.add_field(
        name="⚠️ Important Notes",
        value="• Use at your own risk\n• Account age guaranteed 200+ days\n• Mods pre-configured and tested\n• Instant delivery after payment",
        inline=False
    )

    embed.set_footer(text="ZSupply • Premium Quality")
    return embed

class RobloxOrderView(discord.ui.View):
    def __init__(self, game_type):
        super().__init__(timeout=300)
        self.game_type = game_type

    @discord.ui.button(label='Order Now - $3.00', style=discord.ButtonStyle.success, emoji='💳')
    async def order_account(self, interaction: discord.Interaction, button: discord.ui.Button):
        game_names = {
            "TB3": "The Bronx 3",
            "Philly": "Philly Streets 2", 
            "South Bronx": "South Bronx The Trenches"
        }
        game_name = game_names.get(self.game_type, self.game_type)
        await create_private_order_ticket(interaction, f"Roblox Alts - {game_name}", "Modded Account")

    @discord.ui.button(label='Back to Roblox Shop', style=discord.ButtonStyle.secondary, emoji='🎮')
    async def back_to_roblox_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_roblox_alts_embed(), view=RobloxAltsView())

    @discord.ui.button(label='Back to Shop Selection', style=discord.ButtonStyle.secondary, emoji='🏠')
    async def back_to_main_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_shop_selection_embed(), view=ShopSelectionView())

def create_roblox_order_info_embed(game_type):
    game_names = {
        "TB3": "The Bronx 3",
        "Philly": "Philly Streets 2", 
        "South Bronx": "South Bronx The Trenches"
    }

    game_name = game_names.get(game_type, game_type)

    embed = discord.Embed(
        title="📋 Roblox Account Order Information",
        description="**Ready to complete your order?**",
        color=0x00ff00,
        timestamp=datetime.now()
    )

    embed.add_field(
        name="🎮 Order Details",
        value=f"**Product:** Modded Roblox Account\n**Game:** {game_name}\n**Age:** 200+ Days\n**Price:** $3.00",
        inline=False
    )

    embed.add_field(
        name="📞 Contact to Order",
        value="**Contact:** zpofe\n**Response Time:** Instant",
        inline=True
    )

    embed.add_field(
        name="💳 Payment Methods", 
        value="• **CashApp:** https://cash.app/$EthanCreel1\n• **Apple Pay:** 7656156371\n• **PayPal:** Coming Soon (broken)",
        inline=True
    )

    embed.add_field(
        name="⚡ Delivery Process",
        value="1️⃣ Contact us with your order\n2️⃣ Complete payment ($3.00)\n3️⃣ Receive account credentials\n4️⃣ Get setup instructions\n5️⃣ Start dominating the game!",
        inline=False
    )

    embed.add_field(
        name="🛡️ Guarantees",
        value="✅ Account age 200+ days verified\n✅ All mods pre-installed & tested\n✅ Full account access provided\n✅ 24/7 customer support",
        inline=False
    )

    embed.set_footer(text="ZSupply • Contact us to complete your order!")
    return embed

class RobloxContactView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label='Back to Roblox Shop', style=discord.ButtonStyle.primary, emoji='🎮')
    async def back_to_roblox_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_roblox_alts_embed(), view=RobloxAltsView())

    @discord.ui.button(label='Back to Shop Selection', style=discord.ButtonStyle.secondary, emoji='🏠')
    async def back_to_shop_selection(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_shop_selection_embed(), view=ShopSelectionView())

    @discord.ui.button(label='Back to Main Shop', style=discord.ButtonStyle.secondary, emoji='🏠')
    async def back_to_main_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_shop_selection_embed(), view=ShopSelectionView())

# New embed creation functions
def create_support_embed():
    embed = discord.Embed(
        title="🎫 ZSells Support Center",
        description="Need help? Our support team is here to assist you 24/7!\n\n**What we can help with:**\n• Order issues\n• Payment problems\n• Product questions\n• Technical support\n• General inquiries",
        color=0x00ff00
    )
    embed.add_field(
        name="📝 How it works",
        value="1. Click the **Create Ticket** button below\n2. Describe your issue in detail\n3. Our staff will respond promptly\n4. Get the help you need!",
        inline=False
    )
    embed.add_field(
        name="⏱️ Response Time",
        value="• Average: 15 minutes\n• Maximum: 2 hours\n• 24/7 availability",
        inline=True
    )
    embed.add_field(
        name="🎯 Support Quality",
        value="• Expert staff\n• Quick resolutions\n• 99% satisfaction rate",
        inline=True
    )
    embed.set_footer(text="ZSells Support • Click the button below to get started")
    return embed

def create_gang_embed():
    embed = discord.Embed(
        title="🔫 STK SERVER RULES",
        description="**Elite Gang Recruitment Open!**\n\nSTK Gang is recruiting the most skilled and dedicated members. Are you ready to join the elite?",
        color=0x7289da
    )
    embed.add_field(
        name="📋 STK Server Rules",
        value="**1.** No Leaking - Don't screenshot, record, or share anything from this server outside of it. What happens here stays here.\n\n**2.** Keep VC Chill - No yelling, trolling, or soundboards unless everyone's with it. Don't ruin the vibe.\n\n**3.** Use the Right Channels - Trade in trade channels. Talk in general. Don't spam.\n\n**4.** No Weird Behavior - Racism, homophobia, harassment — you're out instantly. No second chances.\n\n**5.** No Fakes - Don't act like staff or fake claim STK. Keep it real.",
        inline=False
    )
    embed.add_field(
        name="📋 STK Server Rules (Continued)",
        value="**6.** No Scams or Exploits - Scamming = ban. Exploiting in-game = ban. Don't mess it up for everyone.\n\n**7.** Follow Discord TOS - Don't bring dumb attention. If you're too young or breaking TOS, you're gone.\n\n**8.** Stay Active - If you're inactive too long without saying something, you might be removed.\n\n**9.** Respect Mods & Members - If a mod tells you to chill, just chill. Don't start problems with others for no reason either.\n\n**10.** Must wear: SHIRT- Green Varsity, PANTS- Green Ripped Jeans",
        inline=False
    )
    embed.set_footer(text="STK Gang • Elite Members Only")
    return embed

def create_tos_embed():
    embed = discord.Embed(
        title="📋 Terms of Service",
        description="**ZSells Terms of Service - Please Read Carefully**",
        color=0xff9900
    )
    embed.add_field(
        name="🔒 Account & Payment",
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
    embed.set_footer(text="ZSells ToS • Last updated: 2024 • By purchasing, you agree to these terms")
    return embed

def create_rules_embed():
    embed = discord.Embed(
        title="🔫 STK SERVER RULES",
        description="**STK Gang Server Rules - Follow for Elite Status**",
        color=0xff0000
    )
    embed.add_field(
        name="📋 STK Server Rules",
        value="**1.** No Leaking - Don't screenshot, record, or share anything from this server outside of it. What happens here stays here.\n\n**2.** Keep VC Chill - No yelling, trolling, or soundboards unless everyone's with it. Don't ruin the vibe.\n\n**3.** Use the Right Channels - Trade in trade channels. Talk in general. Don't spam.\n\n**4.** No Weird Behavior - Racism, homophobia, harassment — you're out instantly. No second chances.\n\n**5.** No Fakes - Don't act like staff or fake claim STK. Keep it real.",
        inline=False
    )
    embed.add_field(
        name="📋 STK Server Rules (Continued)",
        value="**6.** No Scams or Exploits - Scamming = ban. Exploiting in-game = ban. Don't mess it up for everyone.\n\n**7.** Follow Discord TOS - Don't bring dumb attention. If you're too young or breaking TOS, you're gone.\n\n**8.** Stay Active - If you're inactive too long without saying something, you might be removed.\n\n**9.** Respect Mods & Members - If a mod tells you to chill, just chill. Don't start problems with others for no reason either.\n\n**10.** Must wear: SHIRT- Green Varsity, PANTS- Green Ripped Jeans",
        inline=False
    )
    embed.set_footer(text="STK Gang • Elite Members Only • Staff have final say")
    return embed

def create_news_embed():
    embed = discord.Embed(
        title=NEWS_DATA["title"],
        description=NEWS_DATA["content"],
        color=0x1e90ff,
        timestamp=datetime.fromisoformat(NEWS_DATA["last_updated"]) if NEWS_DATA["last_updated"] else None
    )
    embed.set_footer(text="ZSells News • Stay updated with latest announcements")
    return embed

def create_welcome_embed():
    embed = discord.Embed(
        title="👋 Welcome to ZSells Community!",
        description="**Welcome to our amazing community!**\n\nWe're excited to have you here. Get started by exploring our channels and services!",
        color=0x00ff7f
    )
    embed.add_field(
        name="🎯 Getting Started",
        value="• Read our **rules** and **guidelines**\n• Check out our **shop** for premium items\n• Join our **STK Gang** for exclusive perks\n• Create a **support ticket** if you need help",
        inline=False
    )
    embed.add_field(
        name="💎 Community Benefits",
        value="✅ Premium services\n✅ 24/7 support\n✅ Exclusive deals\n✅ Elite gang access\n✅ Trusted community",
        inline=True
    )
    embed.add_field(
        name="🚀 Quick Links",
        value="• **Shop** - Premium products\n• **Support** - Get help instantly\n• **STK Gang** - Join the elite\n• **Rules** - Community guidelines",
        inline=True
    )
    embed.set_footer(text="ZSells Community • Welcome to the family!")
    return embed

def create_reminder_embed():
    embed = discord.Embed(
        title="🛒 Shop Reminder - ZSells Premium Store!",
        description="**Don't forget to visit our shop channel!**\n\n💰 Amazing deals and premium products are waiting for you in the shop channel!",
        color=0xffd700
    )
    embed.add_field(
        name="🛍️ Available in Shop Channel",
        value="• **Premium Weapons** - Full collection with package deals\n• **Money & Bank Services** - Fast and secure\n• **Luxury Watches** - $1 each, premium quality\n• **Special Packages** - Save more with bundles",
        inline=False
    )
    embed.add_field(
        name="💎 Why Shop With Us?",
        value="✅ Instant delivery guaranteed\n✅ Lowest prices available\n✅ 24/7 customer support\n✅ Secure payment methods\n✅ Trusted by thousands",
        inline=True
    )
    embed.add_field(
        name="🚀 How to Shop",
        value="• Go to the **shop channel**\n• Browse our premium items\n• Use interactive buttons\n• Contact us to complete order",
        inline=True
    )
    embed.add_field(
        name="💳 Quick Purchase Info",
        value="**Payment:** CashApp • Apple Pay\n**Contact:** zpofe\n**Delivery:** Instant",
        inline=False
    )
    embed.set_footer(text="ZSells Shop Reminder • Visit shop channel now for best deals!")
    return embed

# Original embed functions (keeping existing functionality)
def create_main_shop_embed():
    embed = discord.Embed(
        title="🛒 Z Supply - Interactive Shop",
        description="Welcome to Z Supply! Click the buttons below to browse our premium collection:",
        color=0x2F3136
    )
    embed.add_field(
        name="🔫 Weapons",
        value="Premium weapon collection with package options",
        inline=True
    )
    embed.add_field(
        name="💰 Money",
        value="Money and bank packages for your account",
        inline=True
    )
    embed.add_field(
        name="⌚ Watches",
        value="Luxury watch collection - $1 each",
        inline=True
    )
    embed.set_footer(text="Z Supply | Click buttons to navigate")
    return embed

def create_weapons_embed():
    embed = discord.Embed(
        title="🔫 Weapon Selection",
        description="Choose from our premium weapon collection. All weapons are FREE - you only pay for the package!",
        color=0xFF6B6B
    )
    embed.add_field(
        name="📦 Package Options",
        value="🔒 Safe Package - $3.00\n🎒 Bag Package - $2.00\n📦 Trunk Package - $1.00",
        inline=False
    )
    embed.set_footer(text="Select weapons from the dropdown below")
    return embed

def create_weapon_package_embed(weapon):
    embed = discord.Embed(
        title=f"🔫 {weapon}",
        description=f"Selected weapon: **{weapon}**\nChoose your package:",
        color=0x4ECDC4
    )
    embed.add_field(
        name="Package Options",
        value="🔒 Safe Package - $3.00\n🎒 Bag Package - $2.00\n📦 Trunk Package - $1.00",
        inline=False
    )
    embed.set_footer(text="Click a package button below")
    return embed

def create_multi_weapon_package_embed(weapons):
    embed = discord.Embed(
        title=f"Selected Weapons ({len(weapons)})",
        description=f"You've selected **{len(weapons)} weapons**. Choose your package option:",
        color=0x4ECDC4
    )

    weapons_list = "\n".join([f"🔫 {weapon}" for weapon in weapons])
    embed.add_field(
        name="Selected Weapons",
        value=weapons_list if len(weapons_list) < 1000 else f"{weapons_list[:900]}...\n+{len(weapons)-weapons_list[:900].count('🔫')} more",
        inline=False
    )

    embed.add_field(
        name="Package Options (all weapons included)",
        value="🔒 Safe Package - $3.00\n🎒 Bag Package - $2.00\n📦 Trunk Package - $1.00",
        inline=False
    )

    embed.set_footer(text="One package price covers all selected weapons")
    return embed

def create_money_embed():
    embed = discord.Embed(
        title="💰 Money Shop",
        description="Choose your money package:",
        color=0xF7DC6F
    )
    embed.add_field(
        name="💵 Regular Options - $1.00 each",
        value="💰 Max Money 990k\n🏦 Max Bank 990k",
        inline=False
    )
    embed.add_field(
        name="💎 Gamepass Options - $2.00 each",
        value="💎 Max Money 1.6M (Extra Money Pass)\n💳 Max Bank 1.6M (Extra Bank Pass)",
        inline=False
    )
    embed.set_footer(text="Click a button to select your package")
    return embed

def create_watches_embed():
    embed = discord.Embed(
        title="⌚ Luxury Watch Collection",
        description="Premium watches - All $1.00 each. Select from the dropdown below:",
        color=0x85C1E9
    )
    embed.add_field(
        name="💰 Pricing",
        value="All watches: **$1.00** each\nPremium luxury collection",
        inline=False
    )
    embed.set_footer(text="Select a watch from the dropdown below")
    return embed

def create_contact_embed():
    embed = discord.Embed(
        title="📞 Contact Information",
        description="Ready to place an order? Here's how to contact us:",
        color=0xFDCB6E
    )
    embed.add_field(
        name="📝 Order Process",
        value="1. Browse our products using the buttons\n2. Select your items\n3. Contact Z Supply\n4. Complete payment\n5. Receive your items!",
        inline=False
    )
    embed.add_field(
        name="💳 Payment Methods",
        value="CashApp • Apple Pay",
        inline=True
    )
    embed.add_field(
        name="⏱️ Delivery Time",
        value="• Instant delivery\n• 24/7 support\n• Money back guarantee",
        inline=True
    )
    embed.add_field(
        name="📞 Contact Z Supply",
        value="Contact: zpofe",
        inline=False
    )
    embed.set_footer(text="Contact us to complete your order!")
    return embed

def create_order_info_embed(weapons, package_type):
    pkg_info = PACKAGES[package_type]
    total_price = pkg_info['price']

    embed = discord.Embed(
        title="📋 Order Information",
        description="Order details and contact information:",
        color=0x95E1D3
    )

    if len(weapons) == 1:
        embed.add_field(name="Weapon", value=f"🔫 {weapons[0]}", inline=True)
    else:
        weapons_list = "\n".join([f"🔫 {weapon}" for weapon in weapons])
        embed.add_field(
            name=f"Weapons ({len(weapons)})",
            value=weapons_list if len(weapons_list) < 1000 else f"{weapons_list[:900]}...\n+{len(weapons)-weapons_list[:900].count('🔫')} more",
            inline=False
        )

    embed.add_field(name="Package", value=f"{pkg_info['emoji']} {pkg_info['name']}", inline=True)
    embed.add_field(name="Total", value=f"**${total_price:.2f}**", inline=True)

    embed.add_field(
        name="📞 Contact to Order",
        value="Contact: zpofe",
        inline=False
    )
    embed.add_field(
        name="💳 Payment Methods",
        value="CashApp • Apple Pay",
        inline=False
    )

    embed.set_footer(text="Contact us to complete your order!")
    return embed

def create_money_info_embed(item, price):
    embed = discord.Embed(
        title="📋 Order Information",
        description="Order details and contact information:",
        color=0x95E1D3
    )

    embed.add_field(name="Item", value=f"💰 {item}", inline=True)
    embed.add_field(name="Total", value=f"**${price:.2f}**", inline=True)

    embed.add_field(
        name="📞 Contact to Order",
        value="Contact: zpofe",
        inline=False
    )
    embed.add_field(
        name="💳 Payment Methods",
        value="CashApp • Apple Pay",
        inline=False
    )

    embed.set_footer(text="Contact us to complete your order!")
    return embed

def create_watch_info_embed(watch):
    embed = discord.Embed(
        title="📋 Order Information",
        description="Order details and contact information:",
        color=0x95E1D3
    )

    embed.add_field(name="Watch", value=f"⌚ {watch}", inline=True)
    embed.add_field(name="Total", value="**$1.00**", inline=True)

    embed.add_field(
        name="📞 Contact to Order",
        value="Contact: zpofe",
        inline=False
    )
    embed.add_field(
        name="💳 Payment Methods",
        value="CashApp • Apple Pay",
        inline=False
    )

    embed.set_footer(text="Contact us to complete your order!")
    return embed

def create_multi_watch_info_embed(watches):
    embed = discord.Embed(
        title="📋 Order Information",
        description="Order details and contact information:",
        color=0x95E1D3
    )

    total_price = len(watches) * 1.00
    watches_list = "\n".join([f"⌚ {watch}" for watch in watches])

    embed.add_field(
        name=f"Watches ({len(watches)})",
        value=watches_list if len(watches_list) < 1000 else f"{watches_list[:900]}...\n+{len(watches)-watches_list[:900].count('⌚')} more",
        inline=False
    )
    embed.add_field(name="Total", value=f"**${total_price:.2f}**", inline=True)

    embed.add_field(
        name="📞 Contact to Order",
        value="Contact: zpofe",
        inline=False
    )
    embed.add_field(
        name="💳 Payment Methods",
        value="CashApp • Apple Pay",
        inline=False
    )

    embed.set_footer(text="Contact us to complete your order!")
    return embed

# Verification system
VERIFICATION_DATA = {}

class VerificationModal(discord.ui.Modal, title='Server Verification'):
    def __init__(self):
        super().__init__()

    verification_code = discord.ui.TextInput(
        label='Verification Code',
        placeholder='Enter the verification code shown in the embed...',
        style=discord.TextStyle.short,
        max_length=10,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        entered_code = self.verification_code.value.upper()

        if user_id in VERIFICATION_DATA and VERIFICATION_DATA[user_id]['code'] == entered_code:
            # User entered correct code
            verified_role = discord.utils.get(interaction.guild.roles, name="Verified")
            if not verified_role:
                # Create verified role if it doesn't exist
                verified_role = await interaction.guild.create_role(
                    name="Verified",
                    color=discord.Color.green(),
                    reason="Auto-created verification role"
                )

            try:
                await interaction.user.add_roles(verified_role, reason="User verified")
                del VERIFICATION_DATA[user_id]  # Remove verification data

                embed = discord.Embed(
                    title="✅ Verification Successful!",
                    description=f"Welcome to {interaction.guild.name}! You have been verified and can now access all channels.",
                    color=0x00ff00
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)

            except discord.Forbidden:
                await interaction.response.send_message("❌ Bot lacks permission to assign roles.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Invalid verification code! Please try again.", ephemeral=True)

class VerificationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='Verify', style=discord.ButtonStyle.success, emoji='✅', custom_id='verify_user')
    async def verify_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id

        # Check if user is already verified
        verified_role = discord.utils.get(interaction.guild.roles, name="Verified")
        if verified_role and verified_role in interaction.user.roles:
            await interaction.response.send_message("✅ You are already verified!", ephemeral=True)
            return

        # Generate random verification code
        import random
        import string
        verification_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

        # Store verification data
        VERIFICATION_DATA[user_id] = {
            'code': verification_code,
            'timestamp': datetime.now().isoformat()
        }

        # Create verification embed
        embed = discord.Embed(
            title="🔐 Account Verification Required",
            description="Please complete the verification process to access the server.",
            color=0xffa500
        )
        embed.add_field(
            name="📝 Verification Code",
            value=f"```{verification_code}```",
            inline=False
        )
        embed.add_field(
            name="📋 Instructions",
            value="1. Copy the verification code above\n2. Click the **Enter Code** button below\n3. Paste the code in the modal\n4. Submit to complete verification",
            inline=False
        )
        embed.set_footer(text="Code expires in 10 minutes • ZSells Verification System")

        view = VerificationModalView()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class VerificationModalView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=600)

    @discord.ui.button(label='Enter Code', style=discord.ButtonStyle.primary, emoji='🔑')
    async def enter_code(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = VerificationModal()
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
    bot.add_view(VerificationView())
    bot.add_view(OrderTicketControlView(None))

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

# Run the bot
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
if TOKEN:
    bot.run(TOKEN)
else:
    print("❌ DISCORD_BOT_TOKEN not found in environment variables")
    print("Please add your Discord bot token to the environment variables.")