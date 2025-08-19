
# STK Supply Discord Bot

A Discord bot that displays your shop inventory using rich embed messages. Perfect for showcasing weapons, money packages, and watches with an interactive command system.

## Features

### 🤖 Discord Bot Commands
- `!shop` - Main shop menu with categories
- `!weapons` - Browse weapon selection with packages
- `!money` - View money and bank options
- `!watches` - Browse luxury watch collection
- `!cart` - View order format and contact info
- `!help_shop` - Complete command list

### 🛒 Shop Categories
- **Weapons**: 27+ weapons with 3 package options (Safe $3, Bag $2, Trunk $1)
- **Money**: Regular ($1) and Gamepass ($2) money packages
- **Watches**: 16 luxury watches at $1 each

### 🎨 Rich Embeds
- Professional Discord embed messages
- Color-coded categories
- Emoji icons for visual appeal
- Organized field layouts
- Interactive command system

## Setup Instructions

### 1. Create Discord Bot
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Go to the "Bot" section
4. Create a bot and copy the token
5. Enable "Message Content Intent" in bot settings

### 2. Configure Replit
1. Open the Secrets tab in Replit
2. Add a new secret:
   - Key: `DISCORD_BOT_TOKEN`
   - Value: Your Discord bot token

### 3. Invite Bot to Server
1. In Discord Developer Portal, go to OAuth2 > URL Generator
2. Select scopes: `bot`
3. Select permissions: `Send Messages`, `Use Slash Commands`, `Embed Links`
4. Copy the generated URL and invite the bot to your server

### 4. Run the Bot
```bash
python discord_bot.py
```

## Commands Usage

### Basic Shop Navigation
```
!shop                    # Main menu
!weapons                 # View all weapons
!money                   # View money options
!watches                 # View watch collection
```

### Weapon Selection
```
!weapons                           # Show all weapons
!weapons GoldenButton              # Show packages for GoldenButton
!weapons GoldenButton safe         # Order GoldenButton + Safe Package
```

### Money Packages
```
!money                   # Show all options
!money regular           # Show regular packages ($1)
!money gamepass          # Show gamepass packages ($2)
```

## Customization

### Adding New Products
Edit the arrays in `discord_bot.py`:
- `WEAPONS` - Add new weapon names
- `PACKAGES` - Modify package options and prices
- `MONEY_OPTIONS` - Update money packages
- `WATCHES` - Add new watch models

### Changing Colors
Modify the `color` parameter in embed creation:
```python
embed = discord.Embed(color=0xFF6B6B)  # Red
embed = discord.Embed(color=0x4ECDC4)  # Teal
embed = discord.Embed(color=0x95E1D3)  # Green
```

### Custom Emojis
Replace default emojis with custom server emojis:
```python
"emoji": "<:custom_emoji:123456789>"
```

## Deployment

The bot is ready for deployment on Replit:
1. Set up your Discord bot token in Secrets
2. Click the Deploy button in Replit
3. Choose "Reserved VM" for 24/7 uptime
4. Your bot will stay online continuously

## File Structure

```
├── discord_bot.py      # Main bot code with commands
├── requirements.txt    # Python dependencies
├── README.md          # This documentation
└── .replit            # Replit configuration
```

## Support

For questions or customization help:
- Check Discord.py documentation
- Review the command examples in the code
- Test commands in your Discord server

## License

Free to use for personal and commercial projects.
