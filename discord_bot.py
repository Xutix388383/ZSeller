import discord
from discord.ext import commands, tasks
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

# Channel detection function
def get_channels_by_name(guild):
    """Auto-detect channels by name patterns"""
    channels = {}

    if not guild:
        return channels

    # Define channel name patterns to look for
    channel_patterns = {
        'support': ['support', 'help', 'ticket', 'assistance'],
        'stk': ['stk', 'gang', 'recruitment', 'join'],
        'tos': ['tos', 'terms', 'terms-of-service', 'legal'],
        'rules': ['rules', 'server-rules', 'guidelines'],
        'news': ['news', 'announcements', 'updates', 'info'],
        'welcome': ['welcome', 'general', 'main', 'lobby']
    }

    # Get all text channels in the guild
    for channel in guild.text_channels:
        channel_name_lower = channel.name.lower()

        # Check each pattern category
        for category, patterns in channel_patterns.items():
            for pattern in patterns:
                if pattern in channel_name_lower:
                    if category not in channels:  # Only set if not already found
                        channels[category] = channel.id
                    break

    return channels

# Global variable to store detected channels
CHANNELS = {}

# Welcome message task
@tasks.loop(minutes=15)
async def send_welcome_message():
    """Send welcome message every 15 minutes"""
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

        # Send welcome message if channel found and bot has permissions
        if welcome_channel and check_channel_permissions(welcome_channel):
            embed = create_welcome_embed()
            await welcome_channel.send(embed=embed)
            print(f"✅ Welcome message sent to #{welcome_channel.name}")
        elif welcome_channel:
            print(f"❌ No permission to send welcome message in #{welcome_channel.name}")
        else:
            print("⚠️ No welcome channel found. Create a channel with 'welcome', 'general', or 'main' in the name.")

    except Exception as e:
        print(f"Error sending welcome message: {e}")

@send_welcome_message.before_loop
async def before_welcome_message():
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
        embed = discord.Embed(
            title="🎉 Welcome to STK Gang!",
            description="You're about to join one of the most elite gangs!\n\n**Click the link below to join:**\nhttps://discord.gg/C6agZhmhCA",
            color=0x7289da
        )
        embed.set_footer(text="STK Gang • Elite Members Only")
        await interaction.response.send_message(embed=embed, ephemeral=True)

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

@bot.event
async def on_ready():
    global CHANNELS
    load_data()

    # Add persistent views
    bot.add_view(SupportView())
    bot.add_view(GangRecruitmentView())

    # Auto-detect channels for each guild the bot is in
    for guild in bot.guilds:
        detected_channels = get_channels_by_name(guild)
        CHANNELS.update(detected_channels)

        print(f"📡 Auto-detected channels in {guild.name}:")
        for channel_type, channel_id in detected_channels.items():
            channel = guild.get_channel(channel_id)
            if channel:
                print(f"  • {channel_type}: #{channel.name} (ID: {channel_id})")

        if not detected_channels:
            print(f"  ⚠️  No matching channels found in {guild.name}")
            print(f"     Create channels with names like: support, rules, news, etc.")

    # Auto-setup all embeds in their respective channels
    await auto_setup_all_embeds()

    try:
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} slash commands')
    except Exception as e:
        print(f'Failed to sync commands: {e}')

    # Start the welcome message task
    if not send_welcome_message.is_running():
        send_welcome_message.start()
        print("✅ Welcome message task started (every 15 minutes)")

    print(f'{bot.user} has connected to Discord!')
    print('Bot is ready with all systems!')

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

