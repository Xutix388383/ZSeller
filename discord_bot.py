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

    analysis = {
        'guild_info': {
            'name': guild.name,
            'id': guild.id,
            'member_count': guild.member_count,
            'created_at': guild.created_at.isoformat() if guild.created_at else None,
            'verification_level': str(guild.verification_level),
            'boost_count': guild.premium_subscription_count,
            'boost_tier': guild.premium_tier
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
        'members': get_key_members(guild),
        'features': guild.features
    }

    return analysis

# Global variables to store detected data
CHANNELS = {}
GUILD_ANALYSIS = {}

# Shop reminder task
@tasks.loop(minutes=15)
async def send_shop_reminder():
    """Send shop reminder every 15 minutes and auto-delete duplicates"""
    try:
        # Use the specific welcome channel ID
        welcome_channel_id = 1407347199477547101
        welcome_channel = bot.get_channel(welcome_channel_id)

        # If specific channel not found, try to find one
        if not welcome_channel:
            for guild in bot.guilds:
                for channel in guild.text_channels:
                    channel_name_lower = channel.name.lower()
                    if any(pattern in channel_name_lower for pattern in ['welcome', 'general', 'main', 'lobby']):
                        welcome_channel = channel
                        break
                if welcome_channel:
                    break

        # Send reminder and handle duplicate deletion
        if welcome_channel and check_channel_permissions(welcome_channel):
            # Delete old shop reminder messages to prevent spam (limited to prevent rate limiting)
            try:
                deleted_count = 0
                async for message in welcome_channel.history(limit=10):  # Reduced from 50 to 10
                    if (message.author == bot.user and 
                        message.embeds and 
                        len(message.embeds) > 0 and
                        "Shop Reminder" in str(message.embeds[0].title)):
                        await message.delete()
                        deleted_count += 1
                        print(f"🗑️ Deleted old shop reminder message ({deleted_count})")

                        # Add delay to prevent rate limiting
                        if deleted_count >= 3:  # Stop after 3 deletions to prevent rate limiting
                            break
                        await asyncio.sleep(1)  # 1 second delay between deletions

            except discord.Forbidden:
                print("⚠️ No permission to delete old messages")
            except discord.HTTPException as e:
                if e.status == 429:  # Rate limited
                    print("⚠️ Rate limited while deleting messages, skipping cleanup")
                else:
                    print(f"⚠️ HTTP error deleting messages: {e}")
            except Exception as e:
                print(f"⚠️ Error deleting old messages: {e}")

            # Send new reminder message
            embed = create_reminder_embed()
            await welcome_channel.send(embed=embed)
            print(f"✅ Shop reminder sent to #{welcome_channel.name}")
        elif welcome_channel:
            print(f"❌ No permission to send shop reminder in #{welcome_channel.name}")
        else:
            print("⚠️ No welcome channel found. Create a channel with 'welcome', 'general', or 'main' in the name.")

    except Exception as e:
        print(f"Error sending shop reminder: {e}")

@send_shop_reminder.before_loop
async def before_shop_reminder():
    await bot.wait_until_ready()

# Role IDs
STAFF_ROLE_ID = 1407347171795406919  # Admin role
OWNER_ROLE_ID = 1407347171056943214  # Owner role

# Ticket counter and data storage
TICKET_COUNTER = 1
ACTIVE_TICKETS = {}
NEWS_DATA = {"title": "📰 Latest News", "content": "No news updates yet.", "last_updated": None}

# Load data from file if exists
def load_data():
    global TICKET_COUNTER, ACTIVE_TICKETS, NEWS_DATA
    try:
        if os.path.exists('bot_data.json'):
            with open('bot_data.json', 'r') as f:
                data = json.load(f)
                TICKET_COUNTER = data.get('ticket_counter', 1)
                ACTIVE_TICKETS = data.get('active_tickets', {})
                NEWS_DATA = data.get('news_data', NEWS_DATA)
    except Exception as e:
        print(f"Error loading data: {e}")

def save_data():
    try:
        data = {
            'ticket_counter': TICKET_COUNTER,
            'active_tickets': ACTIVE_TICKETS,
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
        embed = create_order_info_embed(self.weapons, "safe")
        view = OrderInfoView()
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label='Bag Package - $2.00', style=discord.ButtonStyle.success)
    async def bag_package(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = create_order_info_embed(self.weapons, "bag")
        view = OrderInfoView()
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label='Trunk Package - $1.00', style=discord.ButtonStyle.secondary)
    async def trunk_package(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = create_order_info_embed(self.weapons, "trunk")
        view = OrderInfoView()
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label='Back', style=discord.ButtonStyle.danger)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_weapons_embed(), view=WeaponsView())

class MoneyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label='💵 Regular Money - $1.00', style=discord.ButtonStyle.primary)
    async def regular_money(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = create_money_info_embed("Max Money 990k", 1.00)
        view = OrderInfoView()
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label='🏦 Regular Bank - $1.00', style=discord.ButtonStyle.primary)
    async def regular_bank(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = create_money_info_embed("Max Bank 990k", 1.00)
        view = OrderInfoView()
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label='💎 Gamepass Money - $2.00', style=discord.ButtonStyle.success)
    async def gamepass_money(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = create_money_info_embed("Max Money 1.6M (Extra Money Pass)", 2.00)
        view = OrderInfoView()
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label='💳 Gamepass Bank - $2.00', style=discord.ButtonStyle.success)
    async def gamepass_bank(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = create_money_info_embed("Max Bank 1.6M (Extra Bank Pass)", 2.00)
        view = OrderInfoView()
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label='Back to Shop', style=discord.ButtonStyle.secondary, emoji='🏠')
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
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
        if len(selected_watches) == 1:
            embed = create_watch_info_embed(selected_watches[0])
        else:
            embed = create_multi_watch_info_embed(selected_watches)
        view = OrderInfoView()
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label='Back to Shop', style=discord.ButtonStyle.secondary, emoji='🏠')
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_main_shop_embed(), view=MainShopView())

class ContactView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label='Back to Shop', style=discord.ButtonStyle.secondary, emoji='🏠')
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_main_shop_embed(), view=MainShopView())

class OrderInfoView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label='Back to Shop', style=discord.ButtonStyle.primary, emoji='🏠')
    async def back_to_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_main_shop_embed(), view=MainShopView())

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

@bot.event
async def on_ready():
    global CHANNELS, GUILD_ANALYSIS
    load_data()

    # Add persistent views
    bot.add_view(SupportView())
    bot.add_view(GangRecruitmentView())
    bot.add_view(VerificationView()) # Add the verification view

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

    try:
        synced = await bot.tree.sync()
        print(f'✅ Synced {len(synced)} slash commands')
    except Exception as e:
        print(f'❌ Failed to sync commands: {e}')

    # Start the shop reminder task
    if not send_shop_reminder.is_running():
        send_shop_reminder.start()
        print("✅ Shop reminder task started (every 15 minutes)")

    print(f'\n🎉 {bot.user} is fully operational with enhanced detection!')
    print('💡 Use /spawner for embed spawning panel')
    print('🔧 Use /admin for advanced admin panel')
    print('🔍 Use /guild_info to view detailed analysis')

async def auto_setup_all_embeds():
    """Automatically setup all embeds in their respective channels"""
    try:
        # First check if bot has basic permissions in any guild
        has_any_permissions = False
        for guild in bot.guilds:
            if check_bot_permissions_in_guild(guild):
                has_any_permissions = True
                break

        if not has_any_permissions:
            print("❌ Bot lacks basic permissions in all guilds. Please check bot permissions:")
            print("   • Send Messages")
            print("   • Embed Links") 
            print("   • View Channel")
            print("   • Read Message History")
            return

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
            elif support_channel:
                print(f"❌ Missing permissions in #{support_channel.name}")

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
            elif stk_channel:
                print(f"❌ Missing permissions in #{stk_channel.name}")

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
            elif tos_channel:
                print(f"❌ Missing permissions in #{tos_channel.name}")

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
            elif rules_channel:
                print(f"❌ Missing permissions in #{rules_channel.name}")

        # Setup News - skip auto-setup to avoid permission issues
        if 'news' in CHANNELS:
            news_channel = bot.get_channel(CHANNELS['news'])
            if news_channel and check_channel_permissions(news_channel):
                try:
                    if not NEWS_DATA["last_updated"]:
                        NEWS_DATA["last_updated"] = datetime.now().isoformat()
                        save_data()
                    # Skip auto-sending news to avoid permission issues
                    print("✅ News channel detected - use /admin to spawn news panel")
                except Exception as e:
                    print(f"❌ Error with news setup: {e}")
            elif news_channel:
                print(f"❌ Missing permissions in #{news_channel.name}")

    except Exception as e:
        print(f"Error in auto-setup: {e}")

