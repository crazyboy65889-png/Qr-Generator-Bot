from motor.motor_asyncio import AsyncIOMotorClient
import os
import datetime
import logging
from typing import Optional, Dict, Any
from utils.encryption import EncryptionManager

logger = logging.getLogger('UPIManager')

class UltimateUPIManager:
    """Ultimate UPI data manager with encryption and caching"""
    
    def __init__(self, mongo_client: AsyncIOMotorClient, encryption: EncryptionManager):
        self.client = mongo_client
        self.db = self.client[os.getenv('MONGO_DB_NAME', 'upi_bot')]
        self.users_collection = self.db['users']
        self.analytics_collection = self.db['analytics']
        self.cache = {}  # Simple in-memory cache
        self.encryption = encryption
    
    async def initialize(self):
        """Initialize collections and indexes"""
        await self.users_collection.create_index([('user_id', 1)], unique=True)
        await self.users_collection.create_index([('upi_id', 1)])
        await self.analytics_collection.create_index([('timestamp', 1)], expireAfterSeconds=2592000)  # 30 days
        logger.info("✅ UPIManager initialized")
    
    async def save_upi(
        self,
        user_id: str,
        upi_id: str,
        name: str,
        note: Optional[str] = None,
        encrypt: bool = True
    ) -> Dict[str, Any]:
        """
        Save UPI data with encryption support
        
        Returns: {
            'success': bool,
            'document_id': str,
            'warnings': list
        }
        """
        try:
            # Prepare document
            document = {
                'user_id': user_id,
                'upi_id': upi_id,
                'name': name,
                'note': note,
                'last_updated': datetime.datetime.utcnow(),
                'created_at': datetime.datetime.utcnow(),
                'usage_count': 0
            }
            
            # Encrypt sensitive data
            if encrypt:
                encrypted = self.encryption.encrypt_dict({
                    'upi_id': upi_id,
                    'name': name,
                    'note': note
                })
                document.update(encrypted)
            
            # Increment usage count
            existing = await self.get_upi(user_id, decrypt=False)
            if existing:
                document['usage_count'] = existing.get('usage_count', 0) + 1
                document['created_at'] = existing.get('created_at', document['created_at'])
            
            # Upsert to database
            result = await self.users_collection.update_one(
                {'user_id': user_id},
                {'$set': document},
                upsert=True
            )
            
            # Update cache
            self.cache[user_id] = document
            
            # Log analytics
            await self.analytics_collection.insert_one({
                'event_type': 'upi_saved',
                'timestamp': datetime.datetime.utcnow(),
                'user_id': user_id,
                'encrypted': encrypt
            })
            
            logger.info(f"💾 UPI data saved for user {user_id}")
            
            return {
                'success': True,
                'document_id': str(result.upserted_id) if result.upserted_id else None,
                'warnings': []
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to save UPI: {e}")
            return {
                'success': False,
                'document_id': None,
                'warnings': [str(e)]
            }
    
    async def get_upi(self, user_id: str, decrypt: bool = True) -> Optional[Dict[str, Any]]:
        """
        Get UPI data with optional decryption
        
        Returns: Decrypted document or None
        """
        try:
            # Check cache first
            if user_id in self.cache:
                cached = self.cache[user_id]
                # Return copy to prevent mutation
                return cached.copy() if not decrypt else self.encryption.decrypt_dict(cached)
            
            # Fetch from database
            document = await self.users_collection.find_one({'user_id': user_id})
            if not document:
                return None
            
            # Update cache
            self.cache[user_id] = document
            
            # Decrypt if needed
            if decrypt:
                return self.encryption.decrypt_dict(document)
            
            return document
            
        except Exception as e:
            logger.error(f"❌ Failed to get UPI: {e}")
            return None
    
    async def delete_upi(self, user_id: str, permanent: bool = False) -> bool:
        """
        Delete UPI data
        
        Args:
            user_id: User ID to delete
            permanent: If True, permanently delete. If False, soft delete.
        
        Returns: Success status
        """
        try:
            if permanent:
                result = await self.users_collection.delete_one({'user_id': user_id})
            else:
                result = await self.users_collection.update_one(
                    {'user_id': user_id},
                    {
                        '$set': {
                            'deleted': True,
                            'deleted_at': datetime.datetime.utcnow()
                        }
                    }
                )
            
            # Clear cache
            if user_id in self.cache:
                del self.cache[user_id]
            
            # Log
            logger.info(f"🗑️ UPI data {'permanently' if permanent else 'soft'} deleted for user {user_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to delete UPI: {e}")
            return False
    
    async def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Get user statistics"""
        try:
            user_data = await self.get_upi(user_id, decrypt=False)
            if not user_data:
                return {'found': False}
            
            analytics = await self.analytics_collection.count_documents({
                'user_id': user_id,
                'event_type': 'qr_generated'
            })
            
            return {
                'found': True,
                'usage_count': user_data.get('usage_count', 0),
                'qr_generated': analytics,
                'last_used': user_data.get('last_updated'),
                'created_at': user_data.get('created_at')
            }
        except Exception as e:
            logger.error(f"❌ Failed to get user stats: {e}")
            return {'found': False, 'error': str(e)}
    
    async def get_global_stats(self) -> Dict[str, Any]:
        """Get global statistics"""
        try:
            total_users = await self.users_collection.count_documents({'deleted': {'$ne': True}})
            total_qr_generated = await self.analytics_collection.count_documents({'event_type': 'qr_generated'})
            total_upi_saved = await self.analytics_collection.count_documents({'event_type': 'upi_saved'})
            
            return {
                'total_users': total_users,
                'total_qr_generated': total_qr_generated,
                'total_upi_saved': total_upi_saved,
                'database_size_mb': await self.get_database_size()
            }
        except Exception as e:
            logger.error(f"❌ Failed to get global stats: {e}")
            return {'error': str(e)}
    
    async def get_database_size(self) -> float:
        """Get database size in MB"""
        try:
            stats = await self.db.command('dbStats')
            return stats.get('dataSize', 0) / 1024 / 1024
        except:
            return 0
    
    def clear_cache(self, user_id: str = None):
        """Clear cache for user or all"""
        if user_id:
            self.cache.pop(user_id, None)
        else:
            self.cache.clear()
        logger.info(f"🧹 Cache cleared{' for ' + user_id if user_id else ''}")
      