# Advanced AI Embed Creator Modal
class AIEmbedModal(discord.ui.Modal, title='🤖 Advanced AI Embed Creator'):
    def __init__(self, target_channel):
        super().__init__()
        self.target_channel = target_channel

    embed_prompt = discord.ui.TextInput(
        label='🎯 AI Prompt - Describe what you want to create',
        placeholder='E.g., "Create a gaming tournament announcement with prizes, rules, and registration info in red theme with emojis"',
        style=discord.TextStyle.paragraph,
        max_length=2000,
        required=True
    )

    embed_style = discord.ui.TextInput(
        label='🎨 Style & Theme (optional)',
        placeholder='E.g., "professional, gaming, fun, serious, colorful, minimalist"',
        style=discord.TextStyle.short,
        max_length=100,
        required=False
    )

    custom_fields = discord.ui.TextInput(
        label='📝 Custom Fields (optional)',
        placeholder='Format: "Field1:Value1|Field2:Value2" - AI will add relevant fields if empty',
        style=discord.TextStyle.paragraph,
        max_length=500,
        required=False
    )

    embed_color = discord.ui.TextInput(
        label='🌈 Color (optional)',
        placeholder='E.g., #ff0000, red, blue, gold, random - AI will choose if empty',
        style=discord.TextStyle.short,
        max_length=20,
        required=False
    )

    footer_text = discord.ui.TextInput(
        label='👤 Footer Text (optional)',
        placeholder='Custom footer text - AI will generate if empty',
        style=discord.TextStyle.short,
        max_length=100,
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Generate advanced AI embed
            ai_embed = generate_advanced_ai_embed(
                prompt=self.embed_prompt.value,
                style=self.embed_style.value or None,
                custom_fields=self.custom_fields.value or None,
                color=self.embed_color.value or None,
                footer=self.footer_text.value or None,
                channel=self.target_channel
            )
            
            await self.target_channel.send(embed=ai_embed)
            await interaction.response.send_message(
                f"🤖 **AI Magic Complete!** ✨\nAdvanced embed generated and sent to {self.target_channel.mention}!\n\n*AI analyzed your prompt and created a custom embed with intelligent formatting.*", 
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ **AI Error:** {str(e)}\n\n*Try simplifying your prompt or check your formatting.*", 
                ephemeral=True
            )

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
        super().__init__(timeout=300)
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
            placeholder="Select a channel to spawn embeds in...",
            options=options[:25]  # Discord limit
        )
        select.callback = self.channel_select
        self.add_item(select)

    async def channel_select(self, interaction: discord.Interaction):
        # Check if user is authorized
        if interaction.user.id != AUTHORIZED_USER_ID:
            await interaction.response.send_message("❌ You are not authorized to use this dropdown.", ephemeral=True)
            return

        selected_value = interaction.data['values'][0]

        # Get the target channel
        if selected_value == "current":
            target_channel = interaction.channel
        elif selected_value == "none":
            await interaction.response.send_message("❌ No channels available!", ephemeral=True)
            return
        elif selected_value.startswith("other_"):
            channel_id = int(selected_value.replace("other_", ""))
            target_channel = bot.get_channel(channel_id)
        else:
            target_channel = bot.get_channel(CHANNELS.get(selected_value))

        if not target_channel:
            await interaction.response.send_message("❌ Selected channel not found!", ephemeral=True)
            return

        # Show the enhanced admin control panel
        embed = create_admin_control_embed(target_channel)
        view = AdminControlView(target_channel)
        await interaction.response.edit_message(embed=embed, view=view)

