import os
from dotenv import load_dotenv

load_dotenv()

# Discord Settings
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
BOT_OWNER_ID = int(os.getenv('BOT_OWNER_ID', '1232586090532306966'))

# MongoDB
MONGO_URI = os.getenv('MONGO_URI')

# Voice Channels
VOICE_CHANNEL_IDS = [int(vid.strip()) for vid in os.getenv('VOICE_CHANNEL_IDS', '').split(',') if vid.strip()]

# Encryption
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', 'X7z9Qp3rLs8vNm2aBf4cKd5eWj6hGy1u')

# Settings
MAX_TEMP_CHANNELS_PER_USER = 3
TEMP_CHANNEL_COOLDOWN = 30
COMMAND_COOLDOWN = 20
RATE_LIMIT_PER_MINUTE = 5
TEMP_CHANNEL_USER_LIMIT = 2

# UPI Providers
VALID_UPI_PROVIDERS = {
    'okaxis', 'okicici', 'oksbi', 'okhdfc', 'okbob', 'axisbank', 
    'barodampay', 'citi', 'flexipay', 'hdfcbank', 'icici', 
    'kotak', 'paytm', 'phonepe', 'sbi', 'upi', 'ybl', 'ibl'
}
