import discord
from discord import app_commands
from discord.ext import commands
import os
import psutil
from datetime import datetime, timezone
import asyncio

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    async def is_owner(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.bot.owner_id
    
    @app_commands.command(name="botstats", description="View bot statistics")
    async def botstats_command(self, interaction: discord.Interaction):
        if not await self.is_owner(interaction):
            await interaction.response.send_message("⛔ Owner only.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            
            uptime = datetime.now(timezone.utc) - self.bot.start_time
            uptime_str = str(uptime).split('.')[0]
            
            # Get stats from database
            total_upi_records = await self.bot.db.upi_records.count_documents({})
            
            embed = discord.Embed(
                title="🤖 Bot Statistics",
                color=discord.Color.blue(),
                timestamp=datetime.now(timezone.utc)
            )
            
            embed.add_field(name="🖥️ System", value=f"**CPU:** {cpu_percent}%\n**RAM:** {memory.percent}%", inline=True)
            embed.add_field(name="📊 Bot", value=f"**Uptime:** {uptime_str}\n**Guilds:** {len(self.bot.guilds)}", inline=True)
            embed.add_field(name="💾 Database", value=f"**UPI Records:** {total_upi_records}", inline=True)
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}")
    
    @app_commands.command(name="tempchannels", description="List all temporary channels")
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
                        'users': len(channel.members)
                    })
        
        if not temp_channels:
            await interaction.followup.send("📭 No temporary channels active.")
            return
        
        embed = discord.Embed(
            title="📋 Temporary Channels",
            color=discord.Color.orange(),
            timestamp=datetime.now(timezone.utc)
        )
        
        for i, channel in enumerate(temp_channels[:10], 1):
            embed.add_field(
                name=f"#{i} {channel['name']}",
                value=f"**Guild:** {channel['guild']}\n**Users:** {channel['users']}",
                inline=False
            )
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="cleanup", description="Force cleanup of empty temp channels")
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
        
        await interaction.followup.send(f"🧹 Cleaned up {deleted} empty channels.")
    
    @app_commands.command(name="broadcast", description="Broadcast message to temp channels")
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
                        await channel.send(f"📢 **Broadcast:** {message}")
                        sent += 1
                    except:
                        pass
        
        await interaction.followup.send(f"📢 Sent to {sent} channels.")

async def setup(bot):
    await bot.add_cog(AdminCog(bot))
