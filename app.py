import asyncio
import logging
import sys
import traceback
from datetime import datetime, timezone
import discord
from discord.ext import commands, tasks
from motor.motor_asyncio import AsyncIOMotorClient
from keep_alive import keep_alive
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Bot configuration
TOKEN = os.getenv('DISCORD_TOKEN')
BOT_OWNER_ID = int(os.getenv('BOT_OWNER_ID', '1232586090532306966'))
MONGO_URI = os.getenv('MONGO_URI')
VOICE_CHANNEL_IDS = [int(vid.strip()) for vid in os.getenv('VOICE_CHANNEL_IDS', '').split(',') if vid.strip()]
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', 'X7z9Qp3rLs8vNm2aBf4cKd5eWj6hGy1u')

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
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="Payment Channels 24/7"
            ),
            status=discord.Status.dnd
        )
        
        self.owner_id = BOT_OWNER_ID
        self.mongo_client = None
        self.db = None
        self.voice_channels = VOICE_CHANNEL_IDS
        self.start_time = datetime.now(timezone.utc)
        self.user_temp_channels = {}
        self.user_cooldowns = {}
        
    async def setup_hook(self):
        """Initialize bot components"""
        try:
            # Connect to MongoDB
            logger.info("Connecting to MongoDB...")
            self.mongo_client = AsyncIOMotorClient(MONGO_URI)
            await self.mongo_client.admin.command('ping')
            self.db = self.mongo_client.upi_bot
            logger.info("✅ MongoDB connected")
            
            # Create indexes
            await self.db.upi_records.create_index([("user_id", 1), ("upi_id", 1)], unique=True)
            await self.db.upi_records.create_index([("created_at", 1)])
            
            # Load cogs
            await self.load_cogs()
            
            # Start background tasks
            self.monitor_voice_channels.start()
            self.cleanup_empty_channels.start()
            
            logger.info("✅ Bot setup complete")
            
        except Exception as e:
            logger.error(f"❌ Setup failed: {e}")
            traceback.print_exc()
            raise
    
    async def load_cogs(self):
        """Load all cogs"""
        for cog in ['cogs.setup', 'cogs.admin', 'cogs.voice']:
            try:
                await self.load_extension(cog)
                logger.info(f"✅ Loaded cog: {cog}")
            except Exception as e:
                logger.error(f"❌ Failed to load {cog}: {e}")
    
    @tasks.loop(seconds=300)
    async def monitor_voice_channels(self):
        """Ensure bot stays in voice channels"""
        if not self.is_ready():
            return
            
        for guild in self.guilds:
            for channel_id in self.voice_channels:
                try:
                    channel = guild.get_channel(channel_id)
                    if not channel or not isinstance(channel, discord.VoiceChannel):
                        continue
                    
                    # Check if bot is in channel
                    if not any(member.id == self.user.id for member in channel.members):
                        voice_client = guild.voice_client
                        
                        if voice_client and voice_client.channel != channel:
                            await voice_client.disconnect(force=True)
                            await asyncio.sleep(1)
                        
                        await channel.connect(reconnect=True, timeout=30)
                        logger.info(f"✅ Reconnected to voice channel: {channel.name}")
                        
                except Exception as e:
                    logger.error(f"Error monitoring voice channel: {e}")
    
    @tasks.loop(seconds=30)
    async def cleanup_empty_channels(self):
        """Cleanup empty temporary channels"""
        if not self.is_ready():
            return
            
        for guild in self.guilds:
            for channel in guild.channels:
                if isinstance(channel, discord.VoiceChannel) and channel.name.startswith("💰 "):
                    if len(channel.members) == 0:
                        try:
                            await channel.delete()
                            logger.info(f"🗑️ Deleted empty temp channel: {channel.name}")
                        except Exception as e:
                            logger.error(f"Failed to delete channel: {e}")
    
    async def on_ready(self):
        """Called when bot is ready"""
        logger.info(f"✅ Bot is ready! Logged in as {self.user}")
        logger.info(f"📊 Guilds: {len(self.guilds)}")
        
        # Connect to voice channels
        await asyncio.sleep(5)
        for guild in self.guilds:
            for channel_id in self.voice_channels:
                try:
                    channel = guild.get_channel(channel_id)
                    if channel:
                        await channel.connect(reconnect=True, timeout=30)
                        logger.info(f"✅ Joined voice channel: {channel.name}")
                        await asyncio.sleep(1)
                except Exception as e:
                    logger.error(f"Failed to join voice channel: {e}")
    
    async def close(self):
        """Clean shutdown"""
        logger.info("Shutting down bot...")
        for guild in self.guilds:
            if guild.voice_client:
                await guild.voice_client.disconnect(force=True)
        
        if self.mongo_client:
            self.mongo_client.close()
        
        await super().close()

def main():
    keep_alive()
    bot = UPI_Bot()
    
    try:
        bot.run(TOKEN)
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
