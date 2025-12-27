import asyncio
import logging
import sys
import traceback
from datetime import datetime
import discord
from discord.ext import commands, tasks
import os
from flask import Flask
from threading import Thread
from pymongo import MongoClient

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Load environment
TOKEN = os.getenv('DISCORD_TOKEN')
OWNER_ID = int(os.getenv('BOT_OWNER_ID', '1232586090532306966'))
MONGO_URI = os.getenv('MONGO_URI')
VOICE_CHANNELS = [int(x.strip()) for x in os.getenv('VOICE_CHANNEL_IDS', '').split(',') if x.strip()]
PORT = int(os.getenv('PORT', '10000'))

# Flask app for keep-alive
app = Flask(__name__)

@app.route('/')
def home():
    return 'Digamber UPI Bot is running'

@app.route('/health')
def health():
    return 'OK', 200

def run_flask():
    app.run(host='0.0.0.0', port=PORT, debug=False, threaded=True)

# Start Flask in thread
flask_thread = Thread(target=run_flask, daemon=True)
flask_thread.start()
logger.info(f"✅ Flask server started on port {PORT}")

class DigamberUPIBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        intents.members = True
        
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None,
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="Digamber Payment Channels 24/7"
            ),
            status=discord.Status.dnd
        )
        
        self.owner_id = OWNER_ID
        self.db = None
        self.mongo_client = None
        self.voice_channels = VOICE_CHANNELS
        self.start_time = datetime.now()
        self.brand_name = "Digamber"
        
    async def setup_hook(self):
        try:
            # MongoDB connection
            logger.info("Connecting to MongoDB...")
            self.mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            self.mongo_client.admin.command('ping')
            self.db = self.mongo_client.digamber_upi_bot
            logger.info("✅ MongoDB connected")
            
            # Create collections if not exists
            collections = self.db.list_collection_names()
            if 'users' not in collections:
                self.db.create_collection('users')
                self.db.users.create_index('user_id', unique=True)
            
            if 'upi_records' not in collections:
                self.db.create_collection('upi_records')
                self.db.upi_records.create_index('user_id')
            
            # Load cogs
            await self.load_extension('cogs.admin')
            await self.load_extension('cogs.setup')
            await self.load_extension('cogs.voice')
            logger.info("✅ Cogs loaded")
            
            # Sync commands
            await self.tree.sync()
            logger.info("✅ Commands synced")
            
            # Start background tasks
            self.monitor_voice_channels.start()
            self.cleanup_channels.start()
            
        except Exception as e:
            logger.error(f"❌ Setup error: {e}")
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
                        if "Already connected" not in str(e):
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
        logger.info(f"✅ {self.brand_name} Bot ready as {self.user}")
        logger.info(f"📊 Servers: {len(self.guilds)}")
        
        # Connect to voice channels
        for guild in self.guilds:
            for channel_id in self.voice_channels:
                channel = guild.get_channel(channel_id)
                if channel:
                    try:
                        if not guild.voice_client:
                            await channel.connect()
                    except:
                        pass

bot = DigamberUPIBot()

if __name__ == "__main__":
    try:
        bot.run(TOKEN)
    except Exception as e:
        logger.error(f"Bot failed to start: {e}")
        traceback.print_exc()