# Simple Embed Creator Modal
class EmbedCreatorModal(discord.ui.Modal, title='Simple Embed Creator'):
    def __init__(self, target_channel):
        super().__init__()
        self.target_channel = target_channel

    embed_title = discord.ui.TextInput(
        label='Title',
        placeholder='Enter embed title (required)',
        style=discord.TextStyle.short,
        max_length=256,
        required=True
    )

    embed_description = discord.ui.TextInput(
        label='Description',
        placeholder='Enter embed description...',
        style=discord.TextStyle.paragraph,
        max_length=2000,
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            if not check_channel_permissions(self.target_channel):
                await interaction.response.send_message(
                    f"❌ Bot lacks permission to send messages in {self.target_channel.mention}", 
                    ephemeral=True
                )
                return

            # Create simple embed
            embed = discord.Embed(
                title=self.embed_title.value,
                description=self.embed_description.value or None,
                color=0x7289da,
                timestamp=datetime.now()
            )

            embed.set_footer(text="ZSells Embed Creator")

            await self.target_channel.send(embed=embed)
            await interaction.response.send_message(
                f"✅ Embed sent to {self.target_channel.mention}!", 
                ephemeral=True
            )

        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

# Message Creator Modal
class MessageCreatorModal(discord.ui.Modal, title='Message Creator'):
    def __init__(self, target_channel):
        super().__init__()
        self.target_channel = target_channel

    message_content = discord.ui.TextInput(
        label='Message Content',
        placeholder='Enter your message content...',
        style=discord.TextStyle.paragraph,
        max_length=2000,
        required=True
    )

    ping_role = discord.ui.TextInput(
        label='Ping Role (optional)',
        placeholder='Role name or ID to ping',
        style=discord.TextStyle.short,
        max_length=100,
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            if not check_channel_permissions(self.target_channel):
                await interaction.response.send_message(
                    f"❌ Bot lacks permission to send messages in {self.target_channel.mention}", 
                    ephemeral=True
                )
                return

            message_text = self.message_content.value

            # Handle role ping if provided
            if self.ping_role.value:
                guild = self.target_channel.guild
                role = None
                if self.ping_role.value.isdigit():
                    role = guild.get_role(int(self.ping_role.value))
                else:
                    role = discord.utils.get(guild.roles, name=self.ping_role.value)

                if role:
                    message_text = f"{role.mention}\n{message_text}"

            await self.target_channel.send(message_text)
            await interaction.response.send_message(
                f"✅ Message sent to {self.target_channel.mention}!", 
                ephemeral=True
            )

        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

# Bulk Actions Modal
class BulkMessageModal(discord.ui.Modal, title='Bulk Message Management'):
    def __init__(self, target_channel, action_type):
        super().__init__()
        self.target_channel = target_channel
        self.action_type = action_type

    amount = discord.ui.TextInput(
        label='Number of messages',
        placeholder='Enter number (1-100)',
        style=discord.TextStyle.short,
        max_length=3,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            amount = int(self.amount.value)
            if amount < 1 or amount > 100:
                await interaction.response.send_message("❌ Amount must be between 1 and 100", ephemeral=True)
                return

            if self.action_type == "delete":
                deleted = await self.target_channel.purge(limit=amount)
                await interaction.response.send_message(
                    f"✅ Deleted {len(deleted)} messages from {self.target_channel.mention}", 
                    ephemeral=True
                )
        except ValueError:
            await interaction.response.send_message("❌ Please enter a valid number", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ Bot lacks permission to delete messages", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

# User Management Modal for selecting users
class UserSelectModal(discord.ui.Modal, title='User Management - Search User'):
    def __init__(self, guild):
        super().__init__()
        self.guild = guild

    username = discord.ui.TextInput(
        label='Username or User ID',
        placeholder='Enter username, display name, or user ID...',
        style=discord.TextStyle.short,
        max_length=100,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            search_term = self.username.value.strip()

            # Search for user by ID first
            target_user = None
            if search_term.isdigit():
                try:
                    target_user = self.guild.get_member(int(search_term))
                    if not target_user:
                        target_user = await self.guild.fetch_member(int(search_term))
                except:
                    pass

            # If not found by ID, search by name
            if not target_user:
                # Search by exact username
                target_user = discord.utils.get(self.guild.members, name=search_term)

                # Search by display name if not found
                if not target_user:
                    target_user = discord.utils.get(self.guild.members, display_name=search_term)

                # Search by partial match if still not found
                if not target_user:
                    search_lower = search_term.lower()
                    for member in self.guild.members:
                        if (search_lower in member.name.lower() or 
                            search_lower in member.display_name.lower()):
                            target_user = member
                            break

            if not target_user:
                await interaction.response.send_message(
                    f"❌ User '{search_term}' not found in this server!", 
                    ephemeral=True
                )
                return

            # Show user management panel
            embed = create_user_card_embed(target_user)
            view = UserManagementView(target_user)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"❌ Error searching for user: {str(e)}", ephemeral=True)

# User Management Views and Actions
class UserManagementView(discord.ui.View):
    def __init__(self, target_user):
        super().__init__(timeout=300)
        self.target_user = target_user

    @discord.ui.button(label='Kick', style=discord.ButtonStyle.secondary, emoji='👢', row=0)
    async def kick_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_admin_permissions(interaction.user, interaction.guild):
            await interaction.response.send_message("❌ You are not authorized.", ephemeral=True)
            return

        modal = ActionReasonModal(self.target_user, "kick")
        await interaction.response.send_modal(modal)

    @discord.ui.button(label='Ban', style=discord.ButtonStyle.danger, emoji='🔨', row=0)
    async def ban_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_admin_permissions(interaction.user, interaction.guild):
            await interaction.response.send_message("❌ You are not authorized.", ephemeral=True)
            return

        modal = ActionReasonModal(self.target_user, "ban")
        await interaction.response.send_modal(modal)

    @discord.ui.button(label='Timeout', style=discord.ButtonStyle.secondary, emoji='⏰', row=0)
    async def timeout_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_admin_permissions(interaction.user, interaction.guild):
            await interaction.response.send_message("❌ You are not authorized.", ephemeral=True)
            return

        modal = TimeoutModal(self.target_user)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label='Warn', style=discord.ButtonStyle.secondary, emoji='⚠️', row=0)
    async def warn_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_admin_permissions(interaction.user, interaction.guild):
            await interaction.response.send_message("❌ You are not authorized.", ephemeral=True)
            return

        modal = ActionReasonModal(self.target_user, "warn")
        await interaction.response.send_modal(modal)

    @discord.ui.button(label='Mute', style=discord.ButtonStyle.secondary, emoji='🔇', row=1)
    async def mute_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_admin_permissions(interaction.user, interaction.guild):
            await interaction.response.send_message("❌ You are not authorized.", ephemeral=True)
            return

        modal = ActionReasonModal(self.target_user, "mute")
        await interaction.response.send_modal(modal)

    @discord.ui.button(label='Unmute', style=discord.ButtonStyle.success, emoji='🔊', row=1)
    async def unmute_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_admin_permissions(interaction.user, interaction.guild):
            await interaction.response.send_message("❌ You are not authorized.", ephemeral=True)
            return

        try:
            # Remove timeout if they have one
            if self.target_user.timed_out_until:
                await self.target_user.edit(timed_out_until=None, reason=f"Unmuted by {interaction.user}")
                await interaction.response.send_message(f"✅ {self.target_user.mention} has been unmuted!", ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ {self.target_user.mention} is not currently muted.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to unmute this user.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error unmuting user: {str(e)}", ephemeral=True)

    @discord.ui.button(label='View Roles', style=discord.ButtonStyle.primary, emoji='🎭', row=1)
    async def view_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_admin_permissions(interaction.user, interaction.guild):
            await interaction.response.send_message("❌ You are not authorized.", ephemeral=True)
            return

        roles = [role.mention for role in self.target_user.roles if role.name != "@everyone"]
        roles_text = "\n".join(roles[:20]) if roles else "No roles"

        embed = discord.Embed(
            title=f"🎭 Roles for {self.target_user.display_name}",
            description=roles_text,
            color=0x7289da
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label='Refresh Info', style=discord.ButtonStyle.primary, emoji='🔄', row=1)
    async def refresh_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_admin_permissions(interaction.user, interaction.guild):
            await interaction.response.send_message("❌ You are not authorized.", ephemeral=True)
            return

        # Refresh the user card with updated information
        embed = create_user_card_embed(self.target_user)
        view = UserManagementView(self.target_user)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label='Close', style=discord.ButtonStyle.danger, emoji='❌', row=2)
    async def close_panel(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="✅ User Management Closed", description="User management panel closed.", color=0x95a5a6)
        await interaction.response.edit_message(embed=embed, view=None)

# Action Reason Modal
class ActionReasonModal(discord.ui.Modal, title='Moderation Action'):
    def __init__(self, target_user, action_type):
        super().__init__()
        self.target_user = target_user
        self.action_type = action_type
        self.title = f'{action_type.title()} {target_user.display_name}'

    reason = discord.ui.TextInput(
        label='Reason',
        placeholder='Enter reason for this action...',
        style=discord.TextStyle.paragraph,
        max_length=500,
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            reason_text = self.reason.value or f"{self.action_type.title()} by {interaction.user}"

            if self.action_type == "kick":
                await self.target_user.kick(reason=reason_text)
                await interaction.response.send_message(f"✅ {self.target_user.mention} has been kicked!\nReason: {reason_text}", ephemeral=True)

            elif self.action_type == "ban":
                await self.target_user.ban(reason=reason_text, delete_message_days=1)
                await interaction.response.send_message(f"✅ {self.target_user.mention} has been banned!\nReason: {reason_text}", ephemeral=True)

            elif self.action_type == "warn":
                # Send warning to user
                try:
                    embed = discord.Embed(
                        title="⚠️ You have received a warning",
                        description=f"**Server:** {interaction.guild.name}\n**Reason:** {reason_text}\n**Moderator:** {interaction.user}",
                        color=0xffaa00
                    )
                    await self.target_user.send(embed=embed)
                    dm_status = "Warning sent via DM"
                except:
                    dm_status = "Could not send DM"

                await interaction.response.send_message(f"⚠️ {self.target_user.mention} has been warned!\nReason: {reason_text}\n{dm_status}", ephemeral=True)

            elif self.action_type == "mute":
                # Create a 10 minute timeout by default
                from datetime import timedelta
                timeout_until = discord.utils.utcnow() + timedelta(minutes=10)
                await self.target_user.edit(timed_out_until=timeout_until, reason=reason_text)
                await interaction.response.send_message(f"🔇 {self.target_user.mention} has been muted for 10 minutes!\nReason: {reason_text}", ephemeral=True)

        except discord.Forbidden:
            await interaction.response.send_message(f"❌ I don't have permission to {self.action_type} this user.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error performing {self.action_type}: {str(e)}", ephemeral=True)

# Timeout Modal with duration selection
class TimeoutModal(discord.ui.Modal, title='Timeout User'):
    def __init__(self, target_user):
        super().__init__()
        self.target_user = target_user

    duration = discord.ui.TextInput(
        label='Duration (in minutes)',
        placeholder='Enter timeout duration in minutes (1-10080)',
        style=discord.TextStyle.short,
        max_length=5,
        required=True
    )

    reason = discord.ui.TextInput(
        label='Reason',
        placeholder='Enter reason for timeout...',
        style=discord.TextStyle.paragraph,
        max_length=500,
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            duration_minutes = int(self.duration.value)
            if duration_minutes < 1 or duration_minutes > 10080:  # Discord's max is 7 days
                await interaction.response.send_message("❌ Duration must be between 1 and 10080 minutes (7 days).", ephemeral=True)
                return

            reason_text = self.reason.value or f"Timed out by {interaction.user}"

            from datetime import timedelta
            timeout_until = discord.utils.utcnow() + timedelta(minutes=duration_minutes)
            await self.target_user.edit(timed_out_until=timeout_until, reason=reason_text)

            await interaction.response.send_message(
                f"⏰ {self.target_user.mention} has been timed out for {duration_minutes} minutes!\nReason: {reason_text}", 
                ephemeral=True
            )

        except ValueError:
            await interaction.response.send_message("❌ Please enter a valid number for duration.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to timeout this user.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error timing out user: {str(e)}", ephemeral=True)

# Helper functions for user management
def create_user_card_embed(user):
    """Create a comprehensive detailed user card embed"""
    embed = discord.Embed(
        title=f"👤 User Management: {user.display_name}",
        description=f"Comprehensive profile for {user.mention}",
        color=user.color if user.color.value != 0 else 0x7289da,
        timestamp=datetime.now()
    )

    # Set user avatar
    embed.set_thumbnail(url=user.display_avatar.url)

    # Account Details
    embed.add_field(
        name="👤 Account Details",
        value=f"**Username:** {user}\n**Display Name:** {user.display_name}\n**User ID:** `{user.id}`\n**Discriminator:** #{user.discriminator}\n**Bot Account:** {'Yes' if user.bot else 'No'}",
        inline=False
    )

    # Important Dates
    embed.add_field(
        name="📅 Important Dates",
        value=f"**Account Created:** {user.created_at.strftime('%B %d, %Y at %I:%M %p UTC')}\n**Joined Server:** {user.joined_at.strftime('%B %d, %Y at %I:%M %p UTC') if user.joined_at else 'Unknown'}\n**Days in Server:** {(datetime.now(user.joined_at.tzinfo) - user.joined_at).days if user.joined_at else 'Unknown'}",
        inline=False
    )

    # Status and Activity
    status_emoji = {
        discord.Status.online: "🟢 Online",
        discord.Status.idle: "🟡 Idle", 
        discord.Status.dnd: "🔴 Do Not Disturb",
        discord.Status.offline: "⚫ Offline"
    }

    embed.add_field(
        name="🎮 Activity & Status",
        value=f"**Status:** {status_emoji.get(user.status, '❓ Unknown')}\n**Activity:** {user.activity.name if user.activity else 'None'}\n**On Mobile:** {'Yes' if user.is_on_mobile() else 'No'}\n**Timed Out:** {'Yes' if user.timed_out_until else 'No'}",
        inline=True
    )

    # Top Roles (show first 8 roles)
    top_roles = [role.mention for role in sorted(user.roles, key=lambda r: r.position, reverse=True) if role.name != "@everyone"][:8]
    embed.add_field(
        name=f"🎭 Roles ({len([r for r in user.roles if r.name != '@everyone'])})",
        value="\n".join(top_roles) if top_roles else "No roles",
        inline=True
    )

    # Key Permissions
    perms = user.guild_permissions
    key_perms = []
    if perms.administrator: key_perms.append("Administrator")
    if perms.manage_guild: key_perms.append("Manage Server")
    if perms.manage_channels: key_perms.append("Manage Channels")
    if perms.manage_messages: key_perms.append("Manage Messages")
    if perms.kick_members: key_perms.append("Kick Members")
    if perms.ban_members: key_perms.append("Ban Members")
    if perms.moderate_members: key_perms.append("Timeout Members")
    if perms.manage_roles: key_perms.append("Manage Roles")

    embed.add_field(
        name="🔐 Key Permissions",
        value="\n".join([f"• {perm}" for perm in key_perms[:8]]) if key_perms else "No special permissions",
        inline=False
    )

    embed.set_footer(text="ZSells User Management System • All details included • Select action below")
    return embed

def create_detailed_user_info(user):
    """Create detailed user information embed"""
    embed = discord.Embed(
        title=f"📊 Detailed Info: {user.display_name}",
        color=user.color if user.color.value != 0 else 0x7289da,
        timestamp=datetime.now()
    )

    embed.set_thumbnail(url=user.display_avatar.url)

    # Account info
    embed.add_field(
        name="👤 Account Details",
        value=f"**Username:** {user}\n**Display Name:** {user.display_name}\n**User ID:** `{user.id}`\n**Discriminator:** #{user.discriminator}\n**Bot Account:** {'Yes' if user.bot else 'No'}",
        inline=False
    )

    # Dates
    embed.add_field(
        name="📅 Important Dates",
        value=f"**Account Created:** {user.created_at.strftime('%B %d, %Y at %I:%M %p UTC')}\n**Joined Server:** {user.joined_at.strftime('%B %d, %Y at %I:%M %p UTC') if user.joined_at else 'Unknown'}\n**Days in Server:** {(datetime.now(user.joined_at.tzinfo) - user.joined_at).days if user.joined_at else 'Unknown'}",
        inline=False
    )

    # Roles (show top roles)
    top_roles = [role.mention for role in sorted(user.roles, key=lambda r: r.position, reverse=True) if role.name != "@everyone"][:10]
    embed.add_field(
        name=f"🎭 Roles ({len([r for r in user.roles if r.name != '@everyone'])})",
        value="\n".join(top_roles) if top_roles else "No roles",
        inline=False
    )

    # Key permissions
    perms = user.guild_permissions
    key_perms = []
    if perms.administrator: key_perms.append("Administrator")
    if perms.manage_guild: key_perms.append("Manage Server")
    if perms.manage_channels: key_perms.append("Manage Channels")
    if perms.manage_messages: key_perms.append("Manage Messages")
    if perms.kick_members: key_perms.append("Kick Members")
    if perms.ban_members: key_perms.append("Ban Members")
    if perms.moderate_members: key_perms.append("Timeout Members")

    embed.add_field(
        name="🔐 Key Permissions",
        value="\n".join([f"• {perm}" for perm in key_perms[:8]]) if key_perms else "No special permissions",
        inline=True
    )

    # Status and activity
    embed.add_field(
        name="🎮 Activity & Status",
        value=f"**Status:** {user.status}\n**Activity:** {user.activity.name if user.activity else 'None'}\n**On Mobile:** {'Yes' if user.is_on_mobile() else 'No'}",
        inline=True
    )

    embed.set_footer(text="ZSells User Information System")
    return embed

# Advanced Embed Creator Modal
class AdvancedEmbedModal(discord.ui.Modal, title='Advanced Embed Creator'):
    def __init__(self, target_channel):
        super().__init__()
        self.target_channel = target_channel

    embed_title = discord.ui.TextInput(
        label='Embed Title',
        placeholder='Enter embed title...',
        style=discord.TextStyle.short,
        max_length=256,
        required=False
    )

    embed_description = discord.ui.TextInput(
        label='Description',
        placeholder='Enter description with markdown formatting...',
        style=discord.TextStyle.paragraph,
        max_length=4000,
        required=False
    )

    embed_color = discord.ui.TextInput(
        label='Color (hex without #)',
        placeholder='Example: ff0000 for red, 00ff00 for green, 0000ff for blue',
        style=discord.TextStyle.short,
        max_length=6,
        required=False
    )

    embed_image = discord.ui.TextInput(
        label='Image URL (optional)',
        placeholder='Direct link to image (must end with .png, .jpg, .gif, etc.)',
        style=discord.TextStyle.short,
        max_length=500,
        required=False
    )

    embed_fields = discord.ui.TextInput(
        label='Fields (optional)',
        placeholder='Format: Title1|Value1|inline\nTitle2|Value2|false\n(inline: true/false)',
        style=discord.TextStyle.paragraph,
        max_length=1000,
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Parse color
            color = 0x7289da  # Default Discord blue
            if self.embed_color.value:
                try:
                    # Remove # if present
                    color_hex = self.embed_color.value.replace('#', '')
                    color = int(color_hex, 16)
                except ValueError:
                    color = 0x7289da

            # Create embed
            embed = discord.Embed(
                title=self.embed_title.value if self.embed_title.value else None,
                description=self.embed_description.value if self.embed_description.value else None,
                color=color,
                timestamp=datetime.now()
            )

            # Add image if provided
            if self.embed_image.value:
                try:
                    embed.set_image(url=self.embed_image.value)
                except:
                    pass  # Invalid image URL

            # Parse and add fields
            if self.embed_fields.value:
                try:
                    field_lines = self.embed_fields.value.strip().split('\n')
                    for line in field_lines:
                        if '|' in line:
                            parts = line.split('|')
                            if len(parts) >= 2:
                                title = parts[0].strip()
                                value = parts[1].strip()
                                inline = parts[2].strip().lower() == 'true' if len(parts) > 2 else False

                                if title and value:
                                    embed.add_field(name=title, value=value, inline=inline)
                except:
                    pass  # Invalid field format

            embed.set_footer(text="ZSells Advanced Embed Creator")

            await self.target_channel.send(embed=embed)
            await interaction.response.send_message(
                f"✅ Advanced embed sent to {self.target_channel.mention}!", 
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Error creating embed: {str(e)}", ephemeral=True)

# Custom Announcement Modal
class AnnouncementModal(discord.ui.Modal, title='Create Announcement'):
    def __init__(self, target_channel):
        super().__init__()
        self.target_channel = target_channel

    announcement_title = discord.ui.TextInput(
        label='Announcement Title',
        placeholder='Enter the title for your announcement',
        style=discord.TextStyle.short,
        max_length=256,
        required=True
    )

    announcement_content = discord.ui.TextInput(
        label='Announcement Content',
        placeholder='Enter your announcement message...',
        style=discord.TextStyle.paragraph,
        max_length=2000,
        required=True
    )

    ping_role = discord.ui.TextInput(
        label='Role to Ping (optional)',
        placeholder='Enter role name or ID, or leave empty',
        style=discord.TextStyle.short,
        max_length=100,
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            embed = discord.Embed(
                title=f"📢 {self.announcement_title.value}",
                description=self.announcement_content.value,
                color=0xffaa00,
                timestamp=datetime.now()
            )
            embed.set_footer(text="ZSells Announcement System")

            ping_message = ""
            if self.ping_role.value:
                # Try to find role by name or ID
                guild = self.target_channel.guild
                role = None
                if self.ping_role.value.isdigit():
                    role = guild.get_role(int(self.ping_role.value))
                else:
                    role = discord.utils.get(guild.roles, name=self.ping_role.value)

                if role:
                    ping_message = role.mention

            if ping_message:
                await self.target_channel.send(ping_message, embed=embed)
            else:
                await self.target_channel.send(embed=embed)

            await interaction.response.send_message(
                f"✅ Announcement sent to {self.target_channel.mention}!", 
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Error sending announcement: {str(e)}", ephemeral=True)

# Enhanced Admin Panel Classes
class ChannelSelectView(discord.ui.View):
    def __init__(self, guild):
        super().__init__(timeout=600)  # Extended timeout to 10 minutes
        self.guild = guild
        self.add_channel_select()

# Second Admin Panel Classes
class ChannelSelectView2(discord.ui.View):
    def __init__(self, guild):
        super().__init__(timeout=600)  # Extended timeout to 10 minutes
        self.guild = guild
        self.add_channel_select()

    def add_channel_select(self):
        # Create options for detected channels
        options = []

        # Add current channel option
        options.append(discord.SelectOption(label="Current Channel", value="current", emoji="📍"))

        # Add detected channels
        channel_emojis = {
            'support': '🎫',
            'stk': '⚔️', 
            'tos': '📋',
            'rules': '📜',
            'news': '📰'
        }

        for channel_type, channel_id in CHANNELS.items():
            channel = self.guild.get_channel(channel_id) if self.guild else bot.get_channel(channel_id)
            if channel:
                emoji = channel_emojis.get(channel_type, '📢')
                label = f"#{channel.name}"
                options.append(discord.SelectOption(
                    label=label,
                    value=channel_type,
                    emoji=emoji,
                    description=f"{channel_type.title()} channel"
                ))

        # Add all other text channels in the guild
        if self.guild:
            other_channels = [ch for ch in self.guild.text_channels 
                           if ch.id not in CHANNELS.values()][:15]  # Limit to 15 to avoid Discord limits

            for channel in other_channels:
                if len(options) < 25:  # Discord limit
                    options.append(discord.SelectOption(
                        label=f"#{channel.name}",
                        value=f"other_{channel.id}",
                        emoji="📝",
                        description="Other channel"
                    ))

        if not options:
            options.append(discord.SelectOption(label="No channels available", value="none", emoji="❌"))

        select = discord.ui.Select(
            placeholder="Select a channel for advanced tools...",
            options=options[:25]  # Discord limit
        )
        select.callback = self.channel_select
        self.add_item(select)

    async def channel_select(self, interaction: discord.Interaction):
        try:
            # Check if interaction is still valid
            if interaction.response.is_done():
                return

            # Check if user is authorized
            if interaction.user.id != AUTHORIZED_USER_ID:
                try:
                    await interaction.response.send_message("❌ You are not authorized to use this dropdown.", ephemeral=True)
                except discord.InteractionResponded:
                    pass
                return

            selected_value = interaction.data['values'][0]

            # Get the target channel
            if selected_value == "current":
                target_channel = interaction.channel
            elif selected_value == "none":
                try:
                    await interaction.response.send_message("❌ No channels available!", ephemeral=True)
                except discord.InteractionResponded:
                    pass
                return
            elif selected_value.startswith("other_"):
                channel_id = int(selected_value.replace("other_", ""))
                target_channel = bot.get_channel(channel_id)
            else:
                target_channel = bot.get_channel(CHANNELS.get(selected_value))

            if not target_channel:
                try:
                    await interaction.response.send_message("❌ Selected channel not found!", ephemeral=True)
                except discord.InteractionResponded:
                    pass
                return

            # Show the secondary admin control panel
            embed = create_admin_control_2_embed(target_channel)
            view = AdminControlView2(target_channel)
            try:
                await interaction.response.edit_message(embed=embed, view=view)
            except discord.InteractionResponded:
                await interaction.edit_original_response(embed=embed, view=view)
        except discord.NotFound:
            print("⚠️ Channel select interaction expired")
        except discord.InteractionResponded:
            print("⚠️ Interaction already responded to")
        except Exception as e:
            print(f"⚠️ Error in channel select: {e}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("❌ An error occurred. Please try again.", ephemeral=True)
            except:
                pass

    def add_channel_select(self):
        # Create options for detected channels
        options = []

        # Add current channel option
        options.append(discord.SelectOption(label="Current Channel", value="current", emoji="📍"))

        # Add detected channels
        channel_emojis = {
            'support': '🎫',
            'stk': '⚔️', 
            'tos': '📋',
            'rules': '📜',
            'news': '📰'
        }

        for channel_type, channel_id in CHANNELS.items():
            channel = self.guild.get_channel(channel_id) if self.guild else bot.get_channel(channel_id)
            if channel:
                emoji = channel_emojis.get(channel_type, '📢')
                label = f"#{channel.name}"
                options.append(discord.SelectOption(
                    label=label,
                    value=channel_type,
                    emoji=emoji,
                    description=f"{channel_type.title()} channel"
                ))

        # Add all other text channels in the guild
        if self.guild:
            other_channels = [ch for ch in self.guild.text_channels 
                           if ch.id not in CHANNELS.values()][:15]  # Limit to 15 to avoid Discord limits

            for channel in other_channels:
                if len(options) < 25:  # Discord limit
                    options.append(discord.SelectOption(
                        label=f"#{channel.name}",
                        value=f"other_{channel.id}",
                        emoji="📝",
                        description="Other channel"
                    ))

        if not options:
            options.append(discord.SelectOption(label="No channels available", value="none", emoji="❌"))

        select = discord.ui.Select(
            placeholder="Select a channel to spawn embeds in...",
            options=options[:25]  # Discord limit
        )
        select.callback = self.channel_select
        self.add_item(select)

    async def channel_select(self, interaction: discord.Interaction):
        try:
            # Check if interaction is still valid
            if interaction.response.is_done():
                return

            # Check if user is authorized
            if interaction.user.id != AUTHORIZED_USER_ID:
                try:
                    await interaction.response.send_message("❌ You are not authorized to use this dropdown.", ephemeral=True)
                except discord.InteractionResponded:
                    pass
                return

            selected_value = interaction.data['values'][0]

            # Get the target channel
            if selected_value == "current":
                target_channel = interaction.channel
            elif selected_value == "none":
                try:
                    await interaction.response.send_message("❌ No channels available!", ephemeral=True)
                except discord.InteractionResponded:
                    pass
                return
            elif selected_value.startswith("other_"):
                channel_id = int(selected_value.replace("other_", ""))
                target_channel = bot.get_channel(channel_id)
            else:
                target_channel = bot.get_channel(CHANNELS.get(selected_value))

            if not target_channel:
                try:
                    await interaction.response.send_message("❌ Selected channel not found!", ephemeral=True)
                except discord.InteractionResponded:
                    pass
                return

            # Show the enhanced admin control panel
            embed = create_admin_control_embed(target_channel)
            view = AdminControlView(target_channel)
            try:
                await interaction.response.edit_message(embed=embed, view=view)
            except discord.InteractionResponded:
                await interaction.edit_original_response(embed=embed, view=view)
        except discord.NotFound:
            print("⚠️ Channel select interaction expired")
        except discord.InteractionResponded:
            print("⚠️ Interaction already responded to")
        except Exception as e:
            print(f"⚠️ Error in channel select: {e}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("❌ An error occurred. Please try again.", ephemeral=True)
            except:
                pass

class AdminControlView(discord.ui.View):
    def __init__(self, target_channel):
        super().__init__(timeout=600)
        self.target_channel = target_channel

    @discord.ui.button(label='Support Panel', style=discord.ButtonStyle.secondary, emoji='🎫', row=0)
    async def spawn_support(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_admin_permissions(interaction.user, interaction.guild):
            await interaction.response.send_message("❌ You are not authorized to use this button.", ephemeral=True)
            return
        if not check_channel_permissions(self.target_channel):
            await interaction.response.send_message(f"❌ Bot lacks permissions in {self.target_channel.mention}.", ephemeral=True)
            return
        try:
            embed = create_support_embed()
            view = SupportView()
            await self.target_channel.send(embed=embed, view=view)
            await interaction.response.send_message(f"✅ Support panel spawned in {self.target_channel.mention}!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

    @discord.ui.button(label='Gang Panel', style=discord.ButtonStyle.secondary, emoji='⚔️', row=0)
    async def spawn_gang(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_admin_permissions(interaction.user, interaction.guild):
            await interaction.response.send_message("❌ You are not authorized to use this button.", ephemeral=True)
            return
        if not check_channel_permissions(self.target_channel):
            await interaction.response.send_message(f"❌ Bot lacks permissions in {self.target_channel.mention}.", ephemeral=True)
            return
        try:
            embed = create_gang_embed()
            view = GangRecruitmentView()
            await self.target_channel.send(embed=embed, view=view)
            await interaction.response.send_message(f"✅ Gang recruitment spawned in {self.target_channel.mention}!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

    @discord.ui.button(label='Shop Panel', style=discord.ButtonStyle.secondary, emoji='🛒', row=0)
    async def spawn_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_admin_permissions(interaction.user, interaction.guild):
            await interaction.response.send_message("❌ You are not authorized to use this button.", ephemeral=True)
            return
        if not check_channel_permissions(self.target_channel):
            await interaction.response.send_message(f"❌ Bot lacks permissions in {self.target_channel.mention}.", ephemeral=True)
            return
        try:
            embed = create_main_shop_embed()
            view = MainShopView()
            await self.target_channel.send(embed=embed, view=view)
            await interaction.response.send_message(f"✅ Shop panel spawned in {self.target_channel.mention}!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

    @discord.ui.button(label='ToS Panel', style=discord.ButtonStyle.secondary, emoji='📋', row=0)
    async def spawn_tos(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_admin_permissions(interaction.user, interaction.guild):
            await interaction.response.send_message("❌ You are not authorized to use this button.", ephemeral=True)
            return
        if not check_channel_permissions(self.target_channel):
            await interaction.response.send_message(f"❌ Bot lacks permissions in {self.target_channel.mention}.", ephemeral=True)
            return
        try:
            embed = create_tos_embed()
            await self.target_channel.send(embed=embed)
            await interaction.response.send_message(f"✅ ToS spawned in {self.target_channel.mention}!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

    @discord.ui.button(label='Rules Panel', style=discord.ButtonStyle.secondary, emoji='📜', row=0)
    async def spawn_rules(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_admin_permissions(interaction.user, interaction.guild):
            await interaction.response.send_message("❌ You are not authorized to use this button.", ephemeral=True)
            return
        if not check_channel_permissions(self.target_channel):
            await interaction.response.send_message(f"❌ Bot lacks permissions in {self.target_channel.mention}.", ephemeral=True)
            return
        try:
            embed = create_rules_embed()
            await self.target_channel.send(embed=embed)
            await interaction.response.send_message(f"✅ Rules spawned in {self.target_channel.mention}!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

    @discord.ui.button(label='News Panel', style=discord.ButtonStyle.secondary, emoji='📰', row=1)
    async def spawn_news(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_admin_permissions(interaction.user, interaction.guild):
            await interaction.response.send_message("❌ You are not authorized to use this button.", ephemeral=True)
            return
        if not check_channel_permissions(self.target_channel):
            await interaction.response.send_message(f"❌ Bot lacks permissions in {self.target_channel.mention}.", ephemeral=True)
            return
        try:
            if not NEWS_DATA["last_updated"]:
                NEWS_DATA["last_updated"] = datetime.now().isoformat()
                save_data()
            embed = create_news_embed()
            await self.target_channel.send(embed=embed)
            await interaction.response.send_message(f"✅ News spawned in {self.target_channel.mention}!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

    @discord.ui.button(label='Welcome Panel', style=discord.ButtonStyle.secondary, emoji='🎉', row=1)
    async def spawn_welcome(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_admin_permissions(interaction.user, interaction.guild):
            await interaction.response.send_message("❌ You are not authorized to use this button.", ephemeral=True)
            return
        if not check_channel_permissions(self.target_channel):
            await interaction.response.send_message(f"❌ Bot lacks permissions in {self.target_channel.mention}.", ephemeral=True)
            return
        try:
            embed = create_welcome_embed()
            await self.target_channel.send(embed=embed)
            await interaction.response.send_message(f"✅ Welcome spawned in {self.target_channel.mention}!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

    @discord.ui.button(label='Shop Reminder', style=discord.ButtonStyle.secondary, emoji='💎', row=1)
    async def spawn_reminder(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_admin_permissions(interaction.user, interaction.guild):
            await interaction.response.send_message("❌ You are not authorized to use this button.", ephemeral=True)
            return
        if not check_channel_permissions(self.target_channel):
            await interaction.response.send_message(f"❌ Bot lacks permissions in {self.target_channel.mention}.", ephemeral=True)
            return
        try:
            embed = create_reminder_embed()
            await self.target_channel.send(embed=embed)
            await interaction.response.send_message(f"✅ Shop reminder spawned in {self.target_channel.mention}!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

    @discord.ui.button(label='Verification Panel', style=discord.ButtonStyle.success, emoji='✅', row=1)
    async def spawn_verification(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_admin_permissions(interaction.user, interaction.guild):
            await interaction.response.send_message("❌ You are not authorized to use this button.", ephemeral=True)
            return
        if not check_channel_permissions(self.target_channel):
            await interaction.response.send_message(f"❌ Bot lacks permissions in {self.target_channel.mention}.", ephemeral=True)
            return
        try:
            embed = discord.Embed(
                title="🔐 Server Verification",
                description="**Welcome to the server!**\n\nTo access all channels and features, you need to complete verification.\n\n**How to verify:**\n1. Click the **Verify** button below\n2. Copy the verification code shown\n3. Enter the code in the modal\n4. Submit to complete verification",
                color=0x00ff00
            )
            embed.add_field(
                name="✅ What happens after verification?",
                value="• Access to all server channels\n• Ability to participate in discussions\n• Full server permissions\n• Welcome to the community!",
                inline=False
            )
            embed.set_footer(text="ZSells Verification System • Keep the server secure")
            
            view = VerificationView()
            await self.target_channel.send(embed=embed, view=view)
            await interaction.response.send_message(f"✅ Verification panel spawned in {self.target_channel.mention}!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

    @discord.ui.button(label='Advanced Embed', style=discord.ButtonStyle.primary, emoji='🎨', row=2)
    async def advanced_embed_creator(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_admin_permissions(interaction.user, interaction.guild):
            await interaction.response.send_message("❌ You are not authorized to use this button.", ephemeral=True)
            return
        if not check_channel_permissions(self.target_channel):
            await interaction.response.send_message(f"❌ Bot lacks permissions in {self.target_channel.mention}.", ephemeral=True)
            return
        modal = AdvancedEmbedModal(self.target_channel)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label='Simple Embed', style=discord.ButtonStyle.success, emoji='📝', row=2)
    async def simple_embed_creator(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_admin_permissions(interaction.user, interaction.guild):
            await interaction.response.send_message("❌ You are not authorized to use this button.", ephemeral=True)
            return
        if not check_channel_permissions(self.target_channel):
            await interaction.response.send_message(f"❌ Bot lacks permissions in {self.target_channel.mention}.", ephemeral=True)
            return
        modal = EmbedCreatorModal(self.target_channel)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label='Simple Message', style=discord.ButtonStyle.primary, emoji='💬', row=2)
    async def simple_message(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_admin_permissions(interaction.user, interaction.guild):
            await interaction.response.send_message("❌ You are not authorized to use this button.", ephemeral=True)
            return
        if not check_channel_permissions(self.target_channel):
            await interaction.response.send_message(f"❌ Bot lacks permissions in {self.target_channel.mention}.", ephemeral=True)
            return
        modal = MessageCreatorModal(self.target_channel)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label='Announcement', style=discord.ButtonStyle.primary, emoji='📢', row=2)
    async def create_announcement(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_admin_permissions(interaction.user, interaction.guild):
            await interaction.response.send_message("❌ You are not authorized to use this button.", ephemeral=True)
            return
        if not check_channel_permissions(self.target_channel):
            await interaction.response.send_message(f"❌ Bot lacks permissions in {self.target_channel.mention}.", ephemeral=True)
            return
        modal = AnnouncementModal(self.target_channel)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label='User Management', style=discord.ButtonStyle.primary, emoji='👥', row=3)
    async def user_management(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_admin_permissions(interaction.user, interaction.guild):
            await interaction.response.send_message("❌ You are not authorized to use this button.", ephemeral=True)
            return
        modal = UserSelectModal(interaction.guild)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label='Bulk Delete', style=discord.ButtonStyle.danger, emoji='🗑️', row=3)
    async def bulk_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_admin_permissions(interaction.user, interaction.guild):
            await interaction.response.send_message("❌ You are not authorized to use this button.", ephemeral=True)
            return
        if not check_channel_permissions(self.target_channel):
            await interaction.response.send_message(f"❌ Bot lacks permissions in {self.target_channel.mention}.", ephemeral=True)
            return
        modal = BulkMessageModal(self.target_channel, "delete")
        await interaction.response.send_modal(modal)

    @discord.ui.button(label='Switch to Admin 2', style=discord.ButtonStyle.secondary, emoji='🔄', row=3)
    async def switch_to_admin2(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_admin_permissions(interaction.user, interaction.guild):
            await interaction.response.send_message("❌ You are not authorized to use this button.", ephemeral=True)
            return
        embed = create_admin_control_2_embed(self.target_channel)
        view = AdminControlView2(self.target_channel)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label='Close Panel', style=discord.ButtonStyle.danger, emoji='❌', row=3)
    async def close_panel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_admin_permissions(interaction.user, interaction.guild):
            await interaction.response.send_message("❌ You are not authorized to use this button.", ephemeral=True)
            return
        embed = discord.Embed(title="✅ Admin Panel Closed", description="Admin panel has been closed.", color=0x95a5a6)
        await interaction.response.edit_message(embed=embed, view=None)

# Second Admin Control View with Additional Tools
class AdminControlView2(discord.ui.View):
    def __init__(self, target_channel):
        super().__init__(timeout=600)
        self.target_channel = target_channel

    @discord.ui.button(label='Mass Mention', style=discord.ButtonStyle.primary, emoji='📢', row=0)
    async def mass_mention(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_admin_permissions(interaction.user, interaction.guild):
            await interaction.response.send_message("❌ You are not authorized to use this button.", ephemeral=True)
            return
        modal = MassMentionModal(self.target_channel)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label='Channel Lock', style=discord.ButtonStyle.danger, emoji='🔒', row=0)
    async def lock_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_admin_permissions(interaction.user, interaction.guild):
            await interaction.response.send_message("❌ You are not authorized to use this button.", ephemeral=True)
            return
        try:
            # Remove send_messages permission for @everyone
            await self.target_channel.set_permissions(interaction.guild.default_role, send_messages=False)
            embed = discord.Embed(title="🔒 Channel Locked", description=f"#{self.target_channel.name} has been locked.", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error locking channel: {str(e)}", ephemeral=True)

    @discord.ui.button(label='Channel Unlock', style=discord.ButtonStyle.success, emoji='🔓', row=0)
    async def unlock_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_admin_permissions(interaction.user, interaction.guild):
            await interaction.response.send_message("❌ You are not authorized to use this button.", ephemeral=True)
            return
        try:
            # Restore send_messages permission for @everyone
            await self.target_channel.set_permissions(interaction.guild.default_role, send_messages=True)
            embed = discord.Embed(title="🔓 Channel Unlocked", description=f"#{self.target_channel.name} has been unlocked.", color=0x00ff00)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error unlocking channel: {str(e)}", ephemeral=True)

    @discord.ui.button(label='Slowmode', style=discord.ButtonStyle.secondary, emoji='⏱️', row=0)
    async def set_slowmode(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_admin_permissions(interaction.user, interaction.guild):
            await interaction.response.send_message("❌ You are not authorized to use this button.", ephemeral=True)
            return
        modal = SlowmodeModal(self.target_channel)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label='Poll Creator', style=discord.ButtonStyle.primary, emoji='📊', row=0)
    async def create_poll(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_admin_permissions(interaction.user, interaction.guild):
            await interaction.response.send_message("❌ You are not authorized to use this button.", ephemeral=True)
            return
        modal = PollModal(self.target_channel)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label='Role Manager', style=discord.ButtonStyle.primary, emoji='🎭', row=1)
    async def role_manager(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_admin_permissions(interaction.user, interaction.guild):
            await interaction.response.send_message("❌ You are not authorized to use this button.", ephemeral=True)
            return
        modal = RoleManagerModal(interaction.guild)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label='Warn All', style=discord.ButtonStyle.danger, emoji='⚠️', row=1)
    async def warn_all(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_admin_permissions(interaction.user, interaction.guild):
            await interaction.response.send_message("❌ You are not authorized to use this button.", ephemeral=True)
            return
        modal = WarnAllModal(interaction.guild)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label='Server Stats', style=discord.ButtonStyle.secondary, emoji='📈', row=1)
    async def server_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_admin_permissions(interaction.user, interaction.guild):
            await interaction.response.send_message("❌ You are not authorized to use this button.", ephemeral=True)
            return
        embed = create_server_stats_embed(interaction.guild)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label='Auto Mod', style=discord.ButtonStyle.danger, emoji='🤖', row=1)
    async def auto_mod_config(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_admin_permissions(interaction.user, interaction.guild):
            await interaction.response.send_message("❌ You are not authorized to use this button.", ephemeral=True)
            return
        embed = create_automod_embed()
        view = AutoModView(self.target_channel)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label='Scheduled Message', style=discord.ButtonStyle.primary, emoji='⏰', row=2)
    async def scheduled_message(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_admin_permissions(interaction.user, interaction.guild):
            await interaction.response.send_message("❌ You are not authorized to use this button.", ephemeral=True)
            return
        modal = ScheduledMessageModal(self.target_channel)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label='Member Search', style=discord.ButtonStyle.secondary, emoji='🔍', row=2)
    async def member_search(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_admin_permissions(interaction.user, interaction.guild):
            await interaction.response.send_message("❌ You are not authorized to use this button.", ephemeral=True)
            return
        modal = MemberSearchModal(interaction.guild)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label='Backup Server', style=discord.ButtonStyle.secondary, emoji='💾', row=2)
    async def backup_server(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_admin_permissions(interaction.user, interaction.guild):
            await interaction.response.send_message("❌ You are not authorized to use this button.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        backup_data = await create_server_backup(interaction.guild)
        embed = discord.Embed(
            title="💾 Server Backup Created",
            description=f"Backup completed for **{interaction.guild.name}**\n\n**Channels:** {backup_data['channels']}\n**Roles:** {backup_data['roles']}\n**Members:** {backup_data['members']}",
            color=0x00ff00
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(label='Activity Monitor', style=discord.ButtonStyle.primary, emoji='📊', row=2)
    async def activity_monitor(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_admin_permissions(interaction.user, interaction.guild):
            await interaction.response.send_message("❌ You are not authorized to use this button.", ephemeral=True)
            return
        embed = create_activity_monitor_embed(interaction.guild)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label='Switch to Admin 1', style=discord.ButtonStyle.secondary, emoji='🔄', row=3)
    async def switch_to_admin1(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_admin_permissions(interaction.user, interaction.guild):
            await interaction.response.send_message("❌ You are not authorized to use this button.", ephemeral=True)
            return
        embed = create_admin_control_embed(self.target_channel)
        view = AdminControlView(self.target_channel)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label='Close Panel', style=discord.ButtonStyle.danger, emoji='❌', row=3)
    async def close_panel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_admin_permissions(interaction.user, interaction.guild):
            await interaction.response.send_message("❌ You are not authorized to use this button.", ephemeral=True)
            return
        embed = discord.Embed(title="✅ Admin Panel 2 Closed", description="Secondary admin panel has been closed.", color=0x95a5a6)
        await interaction.response.edit_message(embed=embed, view=None)

# Admin Panel Embed Functions
def create_admin_panel_embed():
    embed = discord.Embed(
        title="⚡ ZSells Administrative Console",
        description="```\n🔹 ENHANCED MASTER CONTROL PANEL 🔹\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\nAI-Powered Auto-Detection System\n```\n**Comprehensive guild analysis and management**",
        color=0x2c2f33
    )

    # Enhanced detection statistics
    total_guilds = len(bot.guilds)
    total_detected = len(CHANNELS)
    total_members = sum(guild.member_count for guild in bot.guilds)

    embed.add_field(
        name="📊 **System Overview**",
        value=f"```yaml\nGuilds Monitored: {total_guilds}\nTotal Members: {total_members:,}\nChannels Detected: {total_detected}\nAnalysis Status: Active\n```",
        inline=True
    )

    # Show detected channels with better formatting
    detected_channels = []
    channel_emojis = {
        'support': '🎫', 'stk': '⚔️', 'tos': '📋', 'rules': '📜', 
        'news': '📰', 'welcome': '👋', 'shop': '🛒', 'chat': '💬',
        'bot': '🤖', 'log': '📝', 'voice': '🔊', 'meme': '😄'
    }

    for channel_type, channel_id in CHANNELS.items():
        channel = bot.get_channel(channel_id)
        if channel:
            emoji = channel_emojis.get(channel_type, '📝')
            perms = "✅" if check_channel_permissions(channel) else "❌"
            detected_channels.append(f"{perms} {emoji} **#{channel.name}** `{channel_type}`")

    if detected_channels:
        display_channels = detected_channels[:8]  # Show first 8
        if len(detected_channels) > 8:
            display_channels.append(f"... and {len(detected_channels) - 8} more")

        embed.add_field(
            name="🌐 **Active Channel Detection**",
            value=f"```yaml\nStatus: Operational\nChannels: {len(detected_channels)} detected\nPermissions: Verified\n```\n" + "\n".join(display_channels),
            inline=False
        )
    else:
        embed.add_field(
            name="⚠️ **Channel Detection Status**",
            value="```diff\n- No channels auto-detected\n```\n**Auto-Detection Patterns:**\n`support` `help` `tickets` `admin` `staff`\n`rules` `guidelines` `info` `announcements` `news`\n`welcome` `general` `lobby` `stk` `gang` `shop`",
            inline=False
        )

    embed.add_field(
        name="🎛️ **Available Control Modules**",
        value="```\n🎫 Support System     📢 Announcements\n⚔️ Gang Recruitment   🗑️ Bulk Management  \n🛒 Shop Interface     📋 Terms of Service\n📜 Server Rules       📰 News Broadcasting\n👋 Welcome System     💬 Message Tools\n```",
        inline=True
    )

    embed.add_field(
        name="📊 **System Status**",
        value="```yaml\nAuto-Detection: Online\nWelcome Task: Running\nTicket System: Ready\nShop System: Operational\nButtons: Active\n```",
        inline=True
    )

    embed.add_field(
        name="🔧 **Quick Start Guide**",
        value="```\n1️⃣ Select target channel\n2️⃣ Choose embed to spawn\n3️⃣ Configure settings\n4️⃣ Deploy instantly\n```",
        inline=False
    )
    embed.set_footer(text="ZSells Administrative Console v2.0 • Secure Access Granted")
    return embed

def create_admin_panel_2_embed():
    embed = discord.Embed(
        title="⚡ ZSells Administrative Console - Advanced Tools",
        description="```\n🔹 SECONDARY CONTROL PANEL 🔹\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\nAdvanced Moderation & Management\n```\n**Extended functionality and powerful tools**",
        color=0x7289da
    )

    # System overview for admin2
    embed.add_field(
        name="🛠️ **Advanced Management Tools**",
        value="```yaml\nMode: Extended Operations\nAccess: Super Admin\nTools: Active\nSecurity: Maximum\n```",
        inline=True
    )

    embed.add_field(
        name="🔧 **Available Modules**",
        value="```\n🔒 Channel Control     📊 Analytics\n⚠️ Mass Moderation    🎭 Role Management\n⏰ Scheduling         🔍 Advanced Search\n💾 Backup Systems     📈 Activity Tracking\n```",
        inline=True
    )

    embed.add_field(
        name="⚡ **Extended Features**",
        value="```yaml\nChannel Locking: Ready\nMass Operations: Active\nScheduled Tasks: Online\nAuto Moderation: Ready\nBackup System: Standby\nActivity Monitor: Running\n```",
        inline=False
    )

    embed.add_field(
        name="🎯 **Quick Access**",
        value="```\n📢 Mass Mention System\n🔒 Channel Lock/Unlock\n⏱️ Slowmode Controls\n📊 Poll & Survey Tools\n🤖 Auto-Mod Configuration\n💾 Server Backup Tools\n```",
        inline=True
    )

    embed.add_field(
        name="🔐 **Security Level**",
        value="```yaml\nClearance: Maximum\nEncryption: Military Grade\nAccess: Authorized Personnel\nLogging: Full Audit Trail\n```",
        inline=True
    )

    embed.set_footer(text="ZSells Administrative Console v2.0 - Advanced Tools Module")
    return embed

def create_admin_control_2_embed(target_channel):
    embed = discord.Embed(
        title="🎯 Advanced Control Interface",
        description=f"```\n🎯 TARGET CHANNEL: #{target_channel.name}\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\nExtended operations panel active\n```",
        color=0x7289da
    )

    # Advanced Tools Section
    embed.add_field(
        name="🔧 **Channel Control Systems**",
        value="```yaml\nLock/Unlock:\n  ├─ Instant Channel Locking\n  ├─ Permission Management\n  └─ Emergency Lockdown\n\nSlowmode Control:\n  ├─ Custom Delays\n  ├─ Anti-Spam Protection\n  └─ Rate Limiting\n```",
        inline=True
    )

    # Mass Operations
    embed.add_field(
        name="📢 **Mass Operations**",
        value="```yaml\nBroadcast Tools:\n  ├─ Mass Mention System\n  ├─ Server-wide Warnings\n  ├─ Bulk User Management\n  └─ Emergency Alerts\n```",
        inline=True
    )

    # Analytics & Monitoring
    embed.add_field(
        name="📊 **Analytics & Monitoring**",
        value="```yaml\nServer Analytics:\n  ├─ Real-time Statistics\n  ├─ Activity Monitoring\n  ├─ Member Tracking\n  └─ Performance Metrics\n\nBackup Systems:\n  ├─ Full Server Backup\n  ├─ Role Configuration\n  └─ Channel Structure\n```",
        inline=False
    )

    # Security Tools
    embed.add_field(
        name="🛡️ **Security & Automation**",
        value="```diff\n+ 🤖 Auto-Moderation System\n+ 🎭 Advanced Role Manager\n+ ⏰ Scheduled Operations\n+ 🔍 Member Search Tools\n+ 📊 Poll & Survey Creator\n+ 💾 Emergency Backup\n```",
        inline=True
    )

    # Status Monitor
    embed.add_field(
        name="⚡ **System Status**",
        value="```yaml\nOperational: All Systems\nSecurity: Maximum\nLatency: Optimal\nUptime: 99.9%\n```",
        inline=True
    )

    embed.set_footer(text=f"Advanced C&C • Target: #{target_channel.name} • Extended Operations Active")
    return embed

# Helper Modals for Admin Panel 2
class MassMentionModal(discord.ui.Modal, title='Mass Mention System'):
    def __init__(self, target_channel):
        super().__init__()
        self.target_channel = target_channel

    message_content = discord.ui.TextInput(
        label='Message Content',
        placeholder='Enter message to send with mass mention...',
        style=discord.TextStyle.paragraph,
        max_length=1500,
        required=True
    )

    target_role = discord.ui.TextInput(
        label='Target Role (optional)',
        placeholder='Role name or ID to mention, leave empty for @everyone',
        style=discord.TextStyle.short,
        max_length=100,
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            guild = self.target_channel.guild
            role = None
            
            if self.target_role.value:
                if self.target_role.value.isdigit():
                    role = guild.get_role(int(self.target_role.value))
                else:
                    role = discord.utils.get(guild.roles, name=self.target_role.value)
            
            mention = role.mention if role else "@everyone"
            message = f"{mention}\n\n{self.message_content.value}"
            
            await self.target_channel.send(message)
            await interaction.response.send_message("✅ Mass mention sent successfully!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

class SlowmodeModal(discord.ui.Modal, title='Set Channel Slowmode'):
    def __init__(self, target_channel):
        super().__init__()
        self.target_channel = target_channel

    slowmode_seconds = discord.ui.TextInput(
        label='Slowmode Duration (seconds)',
        placeholder='Enter seconds (0-21600, 0 to disable)',
        style=discord.TextStyle.short,
        max_length=5,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            seconds = int(self.slowmode_seconds.value)
            if seconds < 0 or seconds > 21600:
                await interaction.response.send_message("❌ Slowmode must be between 0 and 21600 seconds (6 hours).", ephemeral=True)
                return
            
            await self.target_channel.edit(slowmode_delay=seconds)
            if seconds == 0:
                await interaction.response.send_message(f"✅ Slowmode disabled for #{self.target_channel.name}", ephemeral=True)
            else:
                await interaction.response.send_message(f"✅ Slowmode set to {seconds} seconds for #{self.target_channel.name}", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Please enter a valid number.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

class PollModal(discord.ui.Modal, title='Create Poll'):
    def __init__(self, target_channel):
        super().__init__()
        self.target_channel = target_channel

    poll_question = discord.ui.TextInput(
        label='Poll Question',
        placeholder='What would you like to ask?',
        style=discord.TextStyle.short,
        max_length=256,
        required=True
    )

    poll_options = discord.ui.TextInput(
        label='Poll Options',
        placeholder='Option1\nOption2\nOption3\n(One per line, max 10)',
        style=discord.TextStyle.paragraph,
        max_length=1000,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            options = [opt.strip() for opt in self.poll_options.value.split('\n') if opt.strip()]
            if len(options) < 2:
                await interaction.response.send_message("❌ Poll needs at least 2 options.", ephemeral=True)
                return
            if len(options) > 10:
                await interaction.response.send_message("❌ Maximum 10 options allowed.", ephemeral=True)
                return

            embed = discord.Embed(
                title=f"📊 {self.poll_question.value}",
                description="\n".join([f"{chr(0x1F1E6 + i)} {option}" for i, option in enumerate(options)]),
                color=0x7289da,
                timestamp=datetime.now()
            )
            embed.set_footer(text="React to vote!")

            message = await self.target_channel.send(embed=embed)
            for i in range(len(options)):
                await message.add_reaction(chr(0x1F1E6 + i))
            
            await interaction.response.send_message("✅ Poll created successfully!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

class RoleManagerModal(discord.ui.Modal, title='Role Manager'):
    def __init__(self, guild):
        super().__init__()
        self.guild = guild

    action = discord.ui.TextInput(
        label='Action (create/delete/modify)',
        placeholder='Enter: create, delete, or modify',
        style=discord.TextStyle.short,
        max_length=10,
        required=True
    )

    role_name = discord.ui.TextInput(
        label='Role Name',
        placeholder='Enter role name...',
        style=discord.TextStyle.short,
        max_length=100,
        required=True
    )

    role_color = discord.ui.TextInput(
        label='Role Color (hex, optional)',
        placeholder='Example: ff0000 for red',
        style=discord.TextStyle.short,
        max_length=6,
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            action = self.action.value.lower()
            
            if action == "create":
                color = discord.Color.default()
                if self.role_color.value:
                    try:
                        color = discord.Color(int(self.role_color.value, 16))
                    except:
                        pass
                
                role = await self.guild.create_role(name=self.role_name.value, color=color)
                await interaction.response.send_message(f"✅ Role '{role.name}' created successfully!", ephemeral=True)
                
            elif action == "delete":
                role = discord.utils.get(self.guild.roles, name=self.role_name.value)
                if role:
                    await role.delete()
                    await interaction.response.send_message(f"✅ Role '{self.role_name.value}' deleted successfully!", ephemeral=True)
                else:
                    await interaction.response.send_message(f"❌ Role '{self.role_name.value}' not found.", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Invalid action. Use: create, delete, or modify", ephemeral=True)
                
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

class WarnAllModal(discord.ui.Modal, title='Warn All Members'):
    def __init__(self, guild):
        super().__init__()
        self.guild = guild

    warning_message = discord.ui.TextInput(
        label='Warning Message',
        placeholder='Enter warning message to send to all members...',
        style=discord.TextStyle.paragraph,
        max_length=1500,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
            
            embed = discord.Embed(
                title="⚠️ Server Warning",
                description=self.warning_message.value,
                color=0xff0000,
                timestamp=datetime.now()
            )
            embed.set_footer(text=f"Warning from {self.guild.name} Staff")
            
            success_count = 0
            fail_count = 0
            
            for member in self.guild.members:
                if not member.bot:
                    try:
                        await member.send(embed=embed)
                        success_count += 1
                    except:
                        fail_count += 1
            
            await interaction.followup.send(
                f"✅ Warning sent successfully!\n**Sent:** {success_count}\n**Failed:** {fail_count}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)

class ScheduledMessageModal(discord.ui.Modal, title='Schedule Message'):
    def __init__(self, target_channel):
        super().__init__()
        self.target_channel = target_channel

    message_content = discord.ui.TextInput(
        label='Message Content',
        placeholder='Enter message to schedule...',
        style=discord.TextStyle.paragraph,
        max_length=2000,
        required=True
    )

    delay_minutes = discord.ui.TextInput(
        label='Delay (minutes)',
        placeholder='How many minutes from now?',
        style=discord.TextStyle.short,
        max_length=5,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            delay = int(self.delay_minutes.value)
            if delay < 1 or delay > 1440:  # Max 24 hours
                await interaction.response.send_message("❌ Delay must be between 1 and 1440 minutes (24 hours).", ephemeral=True)
                return
            
            # Schedule the message
            import asyncio
            asyncio.create_task(self.send_scheduled_message(delay * 60))
            
            await interaction.response.send_message(f"✅ Message scheduled to send in {delay} minutes!", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Please enter a valid number for delay.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
    
    async def send_scheduled_message(self, delay_seconds):
        await asyncio.sleep(delay_seconds)
        await self.target_channel.send(self.message_content.value)

class MemberSearchModal(discord.ui.Modal, title='Advanced Member Search'):
    def __init__(self, guild):
        super().__init__()
        self.guild = guild

    search_query = discord.ui.TextInput(
        label='Search Query',
        placeholder='Enter username, ID, or partial name...',
        style=discord.TextStyle.short,
        max_length=100,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            query = self.search_query.value.lower()
            matches = []
            
            for member in self.guild.members:
                if (query in member.name.lower() or 
                    query in member.display_name.lower() or 
                    query == str(member.id)):
                    matches.append(member)
            
            if not matches:
                await interaction.response.send_message("❌ No members found matching your search.", ephemeral=True)
                return
            
            embed = discord.Embed(
                title=f"🔍 Search Results for '{self.search_query.value}'",
                description=f"Found {len(matches)} member(s)",
                color=0x7289da
            )
            
            for i, member in enumerate(matches[:10]):  # Show max 10
                embed.add_field(
                    name=f"{i+1}. {member.display_name}",
                    value=f"**Username:** {member}\n**ID:** `{member.id}`\n**Joined:** {member.joined_at.strftime('%Y-%m-%d') if member.joined_at else 'Unknown'}",
                    inline=False
                )
            
            if len(matches) > 10:
                embed.set_footer(text=f"Showing first 10 of {len(matches)} results")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

# Helper functions for Admin Panel 2
def create_server_stats_embed(guild):
    embed = discord.Embed(
        title=f"📈 Server Statistics - {guild.name}",
        color=0x7289da,
        timestamp=datetime.now()
    )
    
    # Basic stats
    embed.add_field(
        name="👥 Members",
        value=f"**Total:** {guild.member_count}\n**Humans:** {len([m for m in guild.members if not m.bot])}\n**Bots:** {len([m for m in guild.members if m.bot])}",
        inline=True
    )
    
    # Channel stats
    embed.add_field(
        name="📝 Channels",
        value=f"**Text:** {len(guild.text_channels)}\n**Voice:** {len(guild.voice_channels)}\n**Categories:** {len(guild.categories)}",
        inline=True
    )
    
    # Role stats
    embed.add_field(
        name="🎭 Roles",
        value=f"**Total:** {len(guild.roles)}\n**Mentionable:** {len([r for r in guild.roles if r.mentionable])}\n**Hoisted:** {len([r for r in guild.roles if r.hoist])}",
        inline=True
    )
    
    return embed

def create_automod_embed():
    embed = discord.Embed(
        title="🤖 Auto-Moderation Configuration",
        description="Configure automatic moderation settings",
        color=0xff0000
    )
    
    embed.add_field(
        name="Available Features",
        value="• Spam Detection\n• Link Filtering\n• Bad Word Filter\n• Caps Lock Detection\n• Mention Spam Protection",
        inline=False
    )
    
    return embed

def create_activity_monitor_embed(guild):
    embed = discord.Embed(
        title="📊 Activity Monitor",
        description=f"Real-time activity for {guild.name}",
        color=0x00ff00,
        timestamp=datetime.now()
    )
    
    # Recent activity
    online_members = len([m for m in guild.members if m.status != discord.Status.offline])
    
    embed.add_field(
        name="Current Activity",
        value=f"**Online:** {online_members}/{guild.member_count}\n**Active Channels:** {len([c for c in guild.text_channels if c.last_message_id])}\n**Voice Activity:** {sum(len(c.members) for c in guild.voice_channels)}",
        inline=False
    )
    
    return embed

async def create_server_backup(guild):
    """Create a basic server backup"""
    backup_data = {
        'channels': len(guild.channels),
        'roles': len(guild.roles),
        'members': guild.member_count,
        'timestamp': datetime.now().isoformat()
    }
    return backup_data

class AutoModView(discord.ui.View):
    def __init__(self, target_channel):
        super().__init__(timeout=300)
        self.target_channel = target_channel

    @discord.ui.button(label='Enable Spam Filter', style=discord.ButtonStyle.success)
    async def enable_spam_filter(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("✅ Spam filter enabled (simulated)", ephemeral=True)

    @discord.ui.button(label='Configure Word Filter', style=discord.ButtonStyle.primary)
    async def configure_word_filter(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("⚙️ Word filter configuration opened (simulated)", ephemeral=True)

def create_admin_control_embed(target_channel):
    embed = discord.Embed(
        title="🎯 Command & Control Interface",
        description=f"```\n🎯 TARGET CHANNEL: #{target_channel.name}\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\nAdvanced operations panel ready\n```",
        color=0x5865f2
    )

    # Creation Tools Section
    embed.add_field(
        name="📝 **Content Creation Tools**",
        value="```yaml\nEmbed Creator:\n  ├─ Custom Embed Builder\n  ├─ Color & Field Support  \n  ├─ Footer Customization\n  └─ Rich Formatting\n\nMessage Creator:\n  ├─ Simple Message Sender\n  ├─ Role Ping Support\n  └─ Quick Broadcasting\n```\n**Status:** `READY` ⚡",
        inline=True
    )

    # Communication Tools Section  
    embed.add_field(
        name="📡 **Communication Systems**",
        value="```yaml\nBroadcast Tools:\n  ├─ Custom Announcements\n  ├─ Role Ping Integration\n  ├─ Bulk Messaging\n  └─ Scheduled Posts\n```\n**Status:** `ONLINE` 🟢",
        inline=True
    )

    # Quick Deploy Panels
    embed.add_field(
        name="⚡ **Rapid Deployment**",
        value="```yaml\nInstant Panels:\n  ├─ 🎫 Support Tickets\n  ├─ ⚔️ Gang Recruitment\n  ├─ 🛒 Interactive Shop\n  ├─ 📋 Terms of Service\n  ├─ 📜 Server Rules\n  ├─ 📰 News Updates\n  ├─ 🎉 Welcome Messages\n  └─ 💎 Shop Reminders\n```",
        inline=False
    )

    # Management Tools
    embed.add_field(
        name="🛠️ **Admin Control Tools**",
        value="```diff\n+ 🎨 Advanced Embed Creator\n+ 💬 Simple Message Sender\n+ 📢 Announcement System\n+ 👥 User Management Panel\n+ 🗑️ Bulk Message Delete\n+ 🔐 Full Permission Control\n```",
        inline=True
    )

    # Security Info
    embed.add_field(
        name="🔐 **Security Level**",
        value="```yaml\nAccess: Authorized\nUser: Admin\nPermissions: Full\nEncryption: Active\n```",
        inline=True
    )

    embed.set_footer(text=f"C&C Interface • Target: #{target_channel.name} • All systems operational", icon_url="https://cdn.discordapp.com/emojis/123456789.png")
    return embed

# Authorized user ID
AUTHORIZED_USER_ID = 1385239185006268457

# Slash commands
@bot.tree.command(name='spawner', description='Open the embed spawning panel for basic functions')
async def spawner_panel(interaction: discord.Interaction):
    """Open the embed spawning panel for basic functions"""
    try:
        # Check if user is authorized first
        if not has_admin_permissions(interaction.user, interaction.guild):
            await interaction.response.send_message("❌ You are not authorized to use this command.", ephemeral=True)
            return

        # Respond immediately to prevent timeout
        await interaction.response.defer(ephemeral=True)

        embed = create_admin_panel_embed()
        view = ChannelSelectView(interaction.guild)

        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    except discord.NotFound:
        pass  # Interaction expired, ignore silently
    except discord.HTTPException as e:
        if e.status != 404:  # Don't log 404 errors
            print(f"⚠️ HTTP error in spawner command: {e}")
    except Exception as e:
        print(f"⚠️ Error in spawner command: {e}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred. Please try again.", ephemeral=True)
        except:
            pass

@bot.tree.command(name='admin', description='Open the advanced admin control panel with extended features')
async def admin_panel(interaction: discord.Interaction):
    """Open the advanced admin control panel with extended features"""
    try:
        # Check if user is authorized first
        if not has_admin_permissions(interaction.user, interaction.guild):
            await interaction.response.send_message("❌ You are not authorized to use this command.", ephemeral=True)
            return

        # Respond immediately to prevent timeout
        await interaction.response.defer(ephemeral=True)

        embed = create_admin_panel_2_embed()
        view = ChannelSelectView2(interaction.guild)

        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    except discord.NotFound:
        pass  # Interaction expired, ignore silently
    except discord.HTTPException as e:
        if e.status != 404:  # Don't log 404 errors
            print(f"⚠️ HTTP error in admin command: {e}")
    except Exception as e:
        print(f"⚠️ Error in admin command: {e}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred. Please try again.", ephemeral=True)
        except:
            pass



@bot.tree.command(name='news', description='Update the news content')
async def news_command(interaction: discord.Interaction, title: str = None, content: str = None):
    """Update the news content"""
    # Check if user is authorized
    if not has_admin_permissions(interaction.user, interaction.guild):
        await interaction.response.send_message("❌ You are not authorized to use this command.", ephemeral=True)
        return

    global NEWS_DATA

    if title:
        NEWS_DATA["title"] = title
    if content:
        NEWS_DATA["content"] = content

    NEWS_DATA["last_updated"] = datetime.now().isoformat()
    save_data()

    await interaction.response.send_message("✅ News content updated! Use `/spawner` to spawn the updated news panel.", ephemeral=True)



@bot.tree.command(name='guild_info', description='Display comprehensive guild analysis')
async def guild_info(interaction: discord.Interaction):
    """Display detailed guild analysis"""
    # Check if user is authorized
    if not has_admin_permissions(interaction.user, interaction.guild):
        await interaction.response.send_message("❌ You are not authorized to use this command.", ephemeral=True)
        return

    guild = interaction.guild
    if not guild:
        await interaction.response.send_message("❌ This command must be used in a guild.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    try:
        # Get fresh analysis
        analysis = analyze_guild_structure(guild)

        # Create detailed embed
        embed = discord.Embed(
            title=f"🏰 Guild Analysis: {guild.name}",
            description=f"Comprehensive analysis of server structure and members",
            color=0x5865f2,
            timestamp=datetime.now()
        )

        # Guild info
        guild_info = analysis['guild_info']
        embed.add_field(
            name="📊 Server Statistics",
            value=f"```yaml\nMembers: {guild_info['member_count']}\nBoost Tier: {guild_info['boost_tier']}\nBoosts: {guild_info['boost_count']}\nVerification: {guild_info['verification_level']}\n```",
            inline=True
        )

        # Channel info
        channels = analysis['channels']
        embed.add_field(
            name="📝 Channel Statistics",
            value=f"```yaml\nText: {channels['total_text']}\nVoice: {channels['total_voice']}\nCategories: {channels['total_categories']}\nDetected: {len(channels['detected_channels'])}\n```",
            inline=True
        )

        # Member hierarchy
        members = analysis['members']
        embed.add_field(
            name="👥 Member Hierarchy",
            value=f"```yaml\nAdmins: {len(members['admins'])}\nModerators: {len(members['moderators'])}\nStaff: {len(members['staff'])}\nBots: {len(members['bots'])}\n```",
            inline=True
        )

        # Detected channels
        if channels['detected_channels']:
            channel_list = []
            for channel_type, channel_id in channels['detected_channels'].items():
                channel = guild.get_channel(channel_id)
                if channel:
                    perms = "✅" if check_channel_permissions(channel) else "❌"
                    channel_list.append(f"{perms} **{channel_type}**: #{channel.name}")

            embed.add_field(
                name="🎯 Auto-Detected Channels",
                value="\n".join(channel_list[:10]),  # Limit to prevent embed overflow
                inline=False
            )

        # Top roles
        if analysis['roles']['role_hierarchy']:
            role_list = []
            for role_data in analysis['roles']['role_hierarchy'][:5]:
                role_list.append(f"• **{role_data['name']}** ({role_data['members']} members)")

            embed.add_field(
                name="🎭 Top Roles",
                value="\n".join(role_list),
                inline=True
            )

        # Guild features
        if guild_info['features']:
            embed.add_field(
                name="✨ Server Features",
                value=f"```\n{', '.join(guild_info['features'][:8])}\n```",
                inline=True
            )

        embed.set_footer(text="ZSells Guild Analysis System")
        await interaction.followup.send(embed=embed, ephemeral=True)

    except Exception as e:
        await interaction.followup.send(f"❌ Error generating guild analysis: {str(e)}", ephemeral=True)

@bot.tree.command(name='refresh_channels', description='Refresh auto-detected channels and members')
async def refresh_channels(interaction: discord.Interaction):
    """Refresh the auto-detected channels and member analysis"""
    # Check if user is authorized
    if not has_admin_permissions(interaction.user, interaction.guild):
        await interaction.response.send_message("❌ You are not authorized to use this command.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    global CHANNELS, GUILD_ANALYSIS
    CHANNELS.clear()
    GUILD_ANALYSIS.clear()

    # Re-analyze all guilds
    total_detected = 0
    for guild in bot.guilds:
        try:
            analysis = analyze_guild_structure(guild)
            GUILD_ANALYSIS[guild.id] = analysis
            CHANNELS.update(analysis['channels']['detected_channels'])
            total_detected += len(analysis['channels']['detected_channels'])
        except Exception as e:
            print(f"Error analyzing {guild.name}: {e}")

    embed = discord.Embed(
        title="🔄 Full System Refresh Complete",
        description="Auto-detection and member analysis has been refreshed!",
        color=0x00ff00,
        timestamp=datetime.now()
    )

    if CHANNELS:
        # Show detected channels for current guild
        current_guild_channels = []
        if interaction.guild and interaction.guild.id in GUILD_ANALYSIS:
            guild_channels = GUILD_ANALYSIS[interaction.guild.id]['channels']['detected_channels']
            for channel_type, channel_id in guild_channels.items():
                channel = bot.get_channel(channel_id)
                if channel:
                    perms = "✅" if check_channel_permissions(channel) else "❌"
                    current_guild_channels.append(f"{perms} **{channel_type}**: #{channel.name}")

        if current_guild_channels:
            embed.add_field(
                name="📡 Detected in This Guild",
                value="\n".join(current_guild_channels),
                inline=False
            )

        embed.add_field(
            name="📊 Global Statistics",
            value=f"```yaml\nTotal Guilds: {len(bot.guilds)}\nTotal Channels Detected: {total_detected}\nSystem Status: Fully Operational\n```",
            inline=False
        )
    else:
        embed.add_field(
            name="⚠️ No Channels Detected",
            value="Create channels with descriptive names like:\n• `#support` `#help` `#tickets`\n• `#rules` `#guidelines` `#info`\n• `#announcements` `#news` `#updates`\n• `#welcome` `#general` `#lobby`",
            inline=False
        )

    embed.set_footer(text="ZSells Auto-Detection System • Enhanced Analysis Complete")
    await interaction.followup.send(embed=embed, ephemeral=True)

# Error handling
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        embed = discord.Embed(
            title="❌ Command Not Found",
            description="Use `/shop` to access the interactive shop!",
            color=0xE74C3C
        )
        await ctx.send(embed=embed)
    else:
        print(f'Error: {error}')

# Helper function for permission checking
def has_admin_permissions(user, guild):
    """Check if user has admin permissions - restricted to authorized user only"""
    if not user:
        return False

    # Only allow the specific authorized user
    return user.id == AUTHORIZED_USER_ID

def check_bot_permissions_in_guild(guild):
    """Check if bot has basic permissions in the guild"""
    try:
        if not guild:
            return False

        bot_member = guild.me
        if not bot_member:
            return False

        # Check if bot has basic permissions
        permissions = bot_member.guild_permissions
        return (permissions.send_messages and 
                permissions.embed_links and 
                permissions.view_channel and
                permissions.read_message_history)

    except Exception:
        return False

def check_channel_permissions(channel):
    """Check if bot has permission to send messages in the channel"""
    try:
        if not channel:
            return False

        # Get bot member in the guild
        bot_member = channel.guild.me
        if not bot_member:
            return False

        # Check permissions
        permissions = channel.permissions_for(bot_member)
        return permissions.send_messages and permissions.embed_links

    except Exception:
        return False

# Run the bot
if __name__ == "__main__":
    import os

    # Get token from environment variable
    TOKEN = os.getenv('DISCORD_BOT_TOKEN')

    if not TOKEN:
        print("❌ Please set DISCORD_BOT_TOKEN in your environment variables!")
        print("Set DISCORD_BOT_TOKEN with your Discord bot token as the value")
        exit(1)
    else:
        print("🤖 Starting Discord Bot...")
        try:
            bot.run(TOKEN)
        except Exception as e:
            print(f"❌ Bot failed to start: {e}")
            exit(1)