"""/profile show | reload  (core cog: available in every configured server)"""
import discord
from discord import app_commands
from discord.ext import commands

from bot.checks import get_profile, is_staff
from bot.profiles import IDENTITY_FIELDS


@app_commands.guild_only()
class ProfileCog(
    commands.GroupCog,
    group_name="profile",
    group_description="Server profile and configuration",
):
    def __init__(self, bot):
        self.bot = bot
        super().__init__()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if await self.bot.is_owner(interaction.user):
            return True
        return is_staff(interaction.user, get_profile(interaction))

    @app_commands.command(name="show", description="Show this server's active profile")
    async def show(self, interaction: discord.Interaction):
        p = get_profile(interaction)
        roles = []
        for rid in sorted(p.mod_role_ids):
            role = interaction.guild.get_role(rid)
            roles.append(role.mention if role else f"⚠️ `{rid}` (not found in this server)")

        def fmt(key: str) -> str:
            v = p.identity.get(key)
            return "not managed" if v is None else ("(cleared)" if v == "" else v)

        embed = discord.Embed(title=f"Profile: {p.name}", color=p.accent_color)
        embed.add_field(name="Guild ID", value=f"`{p.guild_id}`", inline=True)
        embed.add_field(name="Accent", value=p.theme["accent"], inline=True)
        embed.add_field(name="Features", value=", ".join(sorted(p.enabled_cogs)) or "none", inline=False)
        embed.add_field(name="Mod roles", value="\n".join(roles) or "none (owner/admins only)", inline=False)
        embed.add_field(
            name="Identity",
            value="\n".join(f"**{k}:** {fmt(k)}" for k in IDENTITY_FIELDS)[:1024],
            inline=False,
        )
        embed.set_footer(text=f"profiles/{p.key}.json")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="reload", description="Reload all server profiles from disk (bot owner only)"
    )
    async def reload(self, interaction: discord.Interaction):
        if not await self.bot.is_owner(interaction.user):
            return await interaction.response.send_message(
                "🚫 Only the bot owner can reload profiles.", ephemeral=True
            )
        await interaction.response.defer(ephemeral=True)
        problems = await self.bot.refresh()
        report = await self.bot.apply_identities()
        msg = f"✅ Reloaded {len(self.bot.profiles.all())} server profile(s) and re-synced commands."
        if report:
            msg += "\n\n**Identity**\n" + "\n".join(
                f"**{name}:** " + " · ".join(lines) for name, lines in report.items()
            )
        if problems:
            msg += "\n\n⚠️ **Problems:**\n" + "\n".join(f"• {p}" for p in problems)
        await interaction.followup.send(msg[:1900], ephemeral=True)


async def setup(bot):
    guilds = bot.profiles.guild_objects()
    if guilds:
        await bot.add_cog(ProfileCog(bot), guilds=guilds)
