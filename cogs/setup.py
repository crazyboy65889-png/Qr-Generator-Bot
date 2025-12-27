import discord
from discord import app_commands
from discord.ext import commands
import io
import datetime
import logging
from typing import Optional
from utils.validators import UPIValidator, RateLimiter, CooldownManager
from utils.qr_generator import UltimateQRGenerator
from utils.logger import log_command_execution

logger = logging.getLogger('SetupCog')

class Setup(commands.Cog):
    """Ultimate UPI setup commands"""
    
    def __init__(self, bot):
        self.bot = bot
        self.validator = UPIValidator()
        self.qr_generator = UltimateQRGenerator()
        self.rate_limiter = RateLimiter(max_requests=5, window=60)
        self.cooldown_manager = CooldownManager()
        self.cooldown_duration = 20  # seconds
    
    @app_commands.command(name="setup", description="🎯 Set UPI ID and generate QR (Premium Quality)")
    @app_commands.describe(
        upi_id="📱 Your UPI ID (e.g., john@okhdfcbank)",
        name="👤 Beneficiary name",
        amount="💰 Amount (₹0.01 - ₹9,99,999.99)",
        note="📝 Payment note (max 100 chars)",
        color="🎨 QR color (hex, e.g., #000000)"
    )
    async def setup(
        self,
        interaction: discord.Interaction,
        upi_id: str,
        name: Optional[str] = None,
        amount: Optional[float] = None,
        note: Optional[str] = None,
        color: Optional[str] = None
    ):
        """Ultimate UPI setup command"""
        
        # Rate limit check
        is_limited, retry_after = self.rate_limiter.is_rate_limited(f"{interaction.user.id}:setup")
        if is_limited:
            embed = discord.Embed(
                title="⏱️ Rate Limited",
                description=f"Too many requests! Try again in **{retry_after}s**.",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Cooldown check
        on_cooldown, remaining = self.cooldown_manager.check_cooldown(
            interaction.user.id,
            'setup',
            self.cooldown_duration
        )
        if on_cooldown:
            embed = discord.Embed(
                title="⏱️ Cooldown Active",
                description=f"Please wait **{remaining}s** before using this again.",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Voice channel permission check
        if interaction.channel.type == discord.ChannelType.voice:
            from cogs.voice_manager import VoiceManager
            if not await VoiceManager.check_temp_channel_access(self.bot, interaction):
                return
        
        # Validate UPI ID
        validation = self.validator.validate(upi_id.strip())
        if not validation['valid']:
            embed = discord.Embed(
                title="❌ Invalid UPI ID",
                description=f"```{validation['error']}```",
                color=discord.Color.red()
            )
            embed.add_field(
                name="📋 Examples",
                value="• `john@okhdfcbank`\n• `smith@paytm`\n• `user@ybl`",
                inline=False
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Show warnings if any
        if validation['warnings']:
            for warning in validation['warnings']:
                logger.warning(f"UPI warning for {interaction.user.id}: {warning}")
        
        # Validate name
        if name:
            name = name.strip()
            if len(name) > 50:
                await interaction.response.send_message(
                    "❌ Name too long! Maximum 50 characters.",
                    ephemeral=True
                )
                return
        
        # Validate amount
        if amount is not None:
            if amount <= 0:
                await interaction.response.send_message(
                    "❌ Amount must be greater than 0!",
                    ephemeral=True
                )
                return
            if amount > 999999.99:
                await interaction.response.send_message(
                    "❌ Amount too large! Maximum ₹9,99,999.99",
                    ephemeral=True
                )
                return
        
        # Validate note
        if note and len(note) > 100:
            await interaction.response.send_message(
                "❌ Note too long! Maximum 100 characters.",
                ephemeral=True
            )
            return
        
        # Parse color
        color_scheme = None
        if color:
            if not self._is_valid_hex_color(color):
                await interaction.response.send_message("❌ Invalid color format! Use #RRGGBB", ephemeral=True)
                return
            color_scheme = {'front_color': color, 'back_color': '#FFFFFF'}
        
        # Defer response
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Add to rate limiter
            self.rate_limiter.add_request(f"{interaction.user.id}:setup")
            self.cooldown_manager.set_cooldown(interaction.user.id, 'setup')
            
            # Save UPI data
            result = await self.bot.upi_manager.save_upi(
                str(interaction.user.id),
                upi_id.strip(),
                name or interaction.user.display_name,
                note,
                encrypt=True
            )
            
            if not result['success']:
                raise Exception("Failed to save UPI data")
            
            # Generate QR
            qr_buffer = await self.qr_generator.generate_upi_qr(
                upi_id=upi_id.strip(),
                name=name or interaction.user.display_name,
                amount=amount,
                note=note,
                avatar_url=interaction.user.avatar.url if interaction.user.avatar else None,
                color_scheme=color_scheme
            )
            
            # Create professional embed
            embed = discord.Embed(
                title="💸 UPI Payment QR Generated",
                description=f"**UPI ID:** `{upi_id.strip()}`",
                color=discord.Color.green(),
                timestamp=datetime.datetime.utcnow()
            )
            
            embed.add_field(
                name="👤 Beneficiary",
                value=f"```{name or interaction.user.display_name}```",
                inline=True
            )
            
            if amount:
                embed.add_field(
                    name="💰 Amount",
                    value=f"```₹{amount:.2f}```",
                    inline=True
                )
            
            if note:
                embed.add_field(
                    name="📝 Note",
                    value=f"```{note}```",
                    inline=False
                )
            
            if validation['warnings']:
                embed.add_field(
                    name="⚠️ Warnings",
                    value="\n".join(validation['warnings']),
                    inline=False
                )
            
            embed.add_field(
                name="📱 How to Pay?",
                value=(
                    "1️⃣ Scan QR with any UPI app\n"
                    "2️⃣ Verify details carefully\n"
                    "3️⃣ Enter UPI PIN to pay\n"
                    "4️⃣ Payment done! ✅"
                ),
                inline=False
            )
            
            embed.set_author(
                name=f"Generated for {interaction.user}",
                icon_url=interaction.user.avatar.url if interaction.user.avatar else None
            )
            
            embed.set_footer(
                text="UPI Bot v3.0 | Encrypted & Secure",
                icon_url="https://cdn.discordapp.com/embed/avatars/0.png"
            )
            
            # Send QR
            qr_file = discord.File(fp=qr_buffer, filename="upi_qr.png")
            embed.set_image(url="attachment://upi_qr.png")
            
            await interaction.followup.send(embed=embed, file=qr_file, ephemeral=True)
            
            # Update bot metrics
            self.bot.qr_generated += 1
            self.bot.commands_processed += 1
            
            log_command_execution(
                logger,
                'setup',
                interaction.user.id,
                interaction.guild.id if interaction.guild else 'DM',
                success=True
            )
            
            logger.info(f"✅ QR generated for {interaction.user.name} (UPI: {upi_id})")
            
        except Exception as e:
            logger.error(f"❌ Setup command failed: {e}")
            self.bot.errors_logged += 1
            
            await interaction.followup.send(
                embed=discord.Embed(
                    title="❌ Generation Failed",
                    description=f"An error occurred: `{str(e)}`\n\nPlease try again or contact support.",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )
    
    def _is_valid_hex_color(self, color: str) -> bool:
        """Validate hex color"""
        return bool(re.match(r'^#[0-9A-Fa-f]{6}$', color))
    
    @app_commands.command(name="myupi", description="📊 View your encrypted UPI profile")
    async def myupi(self, interaction: discord.Interaction):
        """View user UPI profile"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            stats = await self.bot.upi_manager.get_user_stats(str(interaction.user.id))
            
            if not stats['found']:
                embed = discord.Embed(
                    title="❌ No Profile Found",
                    description="Use `/setup` to create your UPI profile.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            embed = discord.Embed(
                title="📊 Your UPI Profile",
                description="Your data is encrypted and secure 🔒",
                color=discord.Color.blue(),
                timestamp=datetime.datetime.utcnow()
            )
            
            # Get user data (decrypted)
            user_data = await self.bot.upi_manager.get_upi(str(interaction.user.id), decrypt=True)
            
            if user_data:
                embed.add_field(
                    name="UPI ID",
                    value=f"`{user_data['upi_id']}`",
                    inline=False
                )
                embed.add_field(
                    name="Name",
                    value=f"```{user_data['name']}```",
                    inline=True
                )
                
                if user_data.get('note'):
                    embed.add_field(
                        name="Note",
                        value=f"```{user_data['note']}```",
                        inline=False
                    )
            
            embed.add_field(
                name="📈 Statistics",
                value=(
                    f"QR Generated: **{stats.get('qr_generated', 0)}**\n"
                    f"Usage Count: **{stats.get('usage_count', 0)}**\n"
                    f"Profile Created: <t:{int(stats['created_at'].timestamp())}:R>"
                ),
                inline=False
            )
            
            embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
            embed.set_footer(text="UPI Bot v3.0 | All data encrypted")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"MyUPI command failed: {e}")
            await interaction.followup.send("❌ Failed to load profile.", ephemeral=True)
    
    @app_commands.command(name="deleteupi", description="🗑️ Permanently delete your UPI data")
    async def deleteupi(self, interaction: discord.Interaction, confirm: bool = False):
        """Delete user data"""
        if not confirm:
            embed = discord.Embed(
                title="⚠️ Confirm Deletion",
                description=(
                    "This will **permanently delete** your UPI data!\n\n"
                    "To confirm, use:\n`/deleteupi confirm:true`"
                ),
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            result = await self.bot.upi_manager.delete_upi(
                str(interaction.user.id),
                permanent=True
            )
            
            if result:
                embed = discord.Embed(
                    title="✅ Data Deleted",
                    description=(
                        "Your UPI data has been **permanently deleted** from our database.\n\n"
                        "You can create a new profile anytime using `/setup`"
                    ),
                    color=discord.Color.green(),
                    timestamp=datetime.datetime.utcnow()
                )
                logger.info(f"🗑️ User {interaction.user.id} permanently deleted their data")
            else:
                embed = discord.Embed(
                    title="❌ Nothing to Delete",
                    description="No UPI data found for your account.",
                    color=discord.Color.orange()
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"DeleteUPI failed: {e}")
            await interaction.followup.send("❌ Failed to delete data.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Setup(bot))
                  
