class Constants:
    """Bot constants"""
    
    # UPI Providers
    VALID_PROVIDERS = {
        'okhdfcbank', 'okaxis', 'oksbi', 'okicici', 'paytm', 'ybl',
        'ibl', 'axl', 'barodampay', 'kaypay', 'cnrb', 'idfcbank',
        'waicici', 'waaxis', 'wahdfcbank', 'wasbi', 'myicici',
        'rbl', 'hdfcbank', 'axisbank', 'icici', 'sbi', 'yesbank',
        'upi', 'myhdfc', 'mysbi', 'myaxis', 'mykotak', 'apl'
    }
    
    # Error Messages
    ERROR_MESSAGES = {
        'invalid_upi': "Invalid UPI ID format! Use: `username@provider`",
        'rate_limited': "You're doing that too fast! Please wait {time} seconds.",
        'no_permission': "❌ You don't have permission to do that!",
        'channel_owner_only': "🔒 Only the channel owner can use this command here!",
        'temp_channel_limit': "❌ You've reached the maximum of {limit} temporary channels!",
        'command_failed': "❌ Command failed due to an unexpected error.",
    }
    
    # Success Messages
    SUCCESS_MESSAGES = {
        'qr_generated': "✅ QR code generated successfully!",
        'upi_saved': "💾 Your UPI ID has been saved securely!",
        'channel_created': "🏠 Temporary payment room created for you!",
    }
    
    # Limits
    MAX_NAME_LENGTH = 50
    MAX_NOTE_LENGTH = 100
    MAX_UPI_LENGTH = 100
    MAX_AMOUNT = 999999.99
    MIN_AMOUNT = 0.01
  