class AdminControlView(discord.ui.View):
    def __init__(self, target_channel):
        super().__init__(timeout=300)
        self.target_channel = target_channel

    @discord.ui.button(label='AI Embed Creator', style=discord.ButtonStyle.primary, emoji='🤖')
    async def ai_embed(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_admin_permissions(interaction.user, interaction.guild):
            await interaction.response.send_message("❌ You are not authorized to use this button.", ephemeral=True)
            return
        await interaction.response.send_modal(AIEmbedModal(self.target_channel))

    @discord.ui.button(label='Announcement', style=discord.ButtonStyle.success, emoji='📢')
    async def announcement(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_admin_permissions(interaction.user, interaction.guild):
            await interaction.response.send_message("❌ You are not authorized to use this button.", ephemeral=True)
            return
        await interaction.response.send_modal(AnnouncementModal(self.target_channel))

    @discord.ui.button(label='Bulk Delete', style=discord.ButtonStyle.danger, emoji='🗑️')
    async def bulk_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_admin_permissions(interaction.user, interaction.guild):
            await interaction.response.send_message("❌ You are not authorized to use this button.", ephemeral=True)
            return
        await interaction.response.send_modal(BulkMessageModal(self.target_channel, "delete"))

    @discord.ui.button(label='Support Panel', style=discord.ButtonStyle.secondary, emoji='🎫')
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

    @discord.ui.button(label='Gang Panel', style=discord.ButtonStyle.secondary, emoji='⚔️')
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

    @discord.ui.button(label='Shop Panel', style=discord.ButtonStyle.secondary, emoji='🛒', row=1)
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

    @discord.ui.button(label='ToS Panel', style=discord.ButtonStyle.secondary, emoji='📋', row=1)
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

    @discord.ui.button(label='Rules Panel', style=discord.ButtonStyle.secondary, emoji='📜', row=1)
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

    @discord.ui.button(label='Close Panel', style=discord.ButtonStyle.danger, emoji='❌', row=2)
    async def close_panel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_admin_permissions(interaction.user, interaction.guild):
            await interaction.response.send_message("❌ You are not authorized to use this button.", ephemeral=True)
            return
        embed = discord.Embed(title="✅ Admin Panel Closed", description="Admin panel has been closed.", color=0x95a5a6)
        await interaction.response.edit_message(embed=embed, view=None)

# Advanced AI Embed Generation System
def generate_advanced_ai_embed(prompt, style=None, custom_fields=None, color=None, footer=None, channel=None):
    """Advanced AI embed generator that can create any type of embed"""
    import random
    
    prompt_lower = prompt.lower()
    
    # Advanced color processing
    embed_color = parse_embed_color(color, style, prompt_lower)
    
    # AI Title Generation
    title = generate_ai_title(prompt, prompt_lower)
    
    # AI Description Generation
    description = generate_ai_description(prompt, prompt_lower, style)
    
    # Create the embed
    embed = discord.Embed(
        title=title,
        description=description,
        color=embed_color,
        timestamp=datetime.now()
    )
    
    # Add AI-generated fields
    ai_fields = generate_ai_fields(prompt, prompt_lower, custom_fields)
    for field in ai_fields:
        embed.add_field(**field)
    
    # Set footer
    if footer:
        embed.set_footer(text=footer)
    else:
        ai_footer = generate_ai_footer(prompt_lower, style)
        embed.set_footer(text=ai_footer)
    
    # Add thumbnail/image if relevant
    thumbnail_url = get_ai_thumbnail(prompt_lower)
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)
    
    return embed

def parse_embed_color(color, style, prompt_lower):
    """Parse color with AI assistance"""
    import random
    
    # Color map with more options
    color_map = {
        'red': 0xff0000, 'green': 0x00ff00, 'blue': 0x0000ff,
        'yellow': 0xffff00, 'orange': 0xffa500, 'purple': 0x800080,
        'pink': 0xffc0cb, 'black': 0x000000, 'white': 0xffffff,
        'gray': 0x808080, 'gold': 0xffd700, 'silver': 0xc0c0c0,
        'cyan': 0x00ffff, 'magenta': 0xff00ff, 'lime': 0x32cd32,
        'navy': 0x000080, 'maroon': 0x800000, 'teal': 0x008080,
        'olive': 0x808000, 'aqua': 0x00ffff, 'fuchsia': 0xff00ff,
        'crimson': 0xdc143c, 'indigo': 0x4b0082, 'violet': 0xee82ee,
        'turquoise': 0x40e0d0, 'coral': 0xff7f50, 'salmon': 0xfa8072
    }
    
    if color:
        color = color.strip().lower()
        if color == 'random':
            return random.choice(list(color_map.values()))
        elif color in color_map:
            return color_map[color]
        elif color.startswith('#'):
            try:
                return int(color[1:], 16)
            except ValueError:
                pass
    
    # AI color selection based on context
    if 'error' in prompt_lower or 'warning' in prompt_lower or 'danger' in prompt_lower:
        return 0xff0000  # Red
    elif 'success' in prompt_lower or 'complete' in prompt_lower or 'win' in prompt_lower:
        return 0x00ff00  # Green
    elif 'info' in prompt_lower or 'help' in prompt_lower or 'support' in prompt_lower:
        return 0x00aaff  # Blue
    elif 'shop' in prompt_lower or 'store' in prompt_lower or 'buy' in prompt_lower:
        return 0xffd700  # Gold
    elif 'tournament' in prompt_lower or 'game' in prompt_lower or 'competition' in prompt_lower:
        return 0xff6600  # Orange
    elif 'premium' in prompt_lower or 'vip' in prompt_lower or 'elite' in prompt_lower:
        return 0x9d4edd  # Purple
    elif 'welcome' in prompt_lower or 'join' in prompt_lower:
        return 0x00ff7f  # Spring green
    elif style:
        if 'professional' in style.lower():
            return 0x2c3e50  # Dark blue-gray
        elif 'fun' in style.lower() or 'colorful' in style.lower():
            return random.choice([0xff69b4, 0x00ced1, 0xff4500, 0x32cd32])
        elif 'serious' in style.lower():
            return 0x2f3136  # Discord dark
    
    # Default Discord blue
    return 0x7289da

def generate_ai_title(prompt, prompt_lower):
    """Generate intelligent titles based on prompt analysis"""
    
    # Extract key phrases and context
    if 'tournament' in prompt_lower:
        if 'announce' in prompt_lower:
            return "🏆 Tournament Announcement"
        else:
            return "🎮 Gaming Tournament"
    elif 'giveaway' in prompt_lower:
        return "🎁 Special Giveaway Event"
    elif 'update' in prompt_lower or 'patch' in prompt_lower:
        return "📋 Important Update"
    elif 'maintenance' in prompt_lower:
        return "🔧 Maintenance Notice"
    elif 'event' in prompt_lower:
        return "🎉 Special Event"
    elif 'welcome' in prompt_lower:
        return "👋 Welcome to Our Community!"
    elif 'rule' in prompt_lower:
        return "📜 Server Rules & Guidelines"
    elif 'shop' in prompt_lower or 'store' in prompt_lower:
        return "🛒 Premium Store"
    elif 'support' in prompt_lower or 'help' in prompt_lower:
        return "🎫 Support Center"
    elif 'recruitment' in prompt_lower or 'hiring' in prompt_lower:
        return "📢 We're Recruiting!"
    elif 'sale' in prompt_lower or 'discount' in prompt_lower:
        return "💰 Special Sale Event"
    elif 'partnership' in prompt_lower:
        return "🤝 Partnership Announcement"
    elif 'bot' in prompt_lower and 'update' in prompt_lower:
        return "🤖 Bot Update Information"
    else:
        # Extract the first few words as potential title
        words = prompt.split()[:4]
        return f"📋 {' '.join(words).title()}"

def generate_ai_description(prompt, prompt_lower, style):
    """Generate intelligent descriptions with context awareness"""
    
    # Base description with prompt reference
    description = f"*Generated with AI from your request*\n\n"
    
    # Context-aware content generation
    if 'tournament' in prompt_lower:
        description += "🏆 **Tournament Details**\n"
        if 'prize' in prompt_lower:
            description += "💰 Amazing prizes await the winners!\n"
        if 'register' in prompt_lower:
            description += "📝 Registration is now open for all participants.\n"
        description += "\n🎮 Join us for an epic gaming experience where skill meets competition!"
        
    elif 'giveaway' in prompt_lower:
        description += "🎁 **Exciting Giveaway Alert!**\n\n"
        description += "We're giving away amazing prizes to our community members!\n"
        if 'rule' in prompt_lower:
            description += "📋 Make sure to follow all the rules to qualify.\n"
        description += "✨ Good luck to everyone participating!"
        
    elif 'welcome' in prompt_lower:
        description += "🌟 **Welcome to Our Amazing Community!**\n\n"
        description += "We're thrilled to have you join us! Here's what you need to know:\n"
        description += "• Read our rules and guidelines\n"
        description += "• Introduce yourself in the appropriate channels\n"
        description += "• Have fun and make new friends!\n\n"
        description += "If you need any help, don't hesitate to reach out to our staff team."
        
    elif 'shop' in prompt_lower or 'store' in prompt_lower:
        description += "🛒 **Premium Store Experience**\n\n"
        description += "Browse our exclusive collection of premium items:\n"
        description += "• High-quality products\n"
        description += "• Instant delivery\n"
        description += "• 24/7 customer support\n"
        description += "• Secure payment options\n\n"
        description += "💎 *Your satisfaction is our priority!*"
        
    elif 'rule' in prompt_lower:
        description += "📜 **Community Guidelines**\n\n"
        description += "To maintain a positive environment for everyone:\n"
        description += "• Be respectful to all members\n"
        description += "• No spam or excessive self-promotion\n"
        description += "• Use appropriate channels\n"
        description += "• Follow Discord's Terms of Service\n\n"
        description += "⚖️ *Breaking these rules may result in warnings or bans.*"
        
    elif 'support' in prompt_lower:
        description += "🎫 **Support Information**\n\n"
        description += "Our support team is here to help you 24/7!\n"
        description += "• Create a ticket for personalized help\n"
        description += "• Check our FAQ for quick answers\n"
        description += "• Contact staff for urgent matters\n\n"
        description += "⏱️ *Average response time: 15 minutes*"
        
    elif 'update' in prompt_lower:
        description += "📋 **Important Update Information**\n\n"
        description += "We've made some exciting changes and improvements!\n"
        if 'bug' in prompt_lower or 'fix' in prompt_lower:
            description += "🐛 Several bugs have been fixed\n"
        if 'feature' in prompt_lower or 'new' in prompt_lower:
            description += "✨ New features have been added\n"
        description += "\n📈 *We're constantly improving your experience!*"
        
    else:
        # Generic AI-generated content based on prompt
        description += f"**Custom Content Generated**\n\n"
        description += f"Based on your request: *{prompt[:100]}{'...' if len(prompt) > 100 else ''}*\n\n"
        description += "This embed was intelligently created using advanced AI processing to match your specific requirements."
    
    # Add style-based modifications
    if style:
        if 'fun' in style.lower():
            description += "\n\n🎉 *Let's have some fun!*"
        elif 'professional' in style.lower():
            description += "\n\n*Professional service guaranteed.*"
        elif 'serious' in style.lower():
            description += "\n\n*This is an important matter.*"
    
    return description

def generate_ai_fields(prompt, prompt_lower, custom_fields):
    """Generate intelligent fields based on context"""
    fields = []
    
    # Parse custom fields if provided
    if custom_fields:
        try:
            field_pairs = custom_fields.split('|')
            for pair in field_pairs:
                if ':' in pair:
                    name, value = pair.split(':', 1)
                    fields.append({
                        'name': name.strip(),
                        'value': value.strip(),
                        'inline': len(value.strip()) < 50
                    })
        except Exception:
            pass
    
    # AI-generated fields based on context
    if 'tournament' in prompt_lower:
        if not any('date' in f.get('name', '').lower() for f in fields):
            fields.append({'name': '📅 Date & Time', 'value': 'To be announced soon!', 'inline': True})
        if not any('prize' in f.get('name', '').lower() for f in fields):
            fields.append({'name': '🏆 Prizes', 'value': 'Amazing rewards for winners!', 'inline': True})
        if not any('platform' in f.get('name', '').lower() for f in fields):
            fields.append({'name': '🎮 Platform', 'value': 'Check announcements', 'inline': True})
    
    elif 'giveaway' in prompt_lower:
        if not any('duration' in f.get('name', '').lower() for f in fields):
            fields.append({'name': '⏰ Duration', 'value': 'Limited time offer!', 'inline': True})
        if not any('winner' in f.get('name', '').lower() for f in fields):
            fields.append({'name': '🎯 Winners', 'value': 'Multiple winners selected', 'inline': True})
    
    elif 'shop' in prompt_lower or 'store' in prompt_lower:
        if not any('payment' in f.get('name', '').lower() for f in fields):
            fields.append({'name': '💳 Payment Methods', 'value': 'CashApp • Apple Pay', 'inline': True})
        if not any('contact' in f.get('name', '').lower() for f in fields):
            fields.append({'name': '📞 Contact', 'value': 'Contact: zpofe', 'inline': True})
        if not any('delivery' in f.get('name', '').lower() for f in fields):
            fields.append({'name': '🚚 Delivery', 'value': 'Instant delivery guaranteed', 'inline': True})
    
    elif 'support' in prompt_lower:
        if not any('response' in f.get('name', '').lower() for f in fields):
            fields.append({'name': '⏱️ Response Time', 'value': 'Usually within 15 minutes', 'inline': True})
        if not any('hour' in f.get('name', '').lower() for f in fields):
            fields.append({'name': '🕐 Availability', 'value': '24/7 Support Available', 'inline': True})
    
    elif 'welcome' in prompt_lower:
        if not any('channel' in f.get('name', '').lower() for f in fields):
            fields.append({'name': '📍 Important Channels', 'value': 'Check out our rules and announcements!', 'inline': False})
    
    # Add general helpful fields if none exist
    if not fields and 'contact' in prompt_lower:
        fields.append({'name': '📞 Contact Information', 'value': 'Contact: zpofe', 'inline': True})
    
    return fields

def generate_ai_footer(prompt_lower, style):
    """Generate intelligent footer text"""
    
    if 'shop' in prompt_lower or 'store' in prompt_lower:
        return "ZSells Premium Store • Trusted by thousands of customers"
    elif 'support' in prompt_lower:
        return "ZSells Support System • We're here to help!"
    elif 'tournament' in prompt_lower:
        return "ZSells Gaming • Where legends are made"
    elif 'giveaway' in prompt_lower:
        return "ZSells Community • Bringing joy to our members"
    elif 'welcome' in prompt_lower:
        return "ZSells Community • Welcome to the family!"
    elif style and 'professional' in style.lower():
        return "ZSells Services • Professional excellence guaranteed"
    else:
        return "ZSells AI • Generated with advanced AI technology"

def get_ai_thumbnail(prompt_lower):
    """Get appropriate thumbnail URL based on context"""
    # This would typically use actual image URLs
    # For now, returning None as we don't have hosted images
    # In a real implementation, you'd have a library of relevant images
    return None

# Admin Panel Embed Functions
def create_admin_panel_embed():
    embed = discord.Embed(
        title="⚡ ZSells Administrative Console",
        description="```\n🔹 MASTER CONTROL PANEL 🔹\n━━━━━━━━━━━━━━━━━━━━━━━━━━\nAdvanced bot management system\n```\n**Select a target channel to begin operations**",
        color=0x2c2f33
    )
    embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1234567890/settings.png")

    # Show detected channels with better formatting
    detected_channels = []
    channel_emojis = {
        'support': '🎫',
        'stk': '⚔️',
        'tos': '📋',
        'rules': '📜',
        'news': '📰',
        'welcome': '👋'
    }
    
    for channel_type, channel_id in CHANNELS.items():
        channel = bot.get_channel(channel_id)
        if channel:
            emoji = channel_emojis.get(channel_type, '📝')
            detected_channels.append(f"{emoji} **#{channel.name}** `{channel_type}`")

    if detected_channels:
        embed.add_field(
            name="🌐 **Active Channel Detection**",
            value=f"```yaml\nStatus: Online\nChannels: {len(detected_channels)} detected\n```\n" + "\n".join(detected_channels),
            inline=False
        )
    else:
        embed.add_field(
            name="⚠️ **Channel Detection Status**",
            value="```diff\n- No channels auto-detected\n```\n**Required Channel Names:**\n`support` `help` `tickets` `rules` `guidelines`\n`news` `announcements` `stk` `gang` `recruitment`",
            inline=False
        )

    embed.add_field(
        name="🎛️ **Available Control Modules**",
        value="```\n🎫 Support System     📢 Announcements\n⚔️ Gang Recruitment   🗑️ Bulk Management  \n🛒 Shop Interface     📋 Terms of Service\n📜 Server Rules       📰 News Broadcasting\n👋 Welcome System     🤖 AI Assistant\n```",
        inline=True
    )
    
    embed.add_field(
        name="📊 **System Status**",
        value="```yaml\nAI Module: Active\nAuto-Detection: Online\nWelcome Task: Running\nTicket System: Ready\nShop System: Operational\n```",
        inline=True
    )
    
    embed.add_field(
        name="🔧 **Quick Start Guide**",
        value="```\n1️⃣ Select target channel\n2️⃣ Choose control module\n3️⃣ Configure settings\n4️⃣ Deploy instantly\n```",
        inline=False
    )
    embed.set_footer(text="ZSells Administrative Console v2.0 • Secure Access Granted", icon_url="https://cdn.discordapp.com/emojis/123456789.png")
    return embed

def create_admin_control_embed(target_channel):
    embed = discord.Embed(
        title="🎯 Command & Control Interface",
        description=f"```\n🎯 TARGET CHANNEL: #{target_channel.name}\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\nAdvanced operations panel ready\n```",
        color=0x5865f2
    )

    # AI & Advanced Features Section
    embed.add_field(
        name="🤖 **Artificial Intelligence Module**",
        value="```yaml\nAI Embed Creator:\n  ├─ Smart Content Generation\n  ├─ Context-Aware Responses  \n  ├─ Dynamic Field Creation\n  └─ Advanced Formatting\n```\n**Status:** `READY` ⚡",
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
        value="```yaml\nInstant Panels:\n  ├─ 🎫 Support Tickets\n  ├─ ⚔️ Gang Recruitment\n  ├─ 🛒 Interactive Shop\n  ├─ 📋 Terms & Rules\n  └─ 👋 Welcome Center\n```",
        inline=False
    )

    # Management Tools
    embed.add_field(
        name="🛠️ **Channel Management**",
        value="```diff\n+ Bulk Message Deletion\n+ Advanced Moderation\n+ Channel Analytics\n+ Permission Control\n```",
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
@bot.tree.command(name='admin', description='Open the advanced admin control panel with AI features')
async def admin_panel(interaction: discord.Interaction):
    """Open the advanced admin control panel with AI features"""
    # Check if user is authorized
    if not has_admin_permissions(interaction.user, interaction.guild):
        await interaction.response.send_message("❌ You are not authorized to use this command.", ephemeral=True)
        return

    embed = create_admin_panel_embed()
    view = ChannelSelectView(interaction.guild)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)



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

    await interaction.response.send_message("✅ News content updated! Use `/admin` to spawn the updated news panel.", ephemeral=True)

@bot.tree.command(name='refresh_channels', description='Refresh auto-detected channels')
async def refresh_channels(interaction: discord.Interaction):
    """Refresh the auto-detected channels"""
    # Check if user is authorized
    if not has_admin_permissions(interaction.user, interaction.guild):
        await interaction.response.send_message("❌ You are not authorized to use this command.", ephemeral=True)
        return

    global CHANNELS
    CHANNELS.clear()

    # Re-detect channels for each guild
    for guild in bot.guilds:
        detected_channels = get_channels_by_name(guild)
        CHANNELS.update(detected_channels)

    embed = discord.Embed(
        title="🔄 Channels Refreshed",
        description="Auto-detection has been refreshed!",
        color=0x00ff00
    )

    if CHANNELS:
        channel_list = []
        for channel_type, channel_id in CHANNELS.items():
            channel = bot.get_channel(channel_id)
            if channel:
                channel_list.append(f"• #{channel.name} ({channel_type})")

        embed.add_field(
            name="📡 Detected Channels",
            value="\n".join(channel_list),
            inline=False
        )
    else:
        embed.add_field(
            name="⚠️ No Channels Detected",
            value="Create channels with names like: support, rules, news, stk, etc.",
            inline=False
        )

    await interaction.response.send_message(embed=embed, ephemeral=True)

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