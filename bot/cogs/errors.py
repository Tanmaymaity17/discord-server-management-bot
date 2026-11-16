"""Global slash-command error handler."""
import discord
from discord import app_commands
from discord.ext import commands


class Errors(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._original = None

    async def cog_load(self):
        self._original = self.bot.tree.on_error
        self.bot.tree.on_error = self.on_tree_error

    async def cog_unload(self):
        self.bot.tree.on_error = self._original

    async def on_tree_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ):
        if isinstance(error, app_commands.CheckFailure) and not isinstance(
            error, app_commands.CommandOnCooldown
        ):
            msg = "🚫 This command is for the server owner, admins and mods only."
        elif isinstance(error, app_commands.CommandOnCooldown):
            msg = f"⏳ Slow down, try again in {error.retry_after:.0f}s."
        else:
            msg = "⚠️ Something went wrong. Please try again."
            print(f"Command error: {error!r}")
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Errors(bot))
