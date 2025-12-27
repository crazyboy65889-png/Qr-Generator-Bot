import discord
from discord import app_commands
from discord.ext import commands
import datetime
import matplotlib.pyplot as plt
import io
import pandas as pd
from typing import Optional

class Analytics(commands.Cog):
    """Analytics and insights"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="useranalytics", description="📈 View your usage analytics")
    async def useranalytics(self, interaction: discord.Interaction, days: int = 7):
        """Show user analytics"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Get user data from MongoDB
            pipeline = [
                {
                    '$match': {
                        'user_id': str(interaction.user.id),
                        'timestamp': {
                            '$gte': datetime.datetime.utcnow() - datetime.timedelta(days=days)
                        }
                    }
                },
                {
                    '$group': {
                        '_id': '$event_type',
                        'count': {'$sum': 1}
                    }
                }
            ]
            
            results = await self.bot.analytics_collection.aggregate(pipeline).to_list(length=10)
            
            if not results:
                await interaction.followup.send("No analytics data found for the selected period.", ephemeral=True)
                return
            
            embed = discord.Embed(
                title=f"📈 Your Analytics (Last {days} days)",
                color=discord.Color.blue(),
                timestamp=datetime.datetime.utcnow()
            )
            
            for result in results:
                embed.add_field(
                    name=result['_id'].replace('_', ' ').title(),
                    value=f"**{result['count']}**",
                    inline=True
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"User analytics failed: {e}")
            await interaction.followup.send("❌ Failed to load analytics.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Analytics(bot))
  
