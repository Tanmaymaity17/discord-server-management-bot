"""/announce and /embed"""
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from bot.checks import channel_ok, get_profile, staff_only
from bot.ui.modals import EmbedModal


class Announce(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="announce", description="Create a themed announcement embed")
    @app_commands.describe(
        channel="Where to post it",
        ping="Role (or @everyone) to ping — optional",
        color="Hex color like #FF8800 — optional, defaults to the server theme",
    )
    @staff_only()
    async def announce(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        ping: Optional[discord.Role] = None,
        color: Optional[str] = None,
    ):
        if err := channel_ok(interaction, channel):
            return await interaction.response.send_message(err, ephemeral=True)
        profile = get_profile(interaction)
        await interaction.response.send_modal(
            EmbedModal("announce", channel, profile.parse_color(color), ping, profile)
        )

    @app_commands.command(name="embed", description="Create a custom embed message")
    @app_commands.describe(channel="Where to post it", color="Hex color like #FF8800 — optional")
    @staff_only()
    async def embed(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        color: Optional[str] = None,
    ):
        if err := channel_ok(interaction, channel):
            return await interaction.response.send_message(err, ephemeral=True)
        profile = get_profile(interaction)
        await interaction.response.send_modal(
            EmbedModal("embed", channel, profile.parse_color(color), None, profile)
        )


async def setup(bot):
    guilds = bot.guilds_for("announce")     # only servers that enabled this feature
    if guilds:
        await bot.add_cog(Announce(bot), guilds=guilds)
