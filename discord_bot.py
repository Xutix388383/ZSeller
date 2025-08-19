import discord
from discord.ext import commands
import json
import os
from datetime import datetime

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Channel IDs
CHANNELS = {
    'support': 1407347212110925985,
    'stk': 1407347211049766912,
    'tos': 1407347205093982310,
    'rules': 1407347207677677709,
    'news': 1407347202329940000
}

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
        title="⚔️ Join STK Gang",
        description="**Elite Gang Recruitment Open!**\n\nSTK Gang is recruiting the most skilled and dedicated members. Are you ready to join the elite?",
        color=0x7289da
    )
    embed.add_field(
        name="🏆 What we offer",
        value="• Elite member status\n• Exclusive perks\n• Active community\n• Gang events\n• Premium support",
        inline=True
    )
    embed.add_field(
        name="⚡ Requirements",
        value="• Active participation\n• Loyalty to the gang\n• Respect for members\n• Follow gang rules\n• Regular activity",
        inline=True
    )
    embed.add_field(
        name="🎯 Gang Stats",
        value="• Members: 500+\n• Active daily: 200+\n• Gang level: Elite\n• Reputation: ⭐⭐⭐⭐⭐",
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
        title="📜 Server Rules",
        description="**ZSells Discord Server Rules - Follow for a Great Experience**",
        color=0xff0000
    )
    embed.add_field(
        name="💬 Chat Rules",
        value="• Be respectful to all members\n• No spam or excessive caps\n• English only in main channels\n• No NSFW content\n• Use appropriate channels",
        inline=False
    )
    embed.add_field(
        name="🛡️ Behavior Guidelines",
        value="• No harassment or bullying\n• No advertising other servers\n• No impersonation\n• No drama or arguments\n• Respect staff decisions",
        inline=False
    )
    embed.add_field(
        name="🎫 Support Rules",
        value="• One ticket per issue\n• Provide detailed information\n• Be patient with staff\n• No spam tickets\n• Use tickets for support only",
        inline=False
    )
    embed.add_field(
        name="⚠️ Consequences",
        value="• **Warning** → First offense\n• **Mute** → Repeated violations\n• **Kick** → Serious violations\n• **Ban** → Severe/repeated violations\n• **Permanent Ban** → ToS violations",
        inline=False
    )
    embed.set_footer(text="ZSells Rules • Staff have final say • Report issues to staff")
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
        value="• PayPal\n• Crypto\n• CashApp\n• Venmo",
        inline=True
    )
    embed.add_field(
        name="⏱️ Delivery Time",
        value="• Instant delivery\n• 24/7 support\n• Money back guarantee",
        inline=True
    )
    embed.add_field(
        name="📞 Contact Z Supply",
        value="Discord: Z Supply#1234\nWebsite: zsupply.com\nEmail: orders@zsupply.com",
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
        value="Discord: Z Supply#1234\nWebsite: zsupply.com\nEmail: orders@zsupply.com",
        inline=False
    )
    embed.add_field(
        name="💳 Payment Methods",
        value="PayPal • Crypto • CashApp • Venmo",
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
        value="Discord: Z Supply#1234\nWebsite: zsupply.com\nEmail: orders@zsupply.com",
        inline=False
    )
    embed.add_field(
        name="💳 Payment Methods",
        value="PayPal • Crypto • CashApp • Venmo",
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
        value="Discord: Z Supply#1234\nWebsite: zsupply.com\nEmail: orders@zsupply.com",
        inline=False
    )
    embed.add_field(
        name="💳 Payment Methods",
        value="PayPal • Crypto • CashApp • Venmo",
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
        value="Discord: Z Supply#1234\nWebsite: zsupply.com\nEmail: orders@zsupply.com",
        inline=False
    )
    embed.add_field(
        name="💳 Payment Methods",
        value="PayPal • Crypto • CashApp • Venmo",
        inline=False
    )

    embed.set_footer(text="Contact us to complete your order!")
    return embed

@bot.event
async def on_ready():
    load_data()

    # Add persistent views
    bot.add_view(SupportView())
    bot.add_view(GangRecruitmentView())

    # Auto-setup all embeds in their respective channels
    await auto_setup_all_embeds()

    try:
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} slash commands')
    except Exception as e:
        print(f'Failed to sync commands: {e}')

    print(f'{bot.user} has connected to Discord!')
    print('Bot is ready with all systems!')

