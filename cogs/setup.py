import discord
from discord import app_commands
from discord.ext import commands
import qrcode
from io import BytesIO
from datetime import datetime
import time

class SetupCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_cooldowns = {}
    
    @app_commands.command(name="setup", description="Create UPI QR code")
    @app_commands.describe(
        upi_id="Your UPI ID (username@provider)",
        name="Your name",
        amount="Amount (₹)",
        note="Note (optional)",
        color="QR color (blue, green, red, purple, orange, pink)"
    )
    @app_commands.choices(color=[
        app_commands.Choice(name="Blue", value="blue"),
        app_commands.Choice(name="Green", value="green"),
        app_commands.Choice(name="Red", value="red"),
        app_commands.Choice(name="Purple", value="purple"),
        app_commands.Choice(name="Orange", value="orange"),
        app_commands.Choice(name="Pink", value="pink"),
    ])
    async def setup_command(self, interaction: discord.Interaction, upi_id: str, name: str, amount: float, note: str = "", color: str = "blue"):
        await interaction.response.defer(ephemeral=True)
        
        # Check cooldown
        user_id = interaction.user.id
        current_time = time.time()
        
        if user_id in self.user_cooldowns:
            if current_time - self.user_cooldowns[user_id] < 20:
                await interaction.followup.send("⏳ Please wait 20 seconds before another command.", ephemeral=True)
                return
        
        # Check voice channel
        if not interaction.user.voice:
            await interaction.followup.send("🎤 Please join a payment voice channel first!", ephemeral=True)
            return
        
        # Validate amount
        if amount <= 0 or amount > 100000:
            await interaction.followup.send("❌ Amount must be between ₹1 and ₹1,00,000", ephemeral=True)
            return
        
        # Validate UPI
        if '@' not in upi_id:
            await interaction.followup.send("❌ Invalid UPI ID. Use format: username@provider", ephemeral=True)
            return
        
        try:
            # Generate QR code
            upi_url = f"upi://pay?pa={upi_id}&pn={name}&am={amount}&tn={note}&cu=INR"
            qr = qrcode.QRCode(version=10, box_size=10, border=4)
            qr.add_data(upi_url)
            qr.make(fit=True)
            
            # Set color
            colors = {
                'blue': (0, 122, 255),
                'green': (52, 199, 89),
                'red': (255, 59, 48),
                'purple': (88, 86, 214),
                'orange': (255, 149, 0),
                'pink': (255, 45, 85)
            }
            fill_color = colors.get(color.lower(), (0, 122, 255))
            
            img = qr.make_image(fill_color=fill_color, back_color="white")
            img_bytes = BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            
            # Save to database
            self.bot.db.upi_records.insert_one({
                'user_id': user_id,
                'upi_id': upi_id,
                'name': name,
                'amount': amount,
                'note': note,
                'color': color,
                'created_at': datetime.now(),
                'username': interaction.user.display_name
            })
            
            # Send QR code
            file = discord.File(img_bytes, filename="upi_qr.png")
            embed = discord.Embed(
                title="✅ UPI QR Code Generated",
                description=f"**Amount:** ₹{amount}\n**Note:** {note or 'No note provided'}\n**Color:** {color}",
                color=discord.Color.green()
            )
            embed.set_image(url="attachment://upi_qr.png")
            embed.set_footer(text=f"UPI ID: {upi_id}")
            
            await interaction.followup.send(embed=embed, file=file, ephemeral=True)
            self.user_cooldowns[user_id] = current_time
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)
    
    @app_commands.command(name="myupi", description="View your UPI records")
    async def my_upi_command(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        try:
            records = list(self.bot.db.upi_records.find(
                {'user_id': interaction.user.id}
            ).sort('created_at', -1).limit(10))
            
            if not records:
                await interaction.followup.send("📭 No UPI records found. Use `/setup` to create one.", ephemeral=True)
                return
            
            embed = discord.Embed(
                title="📋 Your UPI Records",
                color=discord.Color.blue(),
                description=f"Total records: {len(records)}"
            )
            
            for i, record in enumerate(records, 1):
                embed.add_field(
                    name=f"#{i} - ₹{record['amount']}",
                    value=f"**UPI:** `{record['upi_id']}`\n**Name:** {record['name']}\n**Date:** {record['created_at'].strftime('%d/%m/%Y')}",
                    inline=False
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)
    
    @app_commands.command(name="deleteupi", description="Delete a UPI record")
    @app_commands.describe(record_number="Record number to delete (from /myupi)")
    async def delete_upi_command(self, interaction: discord.Interaction, record_number: int):
        await interaction.response.defer(ephemeral=True)
        
        try:
            records = list(self.bot.db.upi_records.find(
                {'user_id': interaction.user.id}
            ).sort('created_at', -1).limit(10))
            
            if 1 <= record_number <= len(records):
                record_id = records[record_number-1]['_id']
                self.bot.db.upi_records.delete_one({'_id': record_id})
                await interaction.followup.send("✅ UPI record deleted successfully!", ephemeral=True)
            else:
                await interaction.followup.send("❌ Invalid record number. Use `/myupi` to see your records.", ephemeral=True)
                
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(SetupCog(bot))
