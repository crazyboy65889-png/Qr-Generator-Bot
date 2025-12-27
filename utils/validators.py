import re
from config.constants import Constants

class UPIValidator:
    """Ultimate UPI ID validator with provider database"""
    
    PROVIDER_PATTERNS = {
        'banks': r'^(ok|wa|my)?[a-z]{3,}bank$',
        'wallets': r'^(paytm|ybl|ibl|axl|apl)$',
        'upi': r'^upi$'
    }
    
    def validate(self, upi_id: str) -> dict:
        """
        Comprehensive UPI validation
        Returns: {'valid': bool, 'error': str, 'warnings': list}
        """
        warnings = []
        
        # Basic checks
        if not upi_id or '@' not in upi_id:
            return {'valid': False, 'error': "UPI ID must contain '@' symbol", 'warnings': []}
        
        parts = upi_id.split('@', 1)
        if len(parts) != 2:
            return {'valid': False, 'error': "Invalid UPI format", 'warnings': []}
        
        username, provider = parts
        
        # Username validation
        username_error = self._validate_username(username)
        if username_error:
            return {'valid': False, 'error': username_error, 'warnings': []}
        
        # Provider validation
        provider_result = self._validate_provider(provider.lower())
        if not provider_result['valid']:
            return {'valid': False, 'error': provider_result['error'], 'warnings': []}
        
        if provider_result.get('warning'):
            warnings.append(provider_result['warning'])
        
        return {'valid': True, 'error': '', 'warnings': warnings}
    
    def _validate_username(self, username: str) -> str:
        """Validate UPI username"""
        if not username:
            return "Username cannot be empty"
        
        if len(username) < 3:
            return "Username must be at least 3 characters"
        
        if len(username) > Constants.MAX_UPI_LENGTH:
            return f"Username too long (max {Constants.MAX_UPI_LENGTH} characters)"
        
        if username.startswith('.') or username.endswith('.'):
            return "Username cannot start or end with dot"
        
        if '..' in username:
            return "Username cannot contain consecutive dots"
        
        # Allowed characters: alphanumeric, dot, underscore, hyphen
        if not re.match(r'^[a-zA-Z0-9._-]+$', username):
            return "Username can only contain letters, numbers, dots, underscores, hyphens"
        
        return None
    
    def _validate_provider(self, provider: str) -> dict:
        """Validate UPI provider"""
        if not provider:
            return {'valid': False, 'error': "Provider cannot be empty"}
        
        if len(provider) < 2:
            return {'valid': False, 'error': "Provider name too short"}
        
        # Check exact matches first
        if provider in Constants.VALID_PROVIDERS:
            return {'valid': True, 'error': ''}
        
        # Check pattern matches
        for pattern in self.PROVIDER_PATTERNS.values():
            if re.match(pattern, provider):
                return {'valid': True, 'error': ''}
        
        # Unknown provider - warning only
        return {
            'valid': True,
            'error': '',
            'warning': f"Unknown provider '{provider}'. Please verify it's correct."
        }

class RateLimiter:
    """Rate limiter for commands"""
    
    def __init__(self, max_requests=5, window=60):
        self.max_requests = max_requests
        self.window = window  # seconds
        self.requests = {}
    
    def is_rate_limited(self, key: str) -> tuple:
        """
        Check if key is rate limited
        Returns: (is_limited: bool, retry_after: int)
        """
        now = datetime.now()
        
        if key not in self.requests:
            self.requests[key] = []
        
        # Clean old requests
        self.requests[key] = [
            req_time for req_time in self.requests[key]
            if now - req_time < timedelta(seconds=self.window)
        ]
        
        if len(self.requests[key]) >= self.max_requests:
            oldest_request = min(self.requests[key])
            retry_after = self.window - int((now - oldest_request).total_seconds())
            return True, retry_after
        
        return False, 0
    
    def add_request(self, key: str):
        """Add request to rate limiter"""
        if key not in self.requests:
            self.requests[key] = []
        self.requests[key].append(datetime.now())

class CooldownManager:
    """User cooldown manager"""
    
    def __init__(self):
        self.cooldowns = {}
    
    def check_cooldown(self, user_id: int, command: str, duration: int) -> tuple:
        """
        Check cooldown for command
        Returns: (on_cooldown: bool, remaining: int)
        """
        key = f"{user_id}:{command}"
        
        if key not in self.cooldowns:
            return False, 0
        
        last_used = self.cooldowns[key]
        now = datetime.now()
        elapsed = (now - last_used).total_seconds()
        
        if elapsed < duration:
            return True, int(duration - elapsed)
        
        return False, 0
    
    def set_cooldown(self, user_id: int, command: str):
        """Set cooldown for user and command"""
        key = f"{user_id}:{command}"
        self.cooldowns[key] = datetime.now()
          
