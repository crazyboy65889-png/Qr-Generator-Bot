from cryptography.fernet import Fernet
import os
import base64
import hashlib

class EncryptionManager:
    """Advanced encryption for sensitive data"""
    
    def __init__(self, key=None):
        if key and len(key) == 32:
            # FIX: Convert string to bytes before base64 encoding
            self.key = base64.urlsafe_b64encode(key.ljust(32)[:32].encode('utf-8'))
        else:
            self.key = Fernet.generate_key()
        
        self.cipher = Fernet(self.key)
    
    def encrypt(self, data: str) -> str:
        """Encrypt string data"""
        try:
            return self.cipher.encrypt(data.encode()).decode()
        except Exception as e:
            raise Exception(f"Encryption failed: {e}")
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt string data"""
        try:
            return self.cipher.decrypt(encrypted_data.encode()).decode()
        except Exception as e:
            raise Exception(f"Decryption failed: {e}")
    
    def encrypt_dict(self, data_dict: dict) -> dict:
        """Encrypt dictionary values"""
        encrypted = {}
        for key, value in data_dict.items():
            if isinstance(value, str) and value and key in ['upi_id', 'name', 'note']:
                encrypted[key] = self.encrypt(value)
            else:
                encrypted[key] = value
        return encrypted
    
    def decrypt_dict(self, encrypted_dict: dict) -> dict:
        """Decrypt dictionary values"""
        decrypted = {}
        for key, value in encrypted_dict.items():
            if isinstance(value, str) and value and key in ['upi_id', 'name', 'note']:
                try:
                    decrypted[key] = self.decrypt(value)
                except:
                    decrypted[key] = value  # Fallback
            else:
                decrypted[key] = value
        return decrypted
        
