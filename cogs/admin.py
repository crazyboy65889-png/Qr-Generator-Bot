import discord
from discord import app_commands
from discord.ext import commands
import datetime
import psutil
import logging

logger = logging.getLogger('AdminCog')

class Admin(commands.Cog):
    """Ultimate admin commands"""
    
    def __init__(self, bot):
        self.bot = bot
        self.allowed_user_ids = {int(os.getenv('BOT_OWNER_ID', 0))}
    
    def is_admin_or_owner(self, user_id: int, guild: discord.Guild = None) -> bool:
        """Check if user is admin or owner"""
        if user_id in self.allowed_user_ids:
            return True
        
        if guild:
            member = guild.get_member(user_id)
            if member and member.guild_permissions.administrator:
                return True
        
        return False
    
    @app_commands.command(name="botstats", description="📊 View comprehensive bot statistics")
    async def botstats(self, interaction: discord.Interaction):
        """Detailed bot statistics"""
        if not self.is_admin_or_owner(interaction.user.id, interaction.guild):
            await interaction.response.send_message("❌ Admin/Owner only!", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Get stats
            bot_stats = self.bot.get_bot_stats()
            db_stats = await self.bot.upi_manager.get_global_stats()
            
            embed = discord.Embed(
                title="📊 Bot Statistics Dashboard",
                description=f"Bot Uptime: {self._format_uptime(bot_stats['uptime_seconds'])}",
                color=discord.Color.purple(),
                timestamp=datetime.datetime.utcnow()
            )
            
            # System metrics
            embed.add_field(
                name="💻 System",
                value=(
                    f"Memory: **{bot_stats['memory_mb']:.1f} MB**\n"
                    f"CPU: **{psutil.cpu_percent()}%**\n"
                    f"Errors: **{bot_stats['errors_logged']}**"
                ),
                inline=True
            )
            
            # Discord metrics
            embed.add_field(
                name="🤖 Discord",
                value=(
                    f"Guilds: **{bot_stats['guilds']}**\n"
                    f"Voice: **{bot_stats['voice_connections']}**\n"
                    f"Temp Channels: **{bot_stats['temp_channels']}**"
                ),
                inline=True
            )
            
            # Application metrics
            embed.add_field(
                name="📈 Application",
                value=(
                    f"Commands: **{bot_stats['commands_processed']}**\n"
                    f"QR Generated: **{bot_stats['qr_generated']}**\n"
                    f"DB Size: **{db_stats.get('database_size_mb', 0):.2f} MB**"
                ),
                inline=True
            )
            
            # Database stats
            embed.add_field(
                name="🗄️ Database",
                value=(
                    f"Total Users: **{db_stats.get('total_users', 0)}**\n"
                    f"QR Total: **{db_stats.get('total_qr_generated', 0)}**\n"
                    f"UPI Saved: **{db_stats.get('total_upi_saved', 0)}**"
                ),
                inline=True
            )
            
            embed.set_footer(text="UPI Bot v3.0 | Admin Dashboard")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Botstats failed: {e}")
            await interaction.followup.send("❌ Failed to load stats.", ephemeral=True)
    
    def _format_uptime(self, seconds: float) -> str:
        """Format uptime in human readable form"""
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0 or days > 0:
            parts.append(f"{hours}h")
        parts.append(f"{minutes}m")
        
        return " ".join(parts)
    
    @app_commands.command(name="tempchannels", description="🎤 List all active temp channels")
    async def tempchannels(self, interaction: discord.Interaction):
        """List temporary channels"""
        if not self.is_admin_or_owner(interaction.user.id, interaction.guild):
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return
        
        if not self.bot.temp_channels:
            await interaction.response.send_message("✅ No temporary channels active.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🎤 Active Temporary Channels",
            color=discord.Color.blue(),
            timestamp=datetime.datetime.utcnow()
        )
        
        for idx, (channel_id, data) in enumerate(list(self.bot.temp_channels.items())[:25]):
            guild = self.bot.get_guild(data['guild_id'])
            channel = guild.get_channel(channel_id) if guild else None
            owner = self.bot.get_user(data['owner'])
            
            embed.add_field(
                name=f"{idx+1}. #{channel.name if channel else 'Unknown'}",
                value=(
                    f"Owner: {owner.mention if owner else 'Unknown'}\n"
                    f"Guild: {guild.name if guild else 'Unknown'}\n"
                    f"Created: <t:{int(data['created_at'].timestamp())}:R>\n"
                    f"Members: {len(channel.members) if channel else 0}"
                ),
                inline=False
            )
        
        embed.set_footer(text=f"Total: {len(self.bot.temp_channels)} channels")
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="cleanup", description="🧹 Force cleanup temp channels")
    async def cleanup(self, interaction: discord.Interaction, older_than: int = 60):
        """Force cleanup old channels"""
        if not self.is_admin_or_owner(interaction.user.id, interaction.guild):
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            cleaned = 0
            errors = 0
            cutoff = datetime.datetime.utcnow() - datetime.timedelta(minutes=older_than)
            
            for channel_id, data in list(self.bot.temp_channels.items()):
                if data['created_at'] < cutoff:
                    try:
                        guild = self.bot.get_guild(data['guild_id'])
                        if guild:
                            channel = guild.get_channel(channel_id)
                            if channel:
                                await channel.delete(reason=f"Admin cleanup by {interaction.user}")
                        del self.bot.temp_channels[channel_id]
                        cleaned += 1
                    except Exception:
                        errors += 1
            
            embed = discord.Embed(
                title="🧹 Cleanup Complete",
                description=f"✅ Cleaned: {cleaned} channels\n❌ Errors: {errors}",
                color=discord.Color.green() if errors == 0 else discord.Color.orange(),
                timestamp=datetime.datetime.utcnow()
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            logger.info(f"🧹 Admin cleanup: {cleaned} channels by {interaction.user}")
            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            await interaction.followup.send("❌ Cleanup failed.", ephemeral=True)
    
    @app_commands.command(name="broadcast", description="📢 Send announcement to all temp channels")
    async def broadcast(self, interaction: discord.Interaction, message: str):
        """Broadcast message to all temp channels"""
        if not self.is_admin_or_owner(interaction.user.id, interaction.guild):
            await interaction.response.send_message("❌ Owner only!", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            sent = 0
            failed = 0
            
            for channel_id, data in self.bot.temp_channels.items():
                try:
                    guild = self.bot.get_guild(data['guild_id'])
                    channel = guild.get_channel(channel_id) if guild else None
                    
                    if channel and isinstance(channel, discord.VoiceChannel):
                        embed = discord.Embed(
                            title="📢 Announcement",
                            description=message,
                            color=discord.Color.blue(),
                            timestamp=datetime.datetime.utcnow()
                        )
                        embed.set_footer(text=f"From {interaction.user}")
                        
                        await channel.send(embed=embed)
                        sent += 1
                except Exception:
                    failed += 1
            
            await interaction.followup.send(
                f"📢 Broadcast sent to {sent} channels (Failed: {failed})",
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Broadcast failed: {e}")
            await interaction.followup.send("❌ Broadcast failed.", ephemeral=True)
    
    @app_commands.command(name="botrestart", description="🔄 Restart the bot (Owner Only)")
    async def botrestart(self, interaction: discord.Interaction):
        """Restart bot process"""
        if interaction.user.id not in self.allowed_user_ids:
            await interaction.response.send_message("❌ Bot owner only!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🔄 Restarting Bot...",
            description="The bot will restart in 5 seconds.",
            color=discord.Color.yellow(),
            timestamp=datetime.datetime.utcnow()
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        logger.critical(f"🔄 Bot restart initiated by {interaction.user}")
        
        # Save state
        import json
        with open('restart_state.json', 'w') as f:
            json.dump({
                'reason': f'Restart by {interaction.user}',
                'timestamp': datetime.datetime.utcnow().isoformat()
            }, f)
        
        # Restart
        import os
        import sys
        os.execl(sys.executable, sys.executable, *sys.argv)

async def setup(bot):
    await bot.add_cog(Admin(bot))
          
