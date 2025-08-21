from flask import Flask, render_template, request, jsonify
import discord
from discord.ext import commands
import asyncio
import threading
import os
from datetime import datetime
import json
import uuid # Import uuid for unique embed IDs

# Import your Discord bot
from discord_bot import bot, CHANNELS, create_support_embed, create_gang_embed, create_main_shop_embed, create_tos_embed, create_rules_embed, create_news_embed, create_welcome_embed, create_reminder_embed, SupportView, GangRecruitmentView, MainShopView, VerificationView, check_channel_permissions

app = Flask(__name__)

# Load saved embeds from a file, or initialize an empty list
EMBEDS_FILE = 'saved_embeds.json'
SAVED_EMBEDS = []

def load_embeds_from_file():
    global SAVED_EMBEDS
    if os.path.exists(EMBEDS_FILE):
        with open(EMBEDS_FILE, 'r') as f:
            try:
                SAVED_EMBEDS = json.load(f)
            except json.JSONDecodeError:
                SAVED_EMBEDS = [] # Handle empty or invalid JSON file
    else:
        SAVED_EMBEDS = []

def save_embeds_to_file():
    with open(EMBEDS_FILE, 'w') as f:
        json.dump(SAVED_EMBEDS, f, indent=4)

# Load embeds when the application starts
load_embeds_from_file()

def run_bot():
    """Run the Discord bot in a separate thread"""
    try:
        TOKEN = os.getenv('DISCORD_BOT_TOKEN')
        if TOKEN:
            bot.run(TOKEN)
        else:
            print("❌ DISCORD_BOT_TOKEN not found in environment variables")
    except Exception as e:
        print(f"❌ Error running bot: {e}")

# Start Discord bot in background thread
bot_thread = threading.Thread(target=run_bot, daemon=True)
bot_thread.start()

@app.route('/')
def index():
    return render_template('embed_spawner.html')

