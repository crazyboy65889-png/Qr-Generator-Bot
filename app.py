#!/usr/bin/env python3
"""
UPI Discord Bot - ULTIMATE EDITION v3.0
Owner ID: 1232586090532306966
Support Server: https://discord.gg/5bFnXdUp8U
Encryption: AES-256 Enabled
"""

import discord
from discord.ext import commands, tasks
import os
import sys
import signal
import asyncio
import psutil
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from keep_alive import keep_alive
from config.settings import BotConfig
from config.constants import Constants
from utils.logger import setup_master_logger
from utils.encryption import EncryptionManager
import traceback
import gc
import aiohttp

# Setup master logger
logger = setup_master_logger()

# Load environment
load_dotenv()

# Global shutdown flag
shutdown_event = asyncio.Event()

class UltimateUPIBot(commands.Bot):
    """ULTIMATE UPI Discord Bot - Production Ready"""
    
    def __init__(self):
        super().__init__(
            command_prefix=commands.when_mentioned_or('!'),
            intents=BotConfig.INTENTS,
            help_command=None,
            case_insensitive=True,
            strip_after_prefix=True,
            max_messages=10000,
            chunk_guilds_at_startup=False,
            owner_id=BotConfig.OWNER_ID
        )
        
        # Core managers
        self.mongo_client = None
        self.db = None
        self.users_collection = None
        self.analytics_collection = None
        self.temp_channels_collection = None
        
        self.encryption = EncryptionManager(os.getenv('ENCRYPTION_KEY'))
        self.upi_manager = None
        
        # State management
        self.temp_channels = {}
        self.user_cooldowns = {}
        self.guild_rate_limits = {}
        
        # Bot metrics
        self.start_time = datetime.utcnow()
        self.commands_processed = 0
        self.qr_generated = 0
        self.errors_logged = 0
        
        logger.info("🤖 Ultimate Bot instance created")
    
    async def setup_hook(self):
        """Ultimate setup with all features"""
        try:
            logger.info("🚀 Starting ULTIMATE bot setup...")
            
            # Validate config
            validation_errors = BotConfig.validate()
            if validation_errors:
                logger.critical(f"❌ Config validation failed: {validation_errors}")
                sys.exit(1)
            
            # Connect to MongoDB
            await self._initialize_database()
            
            # Initialize UPI Manager
            from utils.upi_manager import UltimateUPIManager
            self.upi_manager = UltimateUPIManager(self.mongo_client, self.encryption)
            await self.upi_manager.initialize()
            
            # Load all cogs
            await self._load_all_cogs()
            
            # Sync commands
            await self._sync_commands()
            
            # Start background tasks
            await self._start_background_tasks()
            
            # Set bot presence
            await self._set_bot_presence()
            
            # Initialize web dashboard
            if BotConfig.ENABLE_DASHBOARD:
                from web.dashboard import Dashboard
                self.dashboard = Dashboard(self)
            
            logger.info("✅ ULTIMATE bot setup completed!")
            logger.info(f"👑 Bot Owner: {self.owner_id}")
            logger.info(f"💬 Support Server: {Constants.SUPPORT_SERVER}")
            
        except Exception as e:
            logger.critical(f"❌ Setup failed: {e}")
            traceback.print_exc()
            sys.exit(1)
    
    async def _initialize_database(self):
        """Initialize MongoDB with connection pooling"""
        try:
            self.mongo_client = AsyncIOMotorClient(
                os.getenv('MONGO_URI'),
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000,
                maxPoolSize=100,
                minPoolSize=10
            )
            
            # Test connection
            await self.mongo_client.admin.command('ping')
            
            # Setup database
            self.db = self.mongo_client[os.getenv('MONGO_DB_NAME', 'upi_bot')]
            self.users_collection = self.db['users']
            self.analytics_collection = self.db['analytics']
            self.temp_channels_collection = self.db['temp_channels']
            
            # Create indexes
            await self._create_indexes()
            
            logger.info("✅ Database initialized with indexes")
            
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            raise
    
    async def _create_indexes(self):
        """Create performance indexes"""
        indexes = [
            self.users_collection.create_index([('user_id', 1)], unique=True),
            self.users_collection.create_index([('upi_id', 1)]),
            self.analytics_collection.create_index([('timestamp', 1)]),
            self.analytics_collection.create_index([('user_id', 1)]),
            self.temp_channels_collection.create_index([('channel_id', 1)], unique=True),
            self.temp_channels_collection.create_index([('created_at', 1)], expireAfterSeconds=7200)
        ]
        await asyncio.gather(*indexes)
    
    async def _load_all_cogs(self):
        """Load all cogs"""
        cog_list = [
            'cogs.setup',
            'cogs.admin',
            'cogs.analytics',
            'cogs.voice_manager'
        ]
        
        loaded = 0
        for cog in cog_list:
            try:
                await self.load_extension(cog)
                logger.info(f"✅ Loaded cog: {cog}")
                loaded += 1
            except Exception as e:
                logger.error(f"❌ Failed to load cog {cog}: {e}")
                self.errors_logged += 1
        
        logger.info(f"📦 Cogs loaded: {loaded}/{len(cog_list)}")
    
    async def _sync_commands(self):
        """Sync slash commands"""
        try:
            synced = await self.tree.sync()
            logger.info(f"🔄 Synced {len(synced)} slash commands globally")
        except Exception as e:
            logger.error(f"❌ Command sync failed: {e}")
            self.errors_logged += 1
    
    async def _start_background_tasks(self):
        """Start all background tasks"""
        self.monitor_voice_channels.start()
        self.cleanup_temp_channels.start()
        self.update_analytics.start()
        self.health_check.start()
        logger.info("🔄 Background tasks started")
    
    async def _set_bot_presence(self):
        """Set DND status"""
        await self.change_presence(
            status=discord.Status.dnd,
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=BotConfig.BOT_ACTIVITY
            )
        )
        logger.info("🔴 Bot status set to DND")
    
    async def on_ready(self):
        """Bot ready event"""
        logger.info("=" * 60)
        logger.info("🤖 ULTIMATE UPI BOT IS READY!")
        logger.info("=" * 60)
        logger.info(f"    Username: {self.user}")
        logger.info(f"    ID: {self.user.id}")
        logger.info(f"    Guilds: {len(self.guilds)}")
        logger.info(f"    Users: {sum(g.member_count for g in self.guilds)}")
        logger.info(f"    Owner ID: {BotConfig.OWNER_ID}")
        logger.info(f"    Support: {Constants.SUPPORT_SERVER}")
        logger.info("=" * 60)
        
        # Log voice channels
        for guild in self.guilds:
            for channel_id in BotConfig.VOICE_CHANNEL_IDS:
                channel = guild.get_channel(channel_id)
                if channel:
                    logger.info(f"🔊 Monitoring: {channel.name} in {guild.name}")
    
    async def on_guild_join(self, guild: discord.Guild):
        """Guild join event"""
        logger.info(f"📥 Joined: {guild.name} ({guild.id}) | {guild.member_count} members")
        await self.log_to_analytics('guild_join', {'guild_id': str(guild.id)})
    
    async def on_guild_remove(self, guild: discord.Guild):
        """Guild leave event"""
        logger.info(f"📤 Left: {guild.name} ({guild.id})")
        await self.log_to_analytics('guild_leave', {'guild_id': str(guild.id)})
    
    async def on_voice_state_update(self, member, before, after):
        """Voice state update handler"""
        try:
            if member.bot:
                return
            
            # Check cooldown
            if self.is_user_rate_limited(member.id):
                try:
                    await member.send("⚠️ Please wait before joining again!")
                except:
                    pass
                return
            
            # Handle join
            if after.channel and after.channel.id in BotConfig.VOICE_CHANNEL_IDS:
                logger.info(f"👤 {member.name} joined monitored channel")
                await self.create_temp_channel(member, after.channel)
            
            # Handle leave
            if before.channel and before.channel.id in self.temp_channels:
                await self.cleanup_temp_channel(before.channel)
                
        except Exception as e:
            logger.error(f"Voice update error: {e}")
            self.errors_logged += 1
    
    async def create_temp_channel(self, member, base_channel):
        """Create temp channel"""
        try:
            from cogs.voice_manager import VoiceManager
            voice_cog = self.get_cog('VoiceManager')
            if voice_cog:
                await voice_cog.create_temp_channel(member, base_channel)
        except Exception as e:
            logger.error(f"Temp channel creation failed: {e}")
    
    async def cleanup_temp_channel(self, channel):
        """Cleanup temp channel"""
        try:
            from cogs.voice_manager import VoiceManager
            voice_cog = self.get_cog('VoiceManager')
            if voice_cog:
                await voice_cog.cleanup_temp_channel(channel)
        except Exception as e:
            logger.error(f"Temp channel cleanup failed: {e}")
    
    @tasks.loop(minutes=5)
    async def monitor_voice_channels(self):
        """Monitor voice channels"""
        try:
            for guild in self.guilds:
                for channel_id in BotConfig.VOICE_CHANNEL_IDS:
                    channel = guild.get_channel(channel_id)
                    if not channel:
                        continue
                    
                    existing_vc = next((vc for vc in self.voice_clients if vc.channel.id == channel_id), None)
                    
                    if not existing_vc:
                        await channel.connect(timeout=5.0)
                        logger.info(f"🔊 Connected to {channel.name}")
                    elif not existing_vc.is_connected():
                        await existing_vc.disconnect()
                        await channel.connect(timeout=5.0)
                        logger.info(f"🔄 Reconnected to {channel.name}")
        
        except Exception as e:
            logger.error(f"Voice monitoring error: {e}")
            self.errors_logged += 1
    
    @tasks.loop(hours=1)
    async def cleanup_temp_channels(self):
        """Cleanup old channels"""
        try:
            now = datetime.utcnow()
            cleaned = 0
            
            for channel_id, data in list(self.temp_channels.items()):
                if now - data['created_at'] > timedelta(hours=BotConfig.TEMP_CHANNEL_MAX_AGE_HOURS):
                    guild = self.get_guild(data['guild_id'])
                    if guild:
                        channel = guild.get_channel(channel_id)
                        if channel:
                            await channel.delete(reason="Auto-cleanup: Expired")
                            cleaned += 1
                    del self.temp_channels[channel_id]
            
            if cleaned > 0:
                logger.info(f"🧹 Cleaned {cleaned} expired channels")
                
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
            self.errors_logged += 1
    
    @tasks.loop(minutes=30)
    async def update_analytics(self):
        """Update analytics"""
        try:
            uptime = datetime.utcnow() - self.start_time
            doc = {
                'event_type': 'bot_metrics',
                'timestamp': datetime.utcnow(),
                'commands_processed': self.commands_processed,
                'qr_generated': self.qr_generated,
                'errors_logged': self.errors_logged,
                'temp_channels': len(self.temp_channels),
                'voice_connections': len(self.voice_clients),
                'guilds': len(self.guilds),
                'uptime_hours': uptime.total_seconds() / 3600,
                'memory_mb': psutil.Process().memory_info().rss / 1024 / 1024
            }
            
            await self.analytics_collection.insert_one(doc)
            
            # Cleanup old data
            cutoff = datetime.utcnow() - timedelta(days=BotConfig.ANALYTICS_RETENTION_DAYS)
            await self.analytics_collection.delete_many({'timestamp': {'$lt': cutoff}})
            
        except Exception as e:
            logger.error(f"Analytics error: {e}")
    
    @tasks.loop(minutes=10)
    async def health_check(self):
        """Health check"""
        try:
            await self.mongo_client.admin.command('ping')
            
            memory = psutil.Process().memory_info().rss / 1024 / 1024
            if memory > 500:
                logger.warning(f"High memory: {memory:.1f}MB")
                gc.collect()
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            self.errors_logged += 1
    
    async def log_to_analytics(self, event_type: str, data: dict):
        """Log to analytics"""
        try:
            if not BotConfig.ENABLE_ANALYTICS:
                return
            
            await self.analytics_collection.insert_one({
                'event_type': event_type,
                'timestamp': datetime.utcnow(),
                'data': data
            })
        except Exception as e:
            logger.warning(f"Analytics logging failed: {e}")
    
    def is_user_rate_limited(self, user_id: int) -> bool:
        """Check rate limit"""
        # Implementation in voice manager
        return False
    
    def get_bot_stats(self) -> dict:
        """Get comprehensive stats"""
        uptime = datetime.utcnow() - self.start_time
        return {
            'uptime_seconds': uptime.total_seconds(),
            'commands_processed': self.commands_processed,
            'qr_generated': self.qr_generated,
            'errors_logged': self.errors_logged,
            'temp_channels': len(self.temp_channels),
            'voice_connections': len(self.voice_clients),
            'guilds': len(self.guilds),
            'memory_mb': psutil.Process().memory_info().rss / 1024 / 1024
        }

