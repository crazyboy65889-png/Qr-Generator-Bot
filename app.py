import asyncio
import logging
import sys
import traceback
from datetime import datetime
import discord
from discord.ext import commands, tasks
from pymongo import MongoClient
import os
import time
import base64
from io import BytesIO
import qrcode
from flask import Flask
from threading import Thread

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment
TOKEN = os.getenv('DISCORD_TOKEN')
OWNER_ID = int(os.getenv('BOT_OWNER_ID', '1232586090532306966'))
MONGO_URI = os.getenv('MONGO_URI')
VOICE_CHANNELS = [int(x.strip()) for x in os.getenv('VOICE_CHANNEL_IDS', '').split(',') if x.strip()]
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', 'X7z9Qp3rLs8vNm2aBf4cKd5eWj6hGy1u')
PORT = int(os.getenv('PORT', '10000'))

# Flask app for keep-alive
app = Flask(__name__)

@app.route('/')
def home():
    return 'Bot is running'

@app.route('/health')
def health():
    return 'OK', 200

def run_flask():
    app.run(host='0.0.0.0', port=PORT)

# Start Flask in thread
Thread(target=run_flask, daemon=True).start()
logger.info(f"Flask server started on port {PORT}")

class UPI_Bot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        intents.members = True
        
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None,
            activity=discord.Activity(type=discord.ActivityType.watching, name="Payment Channels 24/7"),
            status=discord.Status.dnd
        )
        
        self.owner_id = OWNER_ID
        self.db = None
        self.voice_channels = VOICE_CHANNELS
        self.start_time = datetime.now()
        self.user_cooldowns = {}
        
    async def setup_hook(self):
        try:
            # MongoDB
            client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            client.admin.command('ping')
            self.db = client.upi_bot
            
            # Create collections
            if 'upi_records' not in self.db.list_collection_names():
                self.db.create_collection('upi_records')
            
            logger.info("✅ MongoDB connected")
            
            # Load commands
            await self.load_extension('cogs.admin')
            await self.load_extension('cogs.setup')
            await self.load_extension('cogs.voice')
            logger.info("✅ Cogs loaded")
            
            # Start tasks
            self.monitor_voice_channels.start()
            self.cleanup_channels.start()
            
        except Exception as e:
            logger.error(f"Setup error: {e}")
            traceback.print_exc()
    
    @tasks.loop(seconds=300)
    async def monitor_voice_channels(self):
        if not self.is_ready():
            return
            
        for guild in self.guilds:
            for channel_id in self.voice_channels:
                channel = guild.get_channel(channel_id)
                if channel and isinstance(channel, discord.VoiceChannel):
                    try:
                        if not guild.voice_client or not guild.voice_client.is_connected():
                            await channel.connect()
                            logger.info(f"✅ Connected to {channel.name}")
                    except Exception as e:
                        logger.error(f"Voice error: {e}")
    
    @tasks.loop(seconds=30)
    async def cleanup_channels(self):
        if not self.is_ready():
            return
            
        for guild in self.guilds:
            for channel in guild.voice_channels:
                if channel.name.startswith("💰 ") and len(channel.members) == 0:
                    try:
                        await channel.delete()
                    except:
                        pass
    
    async def on_ready(self):
        logger.info(f"✅ Bot ready as {self.user}")
        
        # Connect to voice channels
        for guild in self.guilds:
            for channel_id in self.voice_channels:
                channel = guild.get_channel(channel_id)
                if channel:
                    try:
                        await channel.connect()
                        logger.info(f"✅ Joined {channel.name}")
                    except:
                        pass
    
    async def on_voice_state_update(self, member, before, after):
        if member.bot:
            return
        
        # User joined monitored channel
        if after.channel and after.channel.id in self.voice_channels:
            # Check cooldown
            if member.id in self.user_cooldowns:
                if time.time() - self.user_cooldowns[member.id] < 30:
                    try:
                        await member.move_to(None)
                    except:
                        pass
                    return
            
            # Create temp channel
            try:
                temp_channel = await after.channel.category.create_voice_channel(
                    name=f"💰 {member.display_name}'s Payment",
                    user_limit=2,
                    overwrites={
                        after.channel.guild.default_role: discord.PermissionOverwrite(connect=False),
                        member: discord.PermissionOverwrite(connect=True),
                        after.channel.guild.me: discord.PermissionOverwrite(connect=True, manage_channels=True)
                    }
                )
                await member.move_to(temp_channel)
                self.user_cooldowns[member.id] = time.time()
            except Exception as e:
                logger.error(f"Temp channel error: {e}")
        
        # Clean empty temp channels
        if before.channel and before.channel.name.startswith("💰 ") and len(before.channel.members) == 0:
            await asyncio.sleep(5)
            if before.channel and len(before.channel.members) == 0:
                try:
                    await before.channel.delete()
                except:
                    pass

