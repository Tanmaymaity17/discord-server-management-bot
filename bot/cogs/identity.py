"""/identity apply  (core cog: available in every configured server)"""
import discord
from discord import app_commands
from discord.ext import commands

from bot.checks import get_profile, is_staff
from bot.identity import apply_identity


@app_commands.guild_only()
class IdentityCog(
    commands.GroupCog,
    group_name="identity",
    group_description="The bot's name, bio, avatar and banner in this server",
):
    def __init__(self, bot):
        self.bot = bot
        super().__init__()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if await self.bot.is_owner(interaction.user):
            return True
        return is_staff(interaction.user, get_profile(interaction))

    @app_commands.command(
        name="apply", description="Apply this server's identity from its profile"
    )
    @app_commands.describe(force="Re-send everything even if nothing changed")
    @app_commands.checks.cooldown(1, 30.0, key=lambda i: i.guild_id)
    async def apply(self, interaction: discord.Interaction, force: bool = False):
        profile = get_profile(interaction)
        await interaction.response.defer(ephemeral=True)
        lines = await apply_identity(self.bot, profile, interaction.guild, force=force)
        await interaction.followup.send(
            f"**Identity for {profile.name}**\n" + "\n".join(lines), ephemeral=True
        )


async def setup(bot):
    guilds = bot.profiles.guild_objects()
    if guilds:
        await bot.add_cog(IdentityCog(bot), guilds=guilds)
