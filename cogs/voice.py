import discord
from discord.ext import commands
import asyncio
import time

class VoiceCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_temp_channels = {}
        self.user_cooldowns = {}
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot:
            return
        
        # User joined monitored channel
        if (before.channel != after.channel and 
            after.channel and 
            after.channel.id in self.bot.voice_channels):
            
            # Check cooldown
            current_time = time.time()
            if member.id in self.user_cooldowns:
                if current_time - self.user_cooldowns[member.id] < 30:
                    try:
                        await member.move_to(None)
                    except:
                        pass
                    return
            
            # Check max channels
            user_channels = self.user_temp_channels.get(member.id, [])
            active_channels = []
            for channel_id in user_channels[:]:
                channel = member.guild.get_channel(channel_id)
                if channel and len(channel.members) > 0:
                    active_channels.append(channel_id)
                else:
                    user_channels.remove(channel_id)
            
            if len(active_channels) >= 3:
                try:
                    await member.move_to(None)
                except:
                    pass
                return
            
            # Create temp channel
            try:
                overwrites = {
                    member.guild.default_role: discord.PermissionOverwrite(connect=False),
                    member: discord.PermissionOverwrite(connect=True),
                    member.guild.me: discord.PermissionOverwrite(connect=True, manage_channels=True)
                }
                
                temp_channel = await member.guild.create_voice_channel(
                    name=f"💰 {member.display_name}'s Payment",
                    category=after.channel.category,
                    user_limit=2,
                    overwrites=overwrites
                )
                
                await member.move_to(temp_channel)
                
                # Track channel
                if member.id not in self.user_temp_channels:
                    self.user_temp_channels[member.id] = []
                self.user_temp_channels[member.id].append(temp_channel.id)
                self.user_cooldowns[member.id] = current_time
                
            except Exception as e:
                print(f"Error creating temp channel: {e}")
        
        # User left temp channel
        if (before.channel and 
            before.channel.name.startswith("💰 ") and 
            len(before.channel.members) == 0):
            
            await asyncio.sleep(5)
            if before.channel and len(before.channel.members) == 0:
                try:
                    await before.channel.delete()
                except:
                    pass

async def setup(bot):
    await bot.add_cog(VoiceCog(bot))
