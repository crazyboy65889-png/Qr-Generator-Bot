import discord
import os

class BotConfig:
    """Centralized bot configuration"""
    
    # Discord Intents
    INTENTS = discord.Intents(
        guilds=True,
        members=True,
        voice_states=True,
        message_content=True,
        presences=False,
    )
    
    # Environment Variables
    TOKEN = os.getenv('DISCORD_TOKEN')
    MONGO_URI = os.getenv('MONGO_URI')
    VOICE_CHANNEL_IDS = [
        int(id.strip()) for id in os.getenv('VOICE_CHANNEL_IDS', '').split(',') if id.strip()
    ]
    ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', '').encode()
    
    # Rate Limiting
    MAX_COMMANDS_PER_MINUTE = int(os.getenv('MAX_COMMANDS_PER_MINUTE', 5))
    MAX_TEMP_CHANNELS_PER_USER = int(os.getenv('MAX_TEMP_CHANNELS_PER_USER', 3))
    VOICE_COOLDOWN_SECONDS = int(os.getenv('VOICE_COOLDOWN_SECONDS', 30))
    
    # Bot Behavior
    BOT_STATUS = os.getenv('BOT_STATUS', 'dnd')
    BOT_ACTIVITY = os.getenv('BOT_ACTIVITY', 'Payment Channels 24/7')
    
    # Cleanup
    AUTO_CLEANUP_HOURS = int(os.getenv('AUTO_CLEANUP_HOURS', 1))
    TEMP_CHANNEL_MAX_AGE_HOURS = int(os.getenv('TEMP_CHANNEL_MAX_AGE_HOURS', 2))
    
    # Analytics
    ENABLE_ANALYTICS = os.getenv('ENABLE_ANALYTICS', 'true').lower() == 'true'
    ANALYTICS_RETENTION_DAYS = int(os.getenv('ANALYTICS_RETENTION_DAYS', 30))
    
    # Web Dashboard
    ENABLE_DASHBOARD = os.getenv('ENABLE_DASHBOARD', 'true').lower() == 'true'
    DASHBOARD_PASSWORD = os.getenv('DASHBOARD_PASSWORD')
    PORT = int(os.getenv('PORT', 10000))
    HOST = os.getenv('HOST', '0.0.0.0')
    
    # Validation
    @staticmethod
    def validate():
        """Validate configuration"""
        errors = []
        if not BotConfig.TOKEN:
            errors.append("DISCORD_TOKEN is missing")
        if not BotConfig.MONGO_URI:
            errors.append("MONGO_URI is missing")
        if not BotConfig.VOICE_CHANNEL_IDS:
            errors.append("VOICE_CHANNEL_IDS is missing")
        if len(BotConfig.ENCRYPTION_KEY) not in [0, 32]:
            errors.append("ENCRYPTION_KEY must be exactly 32 characters or empty")
        
        return errors
