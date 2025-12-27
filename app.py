#!/usr/bin/env python3
"""
Advanced UPI Discord Bot - Ultimate Edition
Copyright (c) 2024. All rights reserved.
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
from utils.logger import setup_master_logger
from utils.encryption import EncryptionManager
import traceback
import gc

# Setup master logger
logger = setup_master_logger()

# Load environment
load_dotenv()

# Global shutdown flag
shutdown_event = asyncio.Event()

class AdvancedUPIBot(commands.Bot):
    """Ultimate UPI Discord Bot with enterprise features"""
    
    def __init__(self):
        super().__init__(
            command_prefix=commands.when_mentioned_or('!'),
            intents=BotConfig.INTENTS,
            help_command=None,
            case_insensitive=True,
            strip_after_prefix=True,
            max_messages=10000,
            chunk_guilds_at_startup=False
        )
        
        # Core managers
        self.mongo_client = None
        self.db = None
        self.users_collection = None
        self.analytics_collection = None
        self.temp_channels_collection = None
        
        self.encryption = EncryptionManager(os.getenv('ENCRYPTION_KEY'))
        
        # State management
        self.temp_channels = {}
        self.user_cooldowns = {}
        self.guild_rate_limits = {}
        
        # Bot metrics
        self.start_time = datetime.utcnow()
        self.commands_processed = 0
        self.qr_generated = 0
        self.errors_logged = 0
        
        logger.info("🤖 Bot instance created successfully")
    
    async def setup_hook(self):
        """Advanced setup with dependency injection"""
        try:
            logger.info("🚀 Starting bot setup...")
            
            # Connect to MongoDB with retry
            await self._initialize_database()
            
            # Load all cogs
            await self._load_all_cogs()
            
            # Sync commands globally
            await self._sync_commands()
            
            # Start background tasks
            await self._start_background_tasks()
            
            # Set bot presence
            await self._set_bot_presence()
            
            # Initialize web dashboard (if enabled)
            if BotConfig.ENABLE_DASHBOARD:
                await self._initialize_web_dashboard()
            
            logger.info("✅ Bot setup completed successfully!")
            
        except Exception as e:
            logger.critical(f"❌ Setup failed: {e}")
            traceback.print_exc()
            sys.exit(1)
    
    async def _initialize_database(self):
        """Initialize MongoDB with indexes"""
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
        """Create MongoDB indexes for performance"""
        indexes = [
            self.users_collection.create_index([('user_id', 1)], unique=True),
            self.analytics_collection.create_index([('timestamp', 1)]),
            self.analytics_collection.create_index([('user_id', 1)]),
            self.temp_channels_collection.create_index([('channel_id', 1)], unique=True),
            self.temp_channels_collection.create_index([('created_at', 1)], expireAfterSeconds=7200)
        ]
        await asyncio.gather(*indexes)
    
    async def _load_all_cogs(self):
        """Load all cogs with error handling"""
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
        """Sync slash commands globally"""
        try:
            synced = await self.tree.sync()
            logger.info(f"🔄 Synced {len(synced)} slash commands globally")
        except Exception as e:
            logger.error(f"❌ Command sync failed: {e}")
            self.errors_logged += 1
    
    async def _start_background_tasks(self):
        """Initialize all background tasks"""
        self.monitor_voice_channels.start()
        self.cleanup_temp_channels.start()
        self.update_analytics.start()
        self.health_check.start()
        logger.info("🔄 Background tasks started")
    
    async def _set_bot_presence(self):
        """Set bot status and activity"""
        await self.change_presence(
            status=discord.Status.dnd,
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=os.getenv('BOT_ACTIVITY', 'Payment Channels 24/7')
            )
        )
        logger.info("🔴 Bot status set to DND")
    
    async def _initialize_web_dashboard(self):
        """Initialize Flask web dashboard"""
        from web.dashboard import Dashboard
        self.dashboard = Dashboard(self)
        logger.info("🌐 Web dashboard initialized")
    
    async def on_ready(self):
        """Called when bot is ready"""
        logger.info("=" * 50)
        logger.info(f"🤖 Bot Ready: {self.user}")
        logger.info(f"    ID: {self.user.id}")
        logger.info(f"    Guilds: {len(self.guilds)}")
        logger.info(f"    Users: {sum(g.member_count for g in self.guilds)}")
        logger.info(f"    Voice Connections: {len(self.voice_clients)}")
        logger.info(f"    Memory Usage: {psutil.Process().memory_info().rss / 1024 / 1024:.1f} MB")
        logger.info("=" * 50)
        
        # Log monitored voice channels
        for guild in self.guilds:
            for channel_id in BotConfig.VOICE_CHANNEL_IDS:
                channel = guild.get_channel(channel_id)
                if channel:
                    logger.info(f"🔊 Monitoring: {channel.name} in {guild.name}")
    
    async def on_guild_join(self, guild: discord.Guild):
        """Log guild join"""
        logger.info(f"📥 Joined guild: {guild.name} ({guild.id}) | Members: {guild.member_count}")
        await self.log_to_analytics('guild_join', {'guild_id': str(guild.id)})
    
    async def on_guild_remove(self, guild: discord.Guild):
        """Log guild leave"""
        logger.info(f"📤 Left guild: {guild.name} ({guild.id})")
        await self.log_to_analytics('guild_leave', {'guild_id': str(guild.id)})
    
    async def on_command_error(self, ctx, error):
        """Global command error handler"""
        self.errors_logged += 1
        logger.error(f"Command error: {error}")
        
        if not isinstance(error, commands.CommandNotFound):
            embed = discord.Embed(
                title="❌ Command Error",
                description=f"```\n{str(error)}\n```",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            try:
                await ctx.send(embed=embed, delete_after=30)
            except:
                pass
    
    async def log_to_analytics(self, event_type: str, data: dict):
        """Log events to analytics"""
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
    
    @tasks.loop(minutes=5)
    async def monitor_voice_channels(self):
        """Advanced voice channel monitoring"""
        try:
            for guild in self.guilds:
                for channel_id in BotConfig.VOICE_CHANNEL_IDS:
                    channel = guild.get_channel(channel_id)
                    if not channel or not isinstance(channel, discord.VoiceChannel):
                        logger.warning(f"Channel {channel_id} not found in {guild.name}")
                        continue
                    
                    # Check connection
                    existing_vc = next((vc for vc in self.voice_clients if vc.channel.id == channel_id), None)
                    
                    if not existing_vc:
                        try:
                            await channel.connect(timeout=5.0)
                            logger.info(f"🔊 Connected to {channel.name}")
                        except Exception as e:
                            logger.error(f"Failed to connect to {channel.name}: {e}")
                            self.errors_logged += 1
                    elif not existing_vc.is_connected():
                        await existing_vc.disconnect()
                        await channel.connect(timeout=5.0)
                        logger.info(f"🔄 Reconnected to {channel.name}")
                    
                    # Check connection health
                    if existing_vc and existing_vc.average_latency > 200:
                        logger.warning(f"High latency in {channel.name}: {existing_vc.average_latency}ms")
        
        except Exception as e:
            logger.error(f"Voice monitoring error: {e}")
            self.errors_logged += 1
    
    @tasks.loop(hours=1)
    async def cleanup_temp_channels(self):
        """Auto-cleanup old temp channels"""
        try:
            now = datetime.utcnow()
            cleaned = 0
            
            for channel_id, data in list(self.temp_channels.items()):
                if now - data['created_at'] > timedelta(hours=BotConfig.TEMP_CHANNEL_MAX_AGE_HOURS):
                    guild = self.get_guild(data['guild_id'])
                    if guild:
                        channel = guild.get_channel(channel_id)
                        if channel:
                            await channel.delete(reason="Auto-cleanup: Channel expired")
                            cleaned += 1
                    del self.temp_channels[channel_id]
            
            if cleaned > 0:
                logger.info(f"🧹 Cleaned up {cleaned} expired temp channels")
                
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
            self.errors_logged += 1
    
    @tasks.loop(minutes=30)
    async def update_analytics(self):
        """Update bot analytics"""
        try:
            uptime = datetime.utcnow() - self.start_time
            doc = {
                'timestamp': datetime.utcnow(),
                'type': 'bot_metrics',
                'commands_processed': self.commands_processed,
                'qr_generated': self.qr_generated,
                'errors_logged': self.errors_logged,
                'temp_channels_active': len(self.temp_channels),
                'voice_connections': len(self.voice_clients),
                'guilds': len(self.guilds),
                'uptime_hours': uptime.total_seconds() / 3600,
                'memory_mb': psutil.Process().memory_info().rss / 1024 / 1024
            }
            
            await self.analytics_collection.insert_one(doc)
            
            # Cleanup old analytics
            cutoff = datetime.utcnow() - timedelta(days=int(os.getenv('ANALYTICS_RETENTION_DAYS', 30)))
            await self.analytics_collection.delete_many({'timestamp': {'$lt': cutoff}})
            
            logger.info(f"📊 Analytics updated - Commands: {self.commands_processed}, QR: {self.qr_generated}")
            
        except Exception as e:
            logger.error(f"Analytics update error: {e}")
    
    @tasks.loop(minutes=10)
    async def health_check(self):
        """Perform health checks"""
        try:
            # Check MongoDB
            await self.mongo_client.admin.command('ping')
            
            # Check memory usage
            memory = psutil.Process().memory_info().rss / 1024 / 1024
            if memory > 500:  # 500MB threshold
                logger.warning(f"High memory usage: {memory:.1f}MB")
                gc.collect()
            
            # Log health
            logger.info(f"❤️ Health OK - Memory: {memory:.1f}MB, Errors: {self.errors_logged}")
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            self.errors_logged += 1
    
    def get_bot_stats(self) -> dict:
        """Get comprehensive bot statistics"""
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
bot = AdvancedUPIBot()

# Signal handlers for graceful shutdown
def graceful_shutdown(sig, frame):
    """Handle shutdown gracefully"""
    logger.info(f"🛑 Shutdown signal received: {signal.Signals(sig).name}")
    asyncio.create_task(shutdown())

async def shutdown():
    """Graceful shutdown"""
    try:
        logger.info("🌙 Starting graceful shutdown...")
        bot.monitor_voice_channels.stop()
        bot.cleanup_temp_channels.stop()
        bot.update_analytics.stop()
        bot.health_check.stop()
        
        # Disconnect from voice channels
        for vc in bot.voice_clients:
            await vc.disconnect()
            logger.info(f"🔇 Disconnected from {vc.channel.name}")
        
        # Close MongoDB
        bot.mongo_client.close()
        
        logger.info("✅ Shutdown completed")
        await bot.close()
    except Exception as e:
        logger.error(f"Shutdown error: {e}")
        sys.exit(1)

signal.signal(signal.SIGINT, graceful_shutdown)
signal.signal(signal.SIGTERM, graceful_shutdown)

# Keep alive for Render
keep_alive()

# Run bot
if __name__ == "__main__":
    try:
        logger.info("=" * 60)
        logger.info("🚀 STARTING UPI DISCORD BOT - ULTIMATE EDITION")
        logger.info("=" * 60)
        bot.run(os.getenv('DISCORD_TOKEN'), reconnect=True, log_level=logging.WARNING)
    except Exception as e:
        logger.critical(f"❌ FATAL ERROR: {e}")
        traceback.print_exc()
        sys.exit(1)
