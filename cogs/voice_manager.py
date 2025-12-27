import discord
from discord.ext import commands
import datetime
import logging
from typing import Optional

logger = logging.getLogger('VoiceManager')

class VoiceManager(commands.Cog):
    """Advanced voice channel management"""
    
    def __init__(self, bot):
        self.bot = bot
        self.join_cooldowns = {}
    
    @staticmethod
    async def check_temp_channel_access(bot, interaction: discord.Interaction) -> bool:
        """Check if user has access to temp channel"""
        temp_data = bot.temp_channels.get(interaction.channel.id)
        
        if not temp_data:
            embed = discord.Embed(
                title="❌ Invalid Channel",
                description="This command can only be used in temporary payment channels!",
                color=discord.Color.red()
            )
            try:
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except:
                await interaction.followup.send(embed=embed, ephemeral=True)
            return False
        
        # Check ownership
        if temp_data['owner'] != interaction.user.id:
            embed = discord.Embed(
                title="🔒 Access Denied",
                description="Only the channel owner can use commands here!",
                color=discord.Color.red()
            )
            try:
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except:
                await interaction.followup.send(embed=embed, ephemeral=True)
            return False
        
        return True
    
    async def create_temp_channel(
        self,
        member: discord.Member,
        base_channel: discord.VoiceChannel
    ) -> Optional[discord.VoiceChannel]:
        """Create temporary channel for user"""
        try:
            # Check cooldown
            if await self._is_join_cooldown(member.id):
                await member.send("⏱️ Please wait 30 seconds before creating another temp channel!")
                return None
            
            # Check limit
            user_channels = sum(
                1 for data in self.bot.temp_channels.values()
                if data['owner'] == member.id
            )
            
            if user_channels >= int(os.getenv('MAX_TEMP_CHANNELS_PER_USER', 3)):
                await member.send("❌ You've reached the maximum limit of temporary channels!")
                return None
            
            # Create channel
            guild = base_channel.guild
            
            # Permission overwrites
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(connect=False),
                member: discord.PermissionOverwrite(
                    connect=True,
                    speak=True,
                    stream=True,
                    use_voice_activation=True
                ),
                guild.me: discord.PermissionOverwrite(
                    connect=True,
                    manage_channels=True,
                    manage_permissions=True
                )
            }
            
            channel_name = f"💰 {member.name}'s Payment"
            
            temp_channel = await guild.create_voice_channel(
                name=channel_name,
                category=base_channel.category,
                user_limit=2,
                overwrites=overwrites,
                reason=f"Auto-created payment room for {member.name}"
            )
            
            # Store data
            self.bot.temp_channels[temp_channel.id] = {
                'owner': member.id,
                'created_at': datetime.datetime.utcnow(),
                'guild_id': guild.id,
                'base_channel_id': base_channel.id
            }
            
            # Move member
            await member.move_to(temp_channel)
            
            # Update cooldown
            self.join_cooldowns[member.id] = datetime.datetime.utcnow()
            
            logger.info(f"🏠 Created temp channel {temp_channel.name} for {member.name}")
            return temp_channel
            
        except Exception as e:
            logger.error(f"Failed to create temp channel: {e}")
            try:
                await member.send("❌ Failed to create temporary channel. Please try again.")
            except:
                pass
            return None
    
    async def _is_join_cooldown(self, user_id: int) -> bool:
        """Check if user is on join cooldown"""
        if user_id not in self.join_cooldowns:
            return False
        
        cooldown = int(os.getenv('VOICE_COOLDOWN_SECONDS', 30))
        elapsed = (datetime.datetime.utcnow() - self.join_cooldowns[user_id]).total_seconds()
        
        if elapsed < cooldown:
            return True
        
        # Remove from cooldown
        del self.join_cooldowns[user_id]
        return False
    
    async def cleanup_temp_channel(self, channel: discord.VoiceChannel):
        """Cleanup empty temp channel"""
        try:
            if channel.id not in self.bot.temp_channels:
                return
            
            # Check if empty
            if len(channel.members) == 0:
                await channel.delete(reason="Auto-cleanup: Empty temp channel")
                del self.bot.temp_channels[channel.id]
                logger.info(f"🗑️ Deleted empty temp channel {channel.name}")
                
        except Exception as e:
            logger.error(f"Cleanup failed for {channel.name}: {e}")

async def setup(bot):
    await bot.add_cog(VoiceManager(bot))
  
