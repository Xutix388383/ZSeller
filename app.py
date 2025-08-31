
import os
import subprocess
import sys

def main():
    """Run the Discord bot"""
    print("🤖 Starting Fresh Discord Bot...")
    
    # Check if Discord token is available
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        print("❌ DISCORD_BOT_TOKEN not found in environment variables")
        print("Please add your Discord bot token to the Secrets tab.")
        return
    
    try:
        # Run the Discord bot
        subprocess.run([sys.executable, "discord_bot.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running Discord bot: {e}")
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()
