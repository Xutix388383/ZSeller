import discord
from discord.ext import commands
import json

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Shop data
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

# Custom Shop Data Storage
custom_shops = {}

# Views for button interactions
class CustomShopBuilderView(discord.ui.View):
    def __init__(self, shop_name, shop_description):
        super().__init__(timeout=600)
        self.shop_name = shop_name
        self.shop_description = shop_description
        self.categories = []
        
    @discord.ui.button(label='Add Category', style=discord.ButtonStyle.primary, emoji='📂')
    async def add_category(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = AddCategoryModal(self)
        await interaction.response.send_modal(modal)
        
    @discord.ui.button(label='Preview Shop', style=discord.ButtonStyle.success, emoji='👀')
    async def preview_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.categories:
            embed = discord.Embed(
                title="❌ No Categories",
                description="Add at least one category before previewing!",
                color=0xE74C3C
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
            
        embed = create_custom_shop_embed(self.shop_name, self.shop_description, self.categories)
        view = CustomShopView(self.shop_name, self.categories)
        await interaction.response.send_message(embed=embed, view=view)
        
    @discord.ui.button(label='Save Shop', style=discord.ButtonStyle.secondary, emoji='💾')
    async def save_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.categories:
            embed = discord.Embed(
                title="❌ Cannot Save",
                description="Add at least one category before saving!",
                color=0xE74C3C
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
            
        shop_id = f"{interaction.user.id}_{self.shop_name.lower().replace(' ', '_')}"
        custom_shops[shop_id] = {
            'name': self.shop_name,
            'description': self.shop_description,
            'categories': self.categories,
            'owner': interaction.user.id
        }
        
        embed = discord.Embed(
            title="✅ Shop Saved!",
            description=f"Your shop **{self.shop_name}** has been saved successfully!",
            color=0x2ECC71
        )
        embed.add_field(
            name="Shop ID",
            value=f"`{shop_id}`",
            inline=False
        )
        embed.add_field(
            name="Access Your Shop",
            value=f"Use `/my_shops` to view all your saved shops",
            inline=False
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

class AddCategoryModal(discord.ui.Modal):
    def __init__(self, builder_view):
        super().__init__(title="Add New Category")
        self.builder_view = builder_view
        
    category_name = discord.ui.TextInput(
        label="Category Name",
        placeholder="e.g., Weapons, Electronics, Services...",
        max_length=50
    )
    
    category_emoji = discord.ui.TextInput(
        label="Category Emoji",
        placeholder="e.g., 🔫, 💻, ⚙️...",
        max_length=2
    )
    
    products = discord.ui.TextInput(
        label="Products (one per line)",
        placeholder="Product 1\nProduct 2\nProduct 3...",
        style=discord.TextStyle.paragraph,
        max_length=1000
    )
    
    prices = discord.ui.TextInput(
        label="Prices (one per line, match products)",
        placeholder="10.00\n15.50\n20.00...",
        style=discord.TextStyle.paragraph,
        max_length=500
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            product_list = [p.strip() for p in self.products.value.split('\n') if p.strip()]
            price_list = [float(p.strip()) for p in self.prices.value.split('\n') if p.strip()]
            
            if len(product_list) != len(price_list):
                embed = discord.Embed(
                    title="❌ Mismatch Error",
                    description="Number of products must match number of prices!",
                    color=0xE74C3C
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
                
            category = {
                'name': self.category_name.value,
                'emoji': self.category_emoji.value,
                'products': [{'name': name, 'price': price} for name, price in zip(product_list, price_list)]
            }
            
            self.builder_view.categories.append(category)
            
            embed = discord.Embed(
                title="✅ Category Added!",
                description=f"Added category: {self.category_emoji.value} **{self.category_name.value}**",
                color=0x2ECC71
            )
            embed.add_field(
                name="Products Added",
                value=f"{len(product_list)} products",
                inline=True
            )
            embed.add_field(
                name="Total Categories",
                value=f"{len(self.builder_view.categories)}",
                inline=True
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except ValueError:
            embed = discord.Embed(
                title="❌ Price Error",
                description="All prices must be valid numbers!",
                color=0xE74C3C
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

class CustomShopView(discord.ui.View):
    def __init__(self, shop_name, categories):
        super().__init__(timeout=300)
        self.shop_name = shop_name
        self.categories = categories
        
        # Add buttons for each category (max 5 due to Discord limits)
        for i, category in enumerate(categories[:5]):
            button = discord.ui.Button(
                label=category['name'],
                style=discord.ButtonStyle.primary,
                emoji=category['emoji'],
                custom_id=f"category_{i}"
            )
            button.callback = self.create_category_callback(i)
            self.add_item(button)
    
    def create_category_callback(self, category_index):
        async def callback(interaction: discord.Interaction):
            category = self.categories[category_index]
            embed = create_custom_category_embed(category)
            view = CustomCategoryView(category, self.shop_name, self.categories)
            await interaction.response.edit_message(embed=embed, view=view)
        return callback

class CustomCategoryView(discord.ui.View):
    def __init__(self, category, shop_name, all_categories):
        super().__init__(timeout=300)
        self.category = category
        self.shop_name = shop_name
        self.all_categories = all_categories
        
        # Create the select dropdown with product options
        product_options = [
            discord.SelectOption(
                label=f"{product['name']} - ${product['price']:.2f}",
                value=str(i),
                emoji="🛍️"
            ) for i, product in enumerate(category['products'][:25])
        ]
        
        if product_options:  # Only add select if there are products
            self.product_select = discord.ui.Select(
                placeholder="Choose a product...",
                options=product_options
            )
            self.product_select.callback = self.product_select_callback
            self.add_item(self.product_select)
        
    async def product_select_callback(self, interaction: discord.Interaction):
    select = interaction.data['values']
        product_index = int(select[0])
        product = self.category['products'][product_index]
        
        embed = discord.Embed(
            title="🛍️ Product Selected",
            description=f"You selected: **{product['name']}**",
            color=0x3498DB
        )
        embed.add_field(name="Price", value=f"${product['price']:.2f}", inline=True)
        embed.add_field(name="Category", value=f"{self.category['emoji']} {self.category['name']}", inline=True)
        embed.add_field(
            name="Order Instructions",
            value="Contact the shop owner to complete your purchase!",
            inline=False
        )
        
        view = CustomOrderView(product, self.category, self.shop_name, self.all_categories)
        await interaction.response.edit_message(embed=embed, view=view)
        
    @discord.ui.button(label='Back to Shop', style=discord.ButtonStyle.secondary, emoji='🏠')
    async def back_to_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = create_custom_shop_embed(self.shop_name, "", self.all_categories)
        view = CustomShopView(self.shop_name, self.all_categories)
        await interaction.response.edit_message(embed=embed, view=view)

class CustomOrderView(discord.ui.View):
    def __init__(self, product, category, shop_name, all_categories):
        super().__init__(timeout=300)
        self.product = product
        self.category = category
        self.shop_name = shop_name
        self.all_categories = all_categories
        
    @discord.ui.button(label='Order This Item', style=discord.ButtonStyle.success, emoji='✅')
    async def order_item(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="📦 Order Placed!",
            description=f"Your order for **{self.product['name']}** has been recorded!",
            color=0x2ECC71
        )
        embed.add_field(name="Item", value=self.product['name'], inline=True)
        embed.add_field(name="Price", value=f"${self.product['price']:.2f}", inline=True)
        embed.add_field(name="Shop", value=self.shop_name, inline=True)
        embed.add_field(
            name="Next Steps",
            value="Contact the shop owner through Discord to arrange payment and delivery!",
            inline=False
        )
        
        await interaction.response.edit_message(embed=embed, view=CustomOrderView(self.product, self.category, self.shop_name, self.all_categories))
        
    @discord.ui.button(label='Back to Category', style=discord.ButtonStyle.primary, emoji='📂')
    async def back_to_category(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = create_custom_category_embed(self.category)
        view = CustomCategoryView(self.category, self.shop_name, self.all_categories)
        await interaction.response.edit_message(embed=embed, view=view)
        
    @discord.ui.button(label='Back to Shop', style=discord.ButtonStyle.secondary, emoji='🏠')
    async def back_to_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = create_custom_shop_embed(self.shop_name, "", self.all_categories)
        view = CustomShopView(self.shop_name, self.all_categories)
        await interaction.response.edit_message(embed=embed, view=view)

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

    @discord.ui.button(label='Cart', style=discord.ButtonStyle.danger, emoji='🛒')
    async def cart_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_cart_embed(), view=CartView())

class WeaponsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.selected_weapons = []

    @discord.ui.select(
        placeholder="Choose weapons (multiple allowed)...",
        options=[discord.SelectOption(label=weapon, value=weapon, emoji="🔫") for weapon in WEAPONS[:25]],
        max_values=len(WEAPONS[:25])
    )
    async def weapon_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.selected_weapons = select.values
        if len(self.selected_weapons) == 1:
            embed = create_weapon_package_embed(self.selected_weapons[0])
            view = WeaponPackageView(self.selected_weapons)
        else:
            embed = create_multi_weapon_package_embed(self.selected_weapons)
            view = MultiWeaponPackageView(self.selected_weapons)
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
        if len(self.weapons) == 1:
            embed = create_order_confirmation_embed(self.weapons[0], "safe")
        else:
            embed = create_multi_order_confirmation_embed(self.weapons, "safe")
        view = OrderConfirmationView()
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label='Bag Package - $2.00', style=discord.ButtonStyle.success)
    async def bag_package(self, interaction: discord.Interaction, button: discord.ui.Button):
        if len(self.weapons) == 1:
            embed = create_order_confirmation_embed(self.weapons[0], "bag")
        else:
            embed = create_multi_order_confirmation_embed(self.weapons, "bag")
        view = OrderConfirmationView()
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label='Trunk Package - $1.00', style=discord.ButtonStyle.secondary)
    async def trunk_package(self, interaction: discord.Interaction, button: discord.ui.Button):
        if len(self.weapons) == 1:
            embed = create_order_confirmation_embed(self.weapons[0], "trunk")
        else:
            embed = create_multi_order_confirmation_embed(self.weapons, "trunk")
        view = OrderConfirmationView()
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label='Back', style=discord.ButtonStyle.danger)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_weapons_embed(), view=WeaponsView())

class MultiWeaponPackageView(discord.ui.View):
    def __init__(self, weapons):
        super().__init__(timeout=300)
        self.weapons = weapons

    @discord.ui.button(label='Safe Package - $3.00 each', style=discord.ButtonStyle.primary)
    async def safe_package(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = create_multi_order_confirmation_embed(self.weapons, "safe")
        view = OrderConfirmationView()
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label='Bag Package - $2.00 each', style=discord.ButtonStyle.success)
    async def bag_package(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = create_multi_order_confirmation_embed(self.weapons, "bag")
        view = OrderConfirmationView()
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label='Trunk Package - $1.00 each', style=discord.ButtonStyle.secondary)
    async def trunk_package(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = create_multi_order_confirmation_embed(self.weapons, "trunk")
        view = OrderConfirmationView()
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label='Back', style=discord.ButtonStyle.danger)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_weapons_embed(), view=WeaponsView())

class MoneyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label='💵 Regular Money - $1.00', style=discord.ButtonStyle.primary)
    async def regular_money(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = create_order_confirmation_embed("Max Money 990k", "money", 1.00)
        view = OrderConfirmationView()
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label='🏦 Regular Bank - $1.00', style=discord.ButtonStyle.primary)
    async def regular_bank(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = create_order_confirmation_embed("Max Bank 990k", "money", 1.00)
        view = OrderConfirmationView()
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label='💎 Gamepass Money - $2.00', style=discord.ButtonStyle.success)
    async def gamepass_money(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = create_order_confirmation_embed("Max Money 1.6M (Extra Money Pass)", "money", 2.00)
        view = OrderConfirmationView()
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label='💳 Gamepass Bank - $2.00', style=discord.ButtonStyle.success)
    async def gamepass_bank(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = create_order_confirmation_embed("Max Bank 1.6M (Extra Bank Pass)", "money", 2.00)
        view = OrderConfirmationView()
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label='Back to Shop', style=discord.ButtonStyle.secondary, emoji='🏠')
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_main_shop_embed(), view=MainShopView())

class WatchesView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.select(
        placeholder="Choose a watch...",
        options=[discord.SelectOption(label=watch, value=watch, emoji="⌚") for watch in WATCHES]
    )
    async def watch_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        selected_watch = select.values[0]
        embed = create_order_confirmation_embed(selected_watch, "watch", 1.00)
        view = OrderConfirmationView()
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label='Back to Shop', style=discord.ButtonStyle.secondary, emoji='🏠')
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_main_shop_embed(), view=MainShopView())

