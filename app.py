import os
from discord_bot import bot

if __name__ == '__main__':
    TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    if TOKEN:
        print("🚀 Starting Discord Bot...")
        bot.run(TOKEN)
    else:
        print("❌ DISCORD_BOT_TOKEN not found in environment variables")
        print("Please add your Discord bot token to the environment variables.")