# Create bot
bot = UPI_Bot()

# Add commands directly
@bot.tree.command(name="setup", description="Create UPI QR code")
async def setup_command(interaction: discord.Interaction, upi_id: str, name: str, amount: float, note: str = "", color: str = "blue"):
    await interaction.response.defer(ephemeral=True)
    
    # Check voice channel
    if not interaction.user.voice:
        await interaction.followup.send("🎤 Join a voice channel first!", ephemeral=True)
        return
    
    try:
        # Generate QR
        upi_url = f"upi://pay?pa={upi_id}&pn={name}&am={amount}&tn={note}&cu=INR"
        qr = qrcode.make(upi_url)
        img_bytes = BytesIO()
        qr.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        # Save to DB
        bot.db.upi_records.insert_one({
            'user_id': interaction.user.id,
            'upi_id': upi_id,
            'name': name,
            'amount': amount,
            'note': note,
            'color': color,
            'created_at': datetime.now()
        })
        
        # Send QR
        file = discord.File(img_bytes, filename="qr.png")
        embed = discord.Embed(title="✅ QR Generated", description=f"Amount: ₹{amount}", color=discord.Color.green())
        embed.set_image(url="attachment://qr.png")
        await interaction.followup.send(embed=embed, file=file, ephemeral=True)
        
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)

@bot.tree.command(name="myupi", description="View your UPI records")
async def myupi_command(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    records = list(bot.db.upi_records.find({'user_id': interaction.user.id}).limit(10))
    
    if not records:
        await interaction.followup.send("📭 No records found", ephemeral=True)
        return
    
    embed = discord.Embed(title="📋 Your UPI Records", color=discord.Color.blue())
    for i, rec in enumerate(records, 1):
        embed.add_field(name=f"#{i} - ₹{rec['amount']}", value=f"UPI: {rec['upi_id']}", inline=False)
    
    await interaction.followup.send(embed=embed, ephemeral=True)

@bot.tree.command(name="botstats", description="Bot statistics (Owner only)")
async def botstats_command(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("⛔ Owner only", ephemeral=True)
        return
    
    await interaction.response.defer()
    
    uptime = datetime.now() - bot.start_time
    uptime_str = str(uptime).split('.')[0]
    
    embed = discord.Embed(title="🤖 Bot Stats", color=discord.Color.blue())
    embed.add_field(name="Uptime", value=uptime_str)
    embed.add_field(name="Servers", value=str(len(bot.guilds)))
    embed.add_field(name="Users", value=str(sum(g.member_count or 0 for g in bot.guilds)))
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="cleanup", description="Clean empty channels (Owner only)")
async def cleanup_command(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("⛔ Owner only", ephemeral=True)
        return
    
    await interaction.response.defer()
    
    deleted = 0
    for guild in bot.guilds:
        for channel in guild.voice_channels:
            if channel.name.startswith("💰 ") and len(channel.members) == 0:
                try:
                    await channel.delete()
                    deleted += 1
                except:
                    pass
    
    await interaction.followup.send(f"🧹 Deleted {deleted} channels")

# Run bot
if __name__ == "__main__":
    bot.run(TOKEN)