class CartView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label='📞 Contact Support', style=discord.ButtonStyle.primary)
    async def contact_support(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="📞 Contact STK Supply",
            description="Ready to place your order? Contact us:",
            color=0x00FF00
        )
        embed.add_field(name="Discord", value="STK Supply#1234", inline=True)
        embed.add_field(name="Website", value="stksupply.com", inline=True)
        embed.add_field(name="Email", value="orders@stksupply.com", inline=True)
        view = OrderConfirmationView()
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label='Back to Shop', style=discord.ButtonStyle.secondary, emoji='🏠')
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_main_shop_embed(), view=MainShopView())

class OrderConfirmationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label='Confirm Order', style=discord.ButtonStyle.success, emoji='✅')
    async def confirm_order(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="Order Confirmed!",
            description="Thank you for your order! Contact STK Supply to complete payment.",
            color=0x00FF00
        )
        embed.add_field(name="Next Steps", value="1. Contact STK Supply\n2. Provide order details\n3. Complete payment\n4. Receive your items!", inline=False)
        view = OrderConfirmationView()
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label='Back to Shop', style=discord.ButtonStyle.primary, emoji='🏠')
    async def back_to_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_main_shop_embed(), view=MainShopView())

    @discord.ui.button(label='Order Another', style=discord.ButtonStyle.secondary, emoji='🛒')
    async def order_another(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=create_main_shop_embed(), view=MainShopView())

