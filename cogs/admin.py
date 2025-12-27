import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    async def is_owner(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.bot.owner_id
    
    @app_commands.command(name="botstats", description="View bot statistics (Owner only)")
    async def botstats_command(self, interaction: discord.Interaction):
        if not await self.is_owner(interaction):
            await interaction.response.send_message("⛔ Owner only.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            uptime = datetime.now() - self.bot.start_time
            days = uptime.days
            hours, remainder = divmod(uptime.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            if days > 0:
                uptime_str = f"{days}d {hours}h {minutes}m"
            elif hours > 0:
                uptime_str = f"{hours}h {minutes}m {seconds}s"
            else:
                uptime_str = f"{minutes}m {seconds}s"
            
            total_records = self.bot.db.upi_records.count_documents({})
            total_servers = len(self.bot.guilds)
            total_users = sum(g.member_count or 0 for g in self.bot.guilds)
            
            temp_channels = 0
            voice_users = 0
            for guild in self.bot.guilds:
                for channel in guild.voice_channels:
                    if channel.name.startswith("💰 "):
                        temp_channels += 1
                        voice_users += len(channel.members)
            
            embed = discord.Embed(
                title="🤖 Bot Statistics",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            embed.add_field(name="⏱️ Uptime", value=uptime_str, inline=True)
            embed.add_field(name="🏢 Servers", value=str(total_servers), inline=True)
            embed.add_field(name="👥 Total Users", value=str(total_users), inline=True)
            embed.add_field(name="💾 UPI Records", value=str(total_records), inline=True)
            embed.add_field(name="🎤 Temp Channels", value=str(temp_channels), inline=True)
            embed.add_field(name="🔊 Voice Users", value=str(voice_users), inline=True)
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}")
    
    @app_commands.command(name="tempchannels", description="List all temporary channels (Owner only)")
    async def tempchannels_command(self, interaction: discord.Interaction):
        if not await self.is_owner(interaction):
            await interaction.response.send_message("⛔ Owner only.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        temp_channels = []
        for guild in self.bot.guilds:
            for channel in guild.voice_channels:
                if channel.name.startswith("💰 "):
                    temp_channels.append({
                        'name': channel.name,
                        'guild': guild.name,
                        'users': len(channel.members),
                        'id': channel.id
                    })
        
        if not temp_channels:
            await interaction.followup.send("📭 No temporary channels active.")
            return
        
        embed = discord.Embed(
            title="📋 Temporary Channels",
            color=discord.Color.orange(),
            timestamp=datetime.now()
        )
        
        for i, channel in enumerate(temp_channels[:10], 1):
            embed.add_field(
                name=f"#{i} {channel['name']}",
                value=f"**Guild:** {channel['guild']}\n**Users:** {channel['users']}\n**ID:** {channel['id']}",
                inline=False
            )
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="cleanup", description="Force cleanup of empty temp channels (Owner only)")
    async def cleanup_command(self, interaction: discord.Interaction):
        if not await self.is_owner(interaction):
            await interaction.response.send_message("⛔ Owner only.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        deleted = 0
        for guild in self.bot.guilds:
            for channel in guild.voice_channels:
                if channel.name.startswith("💰 ") and len(channel.members) == 0:
                    try:
                        await channel.delete()
                        deleted += 1
                    except:
                        pass
        
        await interaction.followup.send(f"🧹 Cleaned up {deleted} empty temporary channels.")
    
    @app_commands.command(name="broadcast", description="Broadcast message to temp channels (Owner only)")
    @app_commands.describe(message="Message to broadcast")
    async def broadcast_command(self, interaction: discord.Interaction, message: str):
        if not await self.is_owner(interaction):
            await interaction.response.send_message("⛔ Owner only.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        sent = 0
        for guild in self.bot.guilds:
            for channel in guild.voice_channels:
                if channel.name.startswith("💰 ") and len(channel.members) > 0:
                    try:
                        await channel.send(f"📢 **Broadcast from {interaction.user.display_name}:** {message}")
                        sent += 1
                    except:
                        pass
        
        await interaction.followup.send(f"📢 Message sent to {sent} channels.")
    
    @app_commands.command(name="botrestart", description="Restart the bot (Owner only)")
    async def botrestart_command(self, interaction: discord.Interaction):
        if not await self.is_owner(interaction):
            await interaction.response.send_message("⛔ Owner only.", ephemeral=True)
            return
        
        await interaction.response.send_message("🔄 Restarting bot...")
        
        import os
        import sys
        os.execl(sys.executable, sys.executable, *sys.argv)

async def setup(bot):
    await bot.add_cog(AdminCog(bot))
