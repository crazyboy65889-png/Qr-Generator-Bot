import discord
from discord import app_commands
from discord.ext import commands
import qrcode
from io import BytesIO
from datetime import datetime
import time
import base64
from PIL import Image, ImageDraw, ImageFont
import os

class SetupCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.brand_name = "Digamber"
        self.user_cooldowns = {}
    
    async def check_user_upi(self, user_id: int):
        """Check if user has saved UPI"""
        user_data = self.bot.db.users.find_one({'user_id': user_id})
        if user_data and 'upi_id' in user_data and 'name' in user_data:
            return user_data
        return None
    
    @app_commands.command(name="setup", description=f"Setup your {brand_name} UPI for first time")
    @app_commands.describe(
        upi_id="Your UPI ID (username@provider)",
        name="Your name for payment"
    )
    async def setup_command(self, interaction: discord.Interaction, upi_id: str, name: str):
        """Setup UPI for first time only"""
        await interaction.response.defer(ephemeral=True)
        
        # Check if already has UPI
        existing = await self.check_user_upi(interaction.user.id)
        if existing:
            await interaction.followup.send(
                f"✅ You already have UPI saved!\n\n"
                f"**UPI:** `{existing['upi_id']}`\n"
                f"**Name:** {existing['name']}\n\n"
                f"Use `/qr <amount>` to generate QR code.\n"
                f"Use `/dynamic` for custom amount QR.",
                ephemeral=True
            )
            return
        
        # Validate UPI
        if '@' not in upi_id:
            await interaction.followup.send("❌ Invalid UPI ID. Use format: username@provider", ephemeral=True)
            return
        
        # Save to database
        self.bot.db.users.update_one(
            {'user_id': interaction.user.id},
            {'$set': {
                'user_id': interaction.user.id,
                'upi_id': upi_id,
                'name': name,
                'username': interaction.user.display_name,
                'setup_date': datetime.now()
            }},
            upsert=True
        )
        
        embed = discord.Embed(
            title=f"✅ {self.brand_name} UPI Setup Complete!",
            description=f"**Your UPI has been saved successfully!**\n\n"
                       f"**UPI ID:** `{upi_id}`\n"
                       f"**Name:** {name}\n\n"
                       f"🎯 **Now you can use:**\n"
                       f"• `/qr <amount>` - Generate fixed amount QR\n"
                       f"• `/dynamic` - QR where user enters amount\n"
                       f"• `/myinfo` - View your saved UPI",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"{self.brand_name} UPI System | Secure & Fast")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="qr", description=f"Generate {brand_name} QR code with saved UPI")
    @app_commands.describe(amount="Amount in ₹")
    async def qr_command(self, interaction: discord.Interaction, amount: float):
        """Generate QR with saved UPI"""
        await interaction.response.defer(ephemeral=True)
        
        # Get user's saved UPI
        user_data = await self.check_user_upi(interaction.user.id)
        if not user_data:
            await interaction.followup.send(
                "📝 **You need to setup your UPI first!**\n"
                "Use `/setup <upi_id> <name>` to save your UPI once.\n"
                "Then use `/qr <amount>` anytime!",
                ephemeral=True
            )
            return
        
        # Validate amount
        if amount <= 0 or amount > 100000:
            await interaction.followup.send("❌ Amount must be between ₹1 and ₹1,00,000", ephemeral=True)
            return
        
        try:
            # Generate QR code
            upi_url = f"upi://pay?pa={user_data['upi_id']}&pn={user_data['name']}&am={amount}&cu=INR"
            
            # Create QR with logo
            qr = qrcode.QRCode(
                version=10,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=10,
                border=4,
            )
            qr.add_data(upi_url)
            qr.make(fit=True)
            
            # Create QR image
            qr_img = qr.make_image(fill_color="#1a73e8", back_color="white").convert('RGB')
            
            # Add Digamber branding
            img_width, img_height = qr_img.size
            draw = ImageDraw.Draw(qr_img)
            
            # Add text at bottom
            try:
                # Try to load font, fallback to default
                font = ImageFont.truetype("arial.ttf", 20)
            except:
                font = ImageFont.load_default()
            
            text = f"{self.brand_name} UPI | ₹{amount}"
            text_bbox = draw.textbbox((0, 0), text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_position = ((img_width - text_width) // 2, img_height - 30)
            draw.text(text_position, text, fill="#1a73e8", font=font)
            
            # Convert to bytes
            img_bytes = BytesIO()
            qr_img.save(img_bytes, format='PNG', quality=95)
            img_bytes.seek(0)
            
            # Save to records
            self.bot.db.upi_records.insert_one({
                'user_id': interaction.user.id,
                'upi_id': user_data['upi_id'],
                'name': user_data['name'],
                'amount': amount,
                'created_at': datetime.now(),
                'type': 'fixed_amount'
            })
            
            # Send QR
            file = discord.File(img_bytes, filename="digamber_qr.png")
            embed = discord.Embed(
                title=f"✅ {self.brand_name} QR Generated",
                description=f"**Amount:** ₹{amount}\n"
                           f"**UPI:** `{user_data['upi_id']}`\n"
                           f"**Name:** {user_data['name']}\n\n"
                           f"*Scan this QR to pay instantly*",
                color=discord.Color.blue()
            )
            embed.set_image(url="attachment://digamber_qr.png")
            embed.set_footer(text=f"{self.brand_name} Payment System | Secure & Fast")
            
            await interaction.followup.send(embed=embed, file=file, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error generating QR: {str(e)}", ephemeral=True)
    
    @app_commands.command(name="dynamic", description=f"Generate {brand_name} dynamic QR (user enters amount)")
    async def dynamic_command(self, interaction: discord.Interaction):
        """Generate QR where user enters amount"""
        await interaction.response.defer(ephemeral=True)
        
        # Get user's saved UPI
        user_data = await self.check_user_upi(interaction.user.id)
        if not user_data:
            await interaction.followup.send(
                "📝 **You need to setup your UPI first!**\n"
                "Use `/setup <upi_id> <name>` to save your UPI once.",
                ephemeral=True
            )
            return
        
        try:
            # Generate dynamic QR (no amount specified)
            upi_url = f"upi://pay?pa={user_data['upi_id']}&pn={user_data['name']}&cu=INR"
            
            # Create QR
            qr = qrcode.QRCode(
                version=10,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=10,
                border=4,
            )
            qr.add_data(upi_url)
            qr.make(fit=True)
            
            # Create QR image
            qr_img = qr.make_image(fill_color="#34a853", back_color="white").convert('RGB')
            
            # Add branding
            img_width, img_height = qr_img.size
            draw = ImageDraw.Draw(qr_img)
            
            try:
                font = ImageFont.truetype("arial.ttf", 20)
            except:
                font = ImageFont.load_default()
            
            text = f"{self.brand_name} UPI | Enter Amount"
            text_bbox = draw.textbbox((0, 0), text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_position = ((img_width - text_width) // 2, img_height - 30)
            draw.text(text_position, text, fill="#34a853", font=font)
            
            # Convert to bytes
            img_bytes = BytesIO()
            qr_img.save(img_bytes, format='PNG', quality=95)
            img_bytes.seek(0)
            
            # Save to records
            self.bot.db.upi_records.insert_one({
                'user_id': interaction.user.id,
                'upi_id': user_data['upi_id'],
                'name': user_data['name'],
                'amount': 0,  # Dynamic amount
                'created_at': datetime.now(),
                'type': 'dynamic_amount'
            })
            
            # Send QR
            file = discord.File(img_bytes, filename="digamber_dynamic_qr.png")
            embed = discord.Embed(
                title=f"🔄 {self.brand_name} Dynamic QR",
                description=f"**UPI:** `{user_data['upi_id']}`\n"
                           f"**Name:** {user_data['name']}\n\n"
                           f"*User can enter any amount while paying*\n"
                           f"*Perfect for variable payments*",
                color=discord.Color.green()
            )
            embed.set_image(url="attachment://digamber_dynamic_qr.png")
            embed.set_footer(text=f"{self.brand_name} Dynamic Payment | User Sets Amount")
            
            await interaction.followup.send(embed=embed, file=file, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)
    
    @app_commands.command(name="myinfo", description=f"View your {brand_name} UPI info")
    async def myinfo_command(self, interaction: discord.Interaction):
        """View saved UPI info"""
        await interaction.response.defer(ephemeral=True)
        
        user_data = await self.check_user_upi(interaction.user.id)
        if not user_data:
            await interaction.followup.send(
                "📝 **No UPI saved yet!**\n"
                "Use `/setup <upi_id> <name>` to save your UPI once.",
                ephemeral=True
            )
            return
        
        # Get QR usage stats
        qr_count = self.bot.db.upi_records.count_documents({'user_id': interaction.user.id})
        
        embed = discord.Embed(
            title=f"📋 Your {self.brand_name} UPI Info",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="🆔 UPI ID", value=f"`{user_data['upi_id']}`", inline=False)
        embed.add_field(name="👤 Name", value=user_data['name'], inline=True)
        embed.add_field(name="📊 QR Generated", value=str(qr_count), inline=True)
        
        if 'setup_date' in user_data:
            embed.add_field(name="📅 Setup Date", value=user_data['setup_date'].strftime('%d/%m/%Y'), inline=True)
        
        embed.add_field(
            name="🎯 Quick Commands",
            value=f"• `/qr <amount>` - Generate fixed amount QR\n"
                  f"• `/dynamic` - Generate dynamic QR\n"
                  f"• `/myinfo` - View this info",
            inline=False
        )
        
        embed.set_footer(text=f"{self.brand_name} UPI System | Your data is secure")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="update", description=f"Update your {brand_name} UPI info")
    @app_commands.describe(
        upi_id="New UPI ID (leave empty to keep current)",
        name="New name (leave empty to keep current)"
    )
    async def update_command(self, interaction: discord.Interaction, upi_id: str = None, name: str = None):
        """Update UPI info"""
        await interaction.response.defer(ephemeral=True)
        
        user_data = await self.check_user_upi(interaction.user.id)
        if not user_data:
            await interaction.followup.send("❌ You don't have UPI saved yet. Use `/setup` first.", ephemeral=True)
            return
        
        update_data = {}
        if upi_id and upi_id.strip():
            if '@' not in upi_id:
                await interaction.followup.send("❌ Invalid UPI ID format", ephemeral=True)
                return
            update_data['upi_id'] = upi_id
        
        if name and name.strip():
            update_data['name'] = name
        
        if not update_data:
            await interaction.followup.send("ℹ️ No changes provided.", ephemeral=True)
            return
        
        self.bot.db.users.update_one(
            {'user_id': interaction.user.id},
            {'$set': update_data}
        )
        
        await interaction.followup.send("✅ UPI info updated successfully!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(SetupCog(bot))