# Embed creation functions
def create_main_shop_embed():
    embed = discord.Embed(
        title="🛒 STK Supply - Interactive Shop",
        description="Welcome to STK Supply! Click the buttons below to browse our premium collection:",
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
    embed.set_footer(text="STK Supply | Click buttons to navigate")
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
    embed.set_footer(text="Select a weapon from the dropdown below")
    return embed

def create_weapon_package_embed(weapon):
    embed = discord.Embed(
        title=f"🔫 {weapon}",
        description=f"Selected weapon: **{weapon}** (FREE)\nChoose your package:",
        color=0x4ECDC4
    )
    embed.add_field(
        name="Package Options",
        value="🔒 Safe Package - Premium security - $3.00\n🎒 Bag Package - Standard security - $2.00\n📦 Trunk Package - Basic security - $1.00",
        inline=False
    )
    embed.set_footer(text="Click a package button below")
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

def create_cart_embed():
    embed = discord.Embed(
        title="🛒 Order Information",
        description="Ready to place an order? Here's how:",
        color=0xFDCB6E
    )
    embed.add_field(
        name="📝 Order Process",
        value="1. Browse our products using the buttons\n2. Select your items\n3. Contact STK Supply\n4. Complete payment\n5. Receive your items!",
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
    embed.set_footer(text="Contact us to complete your order!")
    return embed

def create_multi_weapon_package_embed(weapons):
    embed = discord.Embed(
        title=f"Selected Weapons ({len(weapons)})",
        description=f"You've selected **{len(weapons)} weapons** (all FREE). Choose your package option:",
        color=0x4ECDC4
    )
    
    weapons_list = "\n".join([f"🔫 {weapon}" for weapon in weapons])
    embed.add_field(
        name="Selected Weapons",
        value=weapons_list if len(weapons_list) < 1000 else f"{weapons_list[:900]}...\n+{len(weapons)-weapons_list[:900].count('🔫')} more",
        inline=False
    )
    
    embed.add_field(
        name="Package Options (per weapon)",
        value="🔒 Safe Package - Premium security - $3.00\n🎒 Bag Package - Standard security - $2.00\n📦 Trunk Package - Basic security - $1.00",
        inline=False
    )
    
    embed.set_footer(text="Total cost = Package price × Number of weapons")
    return embed

def create_multi_order_confirmation_embed(weapons, package_type):
    pkg_info = PACKAGES[package_type]
    total_price = pkg_info['price'] * len(weapons)
    
    embed = discord.Embed(
        title="Order Summary",
        description="Review your multi-weapon order below:",
        color=0x95E1D3
    )
    
    weapons_list = "\n".join([f"🔫 {weapon} (FREE)" for weapon in weapons])
    embed.add_field(
        name=f"Weapons ({len(weapons)})",
        value=weapons_list if len(weapons_list) < 1000 else f"{weapons_list[:900]}...\n+{len(weapons)-weapons_list[:900].count('🔫')} more",
        inline=False
    )
    
    embed.add_field(name="Package", value=f"{pkg_info['emoji']} {pkg_info['name']}", inline=True)
    embed.add_field(name="Quantity", value=f"{len(weapons)} packages", inline=True)
    embed.add_field(name="Total", value=f"**${total_price:.2f}**", inline=True)
    
    embed.set_footer(text="Click 'Confirm Order' to proceed or 'Back to Shop' to continue browsing")
    return embed

def create_order_confirmation_embed(item, item_type, price=None):
    if item_type in PACKAGES:
        pkg_info = PACKAGES[item_type]
        total_price = pkg_info['price']
        embed = discord.Embed(
            title="Order Summary",
            description="Review your order below:",
            color=0x95E1D3
        )
        embed.add_field(name="Weapon", value=f"🔫 {item} (FREE)", inline=True)
        embed.add_field(name="Package", value=f"{pkg_info['emoji']} {pkg_info['name']}", inline=True)
        embed.add_field(name="Total", value=f"**${total_price:.2f}**", inline=True)
    else:
        embed = discord.Embed(
            title="Order Summary",
            description="Review your order below:",
            color=0x95E1D3
        )
        if item_type == "money":
            embed.add_field(name="Item", value=f"💰 {item}", inline=True)
            embed.add_field(name="Total", value=f"**${price:.2f}**", inline=True)
        elif item_type == "watch":
            embed.add_field(name="Watch", value=f"⌚ {item}", inline=True)
            embed.add_field(name="Total", value=f"**${price:.2f}**", inline=True)

    embed.set_footer(text="Click 'Confirm Order' to proceed or 'Back to Shop' to continue browsing")
    return embed

def create_custom_shop_embed(shop_name, shop_description, categories):
    embed = discord.Embed(
        title=f"🏪 {shop_name}",
        description=shop_description or f"Welcome to {shop_name}! Browse our categories below:",
        color=0x9B59B6
    )
    
    if categories:
        category_list = "\n".join([f"{cat['emoji']} **{cat['name']}** - {len(cat['products'])} items" for cat in categories])
        embed.add_field(
            name="📂 Categories",
            value=category_list,
            inline=False
        )
    else:
        embed.add_field(
            name="📂 Categories",
            value="No categories available",
            inline=False
        )
    
    embed.set_footer(text=f"{shop_name} | Custom Shop")
    return embed

def create_custom_category_embed(category):
    embed = discord.Embed(
        title=f"{category['emoji']} {category['name']}",
        description=f"Browse {category['name']} products below:",
        color=0x3498DB
    )
    
    if category['products']:
        product_list = "\n".join([
            f"🛍️ **{product['name']}** - ${product['price']:.2f}" 
            for product in category['products'][:10]
        ])
        
        if len(category['products']) > 10:
            product_list += f"\n... and {len(category['products']) - 10} more items"
            
        embed.add_field(
            name="🛒 Available Products",
            value=product_list,
            inline=False
        )
    else:
        embed.add_field(
            name="🛒 Products",
            value="No products in this category",
            inline=False
        )
    
    embed.set_footer(text="Select a product from the dropdown below")
    return embed

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} slash commands')
    except Exception as e:
        print(f'Failed to sync commands: {e}')

    print(f'{bot.user} has connected to Discord!')
    print('Interactive Shop bot is ready!')

# Slash Commands
@bot.tree.command(name='shop', description='Open the interactive shop with buttons')
async def shop_slash(interaction: discord.Interaction):
    """Open the main interactive shop"""
    embed = create_main_shop_embed()
    view = MainShopView()
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name='setup', description='Set up the shop bot in this channel')
async def setup_slash(interaction: discord.Interaction):
    """Setup command for the shop bot"""
    embed = discord.Embed(
        title="🛠️ STK Supply Interactive Shop Setup!",
        description="The interactive shop bot has been successfully set up!",
        color=0x00FF00
    )

    embed.add_field(
        name="🚀 Getting Started",
        value="Use `/shop` to open the interactive shop with buttons!",
        inline=False
    )

    embed.add_field(
        name="✨ Features",
        value="• Button-based navigation\n• Dropdown menus for products\n• Interactive order system\n• Real-time confirmations",
        inline=False
    )

    embed.set_footer(text="STK Supply | Interactive Shop Experience")

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='create_shop', description='Create a custom shop with your own products')
async def create_shop(interaction: discord.Interaction, shop_name: str, shop_description: str = "Custom Shop"):
    """Create a custom shop builder"""
    embed = discord.Embed(
        title="🛠️ Custom Shop Builder",
        description=f"Building shop: **{shop_name}**\n{shop_description}",
        color=0x9B59B6
    )
    
    embed.add_field(
        name="📝 Instructions",
        value="Use the buttons below to add categories and products to your shop:",
        inline=False
    )
    
    embed.add_field(
        name="🏗️ Shop Status",
        value="🔸 No categories added yet\n🔸 Ready to customize",
        inline=False
    )
    
    embed.set_footer(text="Custom Shop Builder | Click buttons to add content")
    
    view = CustomShopBuilderView(shop_name, shop_description)
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name='my_shops', description='View and manage your saved custom shops')
async def my_shops(interaction: discord.Interaction):
    """View user's saved custom shops"""
    user_shops = {k: v for k, v in custom_shops.items() if v['owner'] == interaction.user.id}
    
    if not user_shops:
        embed = discord.Embed(
            title="📭 No Shops Found",
            description="You haven't created any custom shops yet!\n\nUse `/create_shop` to build your first shop.",
            color=0xE67E22
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    embed = discord.Embed(
        title="🏪 Your Custom Shops",
        description=f"You have **{len(user_shops)}** saved shops:",
        color=0x9B59B6
    )
    
    for shop_id, shop_data in user_shops.items():
        categories_count = len(shop_data['categories'])
        total_products = sum(len(cat['products']) for cat in shop_data['categories'])
        
        embed.add_field(
            name=f"🏪 {shop_data['name']}",
            value=f"📂 {categories_count} categories\n🛍️ {total_products} products\nID: `{shop_id}`",
            inline=True
        )
    
    embed.set_footer(text="Use the buttons below to open your shops")
    
    view = MyShopsView(user_shops)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class MyShopsView(discord.ui.View):
    def __init__(self, user_shops):
        super().__init__(timeout=300)
        self.user_shops = user_shops
        
        # Add buttons for each shop (max 5 due to Discord limits)
        for i, (shop_id, shop_data) in enumerate(list(user_shops.items())[:5]):
            button = discord.ui.Button(
                label=shop_data['name'][:15],  # Truncate long names
                style=discord.ButtonStyle.primary,
                emoji='🏪',
                custom_id=f"open_shop_{i}"
            )
            button.callback = self.create_shop_callback(shop_id, shop_data)
            self.add_item(button)
    
    def create_shop_callback(self, shop_id, shop_data):
        async def callback(interaction: discord.Interaction):
            embed = create_custom_shop_embed(shop_data['name'], shop_data['description'], shop_data['categories'])
            view = CustomShopView(shop_data['name'], shop_data['categories'])
            await interaction.response.send_message(embed=embed, view=view)
        return callback

# Legacy prefix command for backwards compatibility
@bot.command(name='shop')
async def shop_legacy(ctx):
    """Legacy shop command - redirects to interactive version"""
    embed = discord.Embed(
        title="🔄 Upgraded Shop Experience!",
        description="The shop has been upgraded to an interactive button-based system!",
        color=0x00FF00
    )
    embed.add_field(
        name="🆕 How to Use",
        value="Use `/shop` instead for the new interactive experience with buttons and dropdowns!",
        inline=False
    )
    await ctx.send(embed=embed)

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