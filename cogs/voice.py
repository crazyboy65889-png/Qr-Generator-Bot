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
        if after.channel and after.channel.id in self.bot.voice_channels:
            current_time = time.time()
            
            # Check cooldown
            if member.id in self.user_cooldowns:
                if current_time - self.user_cooldowns[member.id] < 30:
                    try:
                        await member.move_to(None)
                        await member.send("⏳ Please wait 30 seconds before creating another payment channel.")
                    except:
                        pass
                    return
            
            # Check max temp channels (3 per user)
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
                    await member.send("🚫 You can only have 3 active payment channels at once.")
                except:
                    pass
                return
            
            # Create temp channel
            try:
                guild = after.channel.guild
                temp_channel = await guild.create_voice_channel(
                    name=f"💰 {member.display_name}'s Payment",
                    category=after.channel.category,
                    user_limit=2,
                    overwrites={
                        guild.default_role: discord.PermissionOverwrite(connect=False),
                        member: discord.PermissionOverwrite(connect=True, view_channel=True),
                        guild.me: discord.PermissionOverwrite(connect=True, manage_channels=True, view_channel=True)
                    }
                )
                
                await member.move_to(temp_channel)
                
                # Track channel
                if member.id not in self.user_temp_channels:
                    self.user_temp_channels[member.id] = []
                self.user_temp_channels[member.id].append(temp_channel.id)
                self.user_cooldowns[member.id] = current_time
                
                # Send welcome message
                try:
                    embed = discord.Embed(
                        title="💳 Payment Channel Created",
                        description=f"Welcome {member.mention}!\n\nUse `/setup` to create your payment QR code.\nThis channel will auto-delete when empty.",
                        color=discord.Color.green()
                    )
                    await temp_channel.send(embed=embed)
                except:
                    pass
                    
            except Exception as e:
                print(f"Temp channel error: {e}")
        
        # User left temp channel
        if before.channel and before.channel.name.startswith("💰 "):
            # Wait 5 seconds then check if empty
            await asyncio.sleep(5)
            
            if before.channel and len(before.channel.members) == 0:
                try:
                    await before.channel.delete()
                    # Remove from tracking
                    if member.id in self.user_temp_channels:
                        if before.channel.id in self.user_temp_channels[member.id]:
                            self.user_temp_channels[member.id].remove(before.channel.id)
                except:
                    pass

async def setup(bot):
    await bot.add_cog(VoiceCog(bot))