# Create bot instance
bot = UltimateUPIBot()

# Graceful shutdown
def graceful_shutdown(sig, frame):
    logger.info(f"🛑 Shutdown signal: {signal.Signals(sig).name}")
    asyncio.create_task(shutdown())

async def shutdown():
    try:
        logger.info("🌙 Shutting down gracefully...")
        
        # Stop tasks
        bot.monitor_voice_channels.stop()
        bot.cleanup_temp_channels.stop()
        bot.update_analytics.stop()
        bot.health_check.stop()
        
        # Disconnect voice
        for vc in bot.voice_clients:
            await vc.disconnect()
            logger.info(f"🔇 Disconnected from {vc.channel.name}")
        
        # Close MongoDB
        bot.mongo_client.close()
        
        # Clear cache
        if hasattr(bot, 'upi_manager'):
            bot.upi_manager.clear_cache()
        
        logger.info("✅ Shutdown complete")
        await bot.close()
    except Exception as e:
        logger.error(f"Shutdown error: {e}")
        sys.exit(1)

signal.signal(signal.SIGINT, graceful_shutdown)
signal.signal(signal.SIGTERM, graceful_shutdown)

# Keep alive
keep_alive()

# Run bot
if __name__ == "__main__":
    try:
        logger.info("=" * 60)
        logger.info("🚀 ULTIMATE UPI BOT v3.0 - STARTING...")
        logger.info(f"👑 Owner ID: {BotConfig.OWNER_ID}")
        logger.info(f"💬 Support: {Constants.SUPPORT_SERVER}")
        logger.info("=" * 60)
        
        bot.run(os.getenv('DISCORD_TOKEN'), reconnect=True, log_level=logging.WARNING)
    except Exception as e:
        logger.critical(f"❌ FATAL ERROR: {e}")
        traceback.print_exc()
        sys.exit(1)