async def auto_setup_all_embeds():
    """Automatically setup all embeds in their respective channels"""
    try:
        # Setup support panel
        support_channel = bot.get_channel(CHANNELS['support'])
        if support_channel:
            embed = create_support_embed()
            view = SupportView()
            await support_channel.send(embed=embed, view=view)
            print("✅ Support panel auto-setup complete!")

        # Setup gang recruitment
        stk_channel = bot.get_channel(CHANNELS['stk'])
        if stk_channel:
            embed = create_gang_embed()
            view = GangRecruitmentView()
            await stk_channel.send(embed=embed, view=view)
            print("✅ Gang recruitment panel auto-setup complete!")

        # Setup ToS
        tos_channel = bot.get_channel(CHANNELS['tos'])
        if tos_channel:
            embed = create_tos_embed()
            await tos_channel.send(embed=embed)
            print("✅ Terms of Service auto-setup complete!")

        # Setup Rules
        rules_channel = bot.get_channel(CHANNELS['rules'])
        if rules_channel:
            embed = create_rules_embed()
            await rules_channel.send(embed=embed)
            print("✅ Server rules auto-setup complete!")

        # Setup News
        news_channel = bot.get_channel(CHANNELS['news'])
        if news_channel:
            if not NEWS_DATA["last_updated"]:
                NEWS_DATA["last_updated"] = datetime.now().isoformat()
                save_data()
            embed = create_news_embed()
            await news_channel.send(embed=embed)
            print("✅ News channel auto-setup complete!")

    except Exception as e:
        print(f"Error in auto-setup: {e}")

# Admin Panel Classes
class ChannelSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.select(
        placeholder="Select a channel to spawn embeds in...",
        options=[
            discord.SelectOption(label="Support Channel", value="support", emoji="🎫"),
            discord.SelectOption(label="STK Gang Channel", value="stk", emoji="⚔️"),
            discord.SelectOption(label="Terms of Service Channel", value="tos", emoji="📋"),
            discord.SelectOption(label="Rules Channel", value="rules", emoji="📜"),
            discord.SelectOption(label="News Channel", value="news", emoji="📰"),
            discord.SelectOption(label="Current Channel", value="current", emoji="📍")
        ]
    )
    async def channel_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        selected_channel = select.values[0]
        
        # Get the target channel
        if selected_channel == "current":
            target_channel = interaction.channel
        else:
            target_channel = bot.get_channel(CHANNELS.get(selected_channel))
        
        if not target_channel:
            await interaction.response.send_message("❌ Selected channel not found!", ephemeral=True)
            return
        
        # Show the embed spawn panel
        embed = create_admin_spawn_embed(target_channel)
        view = EmbedSpawnView(target_channel)
        await interaction.response.edit_message(embed=embed, view=view)

