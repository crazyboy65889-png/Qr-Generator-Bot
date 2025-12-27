import discord
from discord import app_commands
from discord.ext import commands
import qrcode
from io import BytesIO
from datetime import datetime, timezone
import time
from cryptography.fernet import Fernet
import base64

class SetupCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_cooldowns = {}
        self.command_counts = {}
        
        # Setup encryption
        key_bytes = self.bot.ENCRYPTION_KEY.encode('utf-8')
        key = base64.urlsafe_b64encode(key_bytes.ljust(32)[:32])
        self.cipher = Fernet(key)
    
    def encrypt(self, data: str) -> str:
        if not data:
            return ""
        return self.cipher.encrypt(data.encode('utf-8')).decode('utf-8')
    
    def decrypt(self, data: str) -> str:
        if not data:
            return ""
        try:
            return self.cipher.decrypt(data.encode('utf-8')).decode('utf-8')
        except:
            return ""
    
    @app_commands.command(name="setup", description="Create UPI QR code")
    @app_commands.describe(
        upi_id="Your UPI ID (username@provider)",
        name="Your name",
        amount="Amount (₹)",
        note="Note (optional)",
        color="QR color (blue, green, red, purple)"
    )
    async def setup_command(self, interaction: discord.Interaction, upi_id: str, name: str, amount: float, note: str = "", color: str = "blue"):
        await interaction.response.defer(ephemeral=True)
        
        # Check cooldown
        user_id = interaction.user.id
        current_time = time.time()
        
        if user_id in self.user_cooldowns:
            if current_time - self.user_cooldowns[user_id] < 20:
                await interaction.followup.send("⏳ Please wait 20 seconds before another command.", ephemeral=True)
                return
        
        # Validate UPI
        if '@' not in upi_id:
            await interaction.followup.send("❌ Invalid UPI ID format. Use: username@provider", ephemeral=True)
            return
        
        # Check voice channel
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.followup.send("🎤 Join a payment voice channel first!", ephemeral=True)
            return
        
        try:
            # Generate QR
            upi_url = f"upi://pay?pa={upi_id}&pn={name}&am={amount}&tn={note}&cu=INR"
            qr = qrcode.QRCode(version=10, box_size=10, border=4)
            qr.add_data(upi_url)
            qr.make(fit=True)
            
            # Set colors
            colors = {
                'blue': (0, 122, 255),
                'green': (52, 199, 89),
                'red': (255, 59, 48),
                'purple': (88, 86, 214)
            }
            fill_color = colors.get(color.lower(), (0, 122, 255))
            
            img = qr.make_image(fill_color=fill_color, back_color="white")
            img_bytes = BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            
            # Save to DB
            record = {
                'user_id': user_id,
                'upi_id': self.encrypt(upi_id),
                'name': self.encrypt(name),
                'amount': amount,
                'note': self.encrypt(note),
                'color': color,
                'created_at': datetime.now(timezone.utc)
            }
            
            await self.bot.db.upi_records.insert_one(record)
            
            # Send QR
            file = discord.File(img_bytes, filename="upi_qr.png")
            embed = discord.Embed(
                title="✅ QR Code Generated",
                description=f"**Amount:** ₹{amount}\n**Note:** {note or 'None'}",
                color=discord.Color.green()
            )
            embed.set_image(url="attachment://upi_qr.png")
            
            await interaction.followup.send(embed=embed, file=file, ephemeral=True)
            self.user_cooldowns[user_id] = current_time
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)
    
    @app_commands.command(name="myupi", description="View your UPI records")
    async def my_upi_command(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        records = await self.bot.db.upi_records.find(
            {'user_id': interaction.user.id}
        ).sort('created_at', -1).to_list(length=10)
        
        if not records:
            await interaction.followup.send("📭 No UPI records found.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="📋 Your UPI Records",
            color=discord.Color.blue()
        )
        
        for i, record in enumerate(records, 1):
            embed.add_field(
                name=f"#{i} - ₹{record['amount']}",
                value=f"**UPI:** `{self.decrypt(record['upi_id'])}`\n**Name:** {self.decrypt(record['name'])}",
                inline=False
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="deleteupi", description="Delete a UPI record")
    @app_commands.describe(record_number="Record number to delete (from /myupi)")
    async def delete_upi_command(self, interaction: discord.Interaction, record_number: int):
        await interaction.response.defer(ephemeral=True)
        
        records = await self.bot.db.upi_records.find(
            {'user_id': interaction.user.id}
        ).sort('created_at', -1).to_list(length=10)
        
        if 1 <= record_number <= len(records):
            record_id = records[record_number-1]['_id']
            await self.bot.db.upi_records.delete_one({'_id': record_id})
            await interaction.followup.send("✅ Record deleted.", ephemeral=True)
        else:
            await interaction.followup.send("❌ Invalid record number.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(SetupCog(bot))