@app.route('/spawn_embed', methods=['POST'])
def spawn_embed():
    try:
        data = request.get_json()
        embed_type = data.get('embed_type')
        channel_id = data.get('channel_id')

        if not embed_type or not channel_id:
            return jsonify({'error': 'Missing embed_type or channel_id'}), 400

        # Run the spawn function asynchronously
        asyncio.run_coroutine_threadsafe(
            spawn_embed_async(embed_type, int(channel_id)),
            bot.loop
        )

        return jsonify({'success': True, 'message': f'{embed_type} spawned successfully!'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/create_custom_embed', methods=['POST'])
def create_custom_embed():
    try:
        data = request.get_json()
        channel_id = data.get('channel_id')
        title = data.get('title')
        description = data.get('description')
        color = data.get('color', '7289da')
        embed_name = data.get('embed_name') # Name for saving the embed

        if not channel_id:
            return jsonify({'error': 'Missing channel_id'}), 400

        # Run the custom embed function asynchronously
        asyncio.run_coroutine_threadsafe(
            create_custom_embed_async(int(channel_id), title, description, color),
            bot.loop
        )

        # Save the custom embed if a name is provided
        if embed_name:
            embed_data = {
                'id': str(uuid.uuid4()), # Generate a unique ID
                'name': embed_name,
                'title': title,
                'description': description,
                'color': color
            }
            SAVED_EMBEDS.append(embed_data)
            save_embeds_to_file()

        return jsonify({'success': True, 'message': 'Custom embed created successfully!'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

async def spawn_embed_async(embed_type, channel_id):
    """Spawn embed in the specified channel"""
    try:
        channel = bot.get_channel(channel_id)
        if not channel:
            print(f"❌ Channel {channel_id} not found")
            return

        if not check_channel_permissions(channel):
            print(f"❌ No permissions in channel {channel.name}")
            return

        if embed_type == 'support':
            embed = create_support_embed()
            view = SupportView()
            await channel.send(embed=embed, view=view)
        elif embed_type == 'gang':
            embed = create_gang_embed()
            view = GangRecruitmentView()
            await channel.send(embed=embed, view=view)
        elif embed_type == 'shop':
            embed = create_main_shop_embed()
            view = MainShopView()
            await channel.send(embed=embed, view=view)
        elif embed_type == 'tos':
            embed = create_tos_embed()
            await channel.send(embed=embed)
        elif embed_type == 'rules':
            embed = create_rules_embed()
            await channel.send(embed=embed)
        elif embed_type == 'news':
            embed = create_news_embed()
            await channel.send(embed=embed)
        elif embed_type == 'welcome':
            embed = create_welcome_embed()
            await channel.send(embed=embed)
        elif embed_type == 'reminder':
            embed = create_reminder_embed()
            await channel.send(embed=embed)
        elif embed_type == 'verification':
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
            await channel.send(embed=embed, view=view)

        print(f"✅ {embed_type} spawned in #{channel.name}")
    except Exception as e:
        print(f"❌ Error spawning {embed_type}: {e}")

async def create_custom_embed_async(channel_id, title, description, color):
    """Create a custom embed in the specified channel"""
    try:
        channel = bot.get_channel(channel_id)
        if not channel:
            print(f"❌ Channel {channel_id} not found")
            return

        if not check_channel_permissions(channel):
            print(f"❌ No permissions in channel {channel.name}")
            return

        # Convert hex color to int
        try:
            color_int = int(color, 16) if color else 0x7289da
        except ValueError:
            color_int = 0x7289da

        embed = discord.Embed(
            title=title or "Custom Embed",
            description=description or "No description provided.",
            color=color_int,
            timestamp=datetime.now()
        )
        embed.set_footer(text="ZSells Custom Embed Creator")

        await channel.send(embed=embed)
        print(f"✅ Custom embed sent to #{channel.name}")
    except Exception as e:
        print(f"❌ Error creating custom embed: {e}")

@app.route('/get_guilds')
def get_guilds():
    try:
        from discord_bot import GUILD_ANALYSIS, get_channels_by_name, analyze_guild_structure

        guilds_data = []
        for guild in bot.guilds:
            # Get or create analysis for this guild
            if guild.id not in GUILD_ANALYSIS:
                analysis = analyze_guild_structure(guild)
                GUILD_ANALYSIS[guild.id] = analysis
            else:
                analysis = GUILD_ANALYSIS[guild.id]

            # Get auto-detected channels
            detected_channels = analysis['channels']['detected_channels']

            channels_data = []
            # Add detected channels first with special marking
            for channel_type, channel_id in detected_channels.items():
                channel = guild.get_channel(channel_id)
                if channel:
                    channels_data.append({
                        'id': channel.id,
                        'name': channel.name,
                        'permissions': check_channel_permissions(channel),
                        'detected_type': channel_type,
                        'auto_detected': True
                    })

            # Add remaining channels
            for channel in guild.text_channels:
                # Skip if already added as detected
                if channel.id not in [ch['id'] for ch in channels_data]:
                    channels_data.append({
                        'id': channel.id,
                        'name': channel.name,
                        'permissions': check_channel_permissions(channel),
                        'detected_type': None,
                        'auto_detected': False
                    })

            guilds_data.append({
                'id': guild.id,
                'name': guild.name,
                'member_count': guild.member_count,
                'channels': channels_data,
                'detected_channels': detected_channels,
                'total_detected': len(detected_channels)
            })

        return jsonify({'guilds': guilds_data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/refresh_detection', methods=['POST'])
def refresh_detection():
    try:
        from discord_bot import GUILD_ANALYSIS, analyze_guild_structure

        data = request.get_json()
        guild_id = data.get('guild_id')

        if guild_id:
            # Refresh specific guild
            guild = bot.get_guild(int(guild_id))
            if guild:
                analysis = analyze_guild_structure(guild)
                GUILD_ANALYSIS[guild.id] = analysis
                return jsonify({
                    'success': True,
                    'message': f'Detection refreshed for {guild.name}',
                    'detected_count': len(analysis['channels']['detected_channels'])
                })
            else:
                return jsonify({'error': 'Guild not found'}), 404
        else:
            # Refresh all guilds
            GUILD_ANALYSIS.clear()
            total_detected = 0
            for guild in bot.guilds:
                analysis = analyze_guild_structure(guild)
                GUILD_ANALYSIS[guild.id] = analysis
                total_detected += len(analysis['channels']['detected_channels'])

            return jsonify({
                'success': True,
                'message': f'Detection refreshed for all servers',
                'total_detected': total_detected
            })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_saved_embeds')
def get_saved_embeds():
    """Get all saved embeds"""
    try:
        return jsonify({'embeds': SAVED_EMBEDS})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/spawn_saved_embed', methods=['POST'])
def spawn_saved_embed():
    """Spawn a saved embed"""
    try:
        data = request.get_json()
        embed_id = data.get('embed_id')
        channel_id = data.get('channel_id')

        if not embed_id or not channel_id:
            return jsonify({'error': 'Missing embed_id or channel_id'}), 400

        # Find the saved embed
        saved_embed = None
        for embed in SAVED_EMBEDS:
            if embed['id'] == embed_id: # Compare with string ID
                saved_embed = embed
                break

        if not saved_embed:
            return jsonify({'error': 'Saved embed not found'}), 404

        # Run the spawn function asynchronously
        asyncio.run_coroutine_threadsafe(
            create_custom_embed_async(
                int(channel_id),
                saved_embed.get('title'), # Use .get for safety
                saved_embed.get('description'),
                saved_embed.get('color', '7289da') # Default color if not present
            ),
            bot.loop
        )

        return jsonify({'success': True, 'message': f'Saved embed "{saved_embed["name"]}" spawned successfully!'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/delete_saved_embed', methods=['POST'])
def delete_saved_embed():
    """Delete a saved embed"""
    try:
        data = request.get_json()
        embed_id = data.get('embed_id')

        if not embed_id:
            return jsonify({'error': 'Missing embed_id'}), 400

        global SAVED_EMBEDS
        initial_len = len(SAVED_EMBEDS)
        SAVED_EMBEDS = [embed for embed in SAVED_EMBEDS if embed['id'] != embed_id] # Compare with string ID

        if len(SAVED_EMBEDS) < initial_len:
            save_embeds_to_file()
            return jsonify({'success': True, 'message': 'Embed deleted successfully!'})
        else:
            return jsonify({'error': 'Embed not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)