class EmbedSpawnView(discord.ui.View):
    def __init__(self, target_channel):
        super().__init__(timeout=300)
        self.target_channel = target_channel

    @discord.ui.button(label='Support Panel', style=discord.ButtonStyle.primary, emoji='🎫')
    async def spawn_support(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = create_support_embed()
        view = SupportView()
        await self.target_channel.send(embed=embed, view=view)
        await interaction.response.send_message(f"✅ Support panel spawned in {self.target_channel.mention}!", ephemeral=True)

    @discord.ui.button(label='Gang Recruitment', style=discord.ButtonStyle.success, emoji='⚔️')
    async def spawn_gang(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = create_gang_embed()
        view = GangRecruitmentView()
        await self.target_channel.send(embed=embed, view=view)
        await interaction.response.send_message(f"✅ Gang recruitment panel spawned in {self.target_channel.mention}!", ephemeral=True)

    @discord.ui.button(label='Terms of Service', style=discord.ButtonStyle.secondary, emoji='📋')
    async def spawn_tos(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = create_tos_embed()
        await self.target_channel.send(embed=embed)
        await interaction.response.send_message(f"✅ Terms of Service spawned in {self.target_channel.mention}!", ephemeral=True)

    @discord.ui.button(label='Server Rules', style=discord.ButtonStyle.secondary, emoji='📜')
    async def spawn_rules(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = create_rules_embed()
        await self.target_channel.send(embed=embed)
        await interaction.response.send_message(f"✅ Server rules spawned in {self.target_channel.mention}!", ephemeral=True)

    @discord.ui.button(label='News Panel', style=discord.ButtonStyle.secondary, emoji='📰')
    async def spawn_news(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not NEWS_DATA["last_updated"]:
            NEWS_DATA["last_updated"] = datetime.now().isoformat()
            save_data()
        embed = create_news_embed()
        await self.target_channel.send(embed=embed)
        await interaction.response.send_message(f"✅ News panel spawned in {self.target_channel.mention}!", ephemeral=True)

    @discord.ui.button(label='Shop Panel', style=discord.ButtonStyle.danger, emoji='🛒', row=1)
    async def spawn_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = create_main_shop_embed()
        view = MainShopView()
        await self.target_channel.send(embed=embed, view=view)
        await interaction.response.send_message(f"✅ Shop panel spawned in {self.target_channel.mention}!", ephemeral=True)

    @discord.ui.button(label='Back to Channel Select', style=discord.ButtonStyle.primary, emoji='🔙', row=1)
    async def back_to_select(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = create_admin_panel_embed()
        view = ChannelSelectView()
        await interaction.response.edit_message(embed=embed, view=view)

# Admin Panel Embed Functions
def create_admin_panel_embed():
    embed = discord.Embed(
        title="🛠️ ZSells Admin Control Panel",
        description="**Master control panel for all bot functions**\n\nSelect a channel below to spawn embeds and panels.",
        color=0x7289da
    )
    embed.add_field(
        name="📍 Available Channels",
        value="• Support Channel\n• STK Gang Channel\n• Terms of Service Channel\n• Rules Channel\n• News Channel\n• Current Channel",
        inline=True
    )
    embed.add_field(
        name="🎛️ Available Panels",
        value="• Support Panel (with tickets)\n• Gang Recruitment\n• Terms of Service\n• Server Rules\n• News Panel\n• Shop Panel",
        inline=True
    )
    embed.add_field(
        name="ℹ️ Instructions",
        value="1. Select a channel from the dropdown\n2. Choose which embed to spawn\n3. Confirm the action\n4. Panel will appear instantly!",
        inline=False
    )
    embed.set_footer(text="ZSells Admin Panel • Requires Admin Permissions")
    return embed

def create_admin_spawn_embed(target_channel):
    embed = discord.Embed(
        title="🎯 Embed Spawn Panel",
        description=f"**Target Channel:** {target_channel.mention}\n\nClick the buttons below to spawn embeds in the selected channel.",
        color=0x00ff00
    )
    embed.add_field(
        name="🎫 Interactive Panels",
        value="• Support Panel (tickets + buttons)\n• Gang Recruitment (join button)\n• Shop Panel (full interactive shop)",
        inline=True
    )
    embed.add_field(
        name="📄 Static Embeds",
        value="• Terms of Service\n• Server Rules\n• News Panel",
        inline=True
    )
    embed.add_field(
        name="⚡ Quick Actions",
        value="All panels spawn instantly with full functionality. No setup required!",
        inline=False
    )
    embed.set_footer(text=f"Spawning in: #{target_channel.name}")
    return embed

# Authorized user ID
AUTHORIZED_USER_ID = 1385239185006268457

# Slash commands
@bot.tree.command(name='admin', description='Open the unified admin control panel')
async def admin_panel(interaction: discord.Interaction):
    """Open the unified admin control panel"""
    # Check if user is authorized
    if interaction.user.id != AUTHORIZED_USER_ID:
        await interaction.response.send_message("❌ You are not authorized to use this command.", ephemeral=True)
        return

    embed = create_admin_panel_embed()
    view = ChannelSelectView()
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name='shop', description='Open the interactive shop')
async def shop_slash(interaction: discord.Interaction):
    """Open the main interactive shop"""
    # Check if user is authorized
    if interaction.user.id != AUTHORIZED_USER_ID:
        await interaction.response.send_message("❌ You are not authorized to use this command.", ephemeral=True)
        return

    embed = create_main_shop_embed()
    view = MainShopView()
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name='news', description='Update the news content')
async def news_command(interaction: discord.Interaction, title: str = None, content: str = None):
    """Update the news content"""
    # Check if user is authorized
    if interaction.user.id != AUTHORIZED_USER_ID:
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
    """Check if user has admin permissions or required roles"""
    if not user or not guild:
        return False

    try:
        # Get the member object from the guild
        member = guild.get_member(user.id)
        if not member:
            return False

        # Check admin permissions safely
        try:
            if member.guild_permissions.administrator or member.guild_permissions.manage_guild:
                return True
        except (AttributeError, TypeError):
            pass

        # Check required roles
        try:
            user_role_ids = [role.id for role in member.roles if role]
            return STAFF_ROLE_ID in user_role_ids or OWNER_ROLE_ID in user_role_ids
        except (AttributeError, TypeError):
            pass

        return False

    except Exception:
        return False

# Run the bot
if __name__ == "__main__":
    import os

    # Get token from environment variable
    TOKEN = os.getenv('DISCORD_BOT_TOKEN')

    if not TOKEN:
        print("❌ Please set DISCORD_BOT_TOKEN in your Replit Secrets!")
        print("1. Go to Secrets tab in Replit")
        print("2. Add key: DISCORD_BOT_TOKEN")
        print("3. Add your Discord bot token as the value")
    else:
        bot.run(TOKEN)