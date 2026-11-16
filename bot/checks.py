"""Permission checks and shared guards (all per-server, driven by the profile)."""
from typing import Optional

import discord
from discord import app_commands

from bot.profiles import Profile


def get_profile(interaction: discord.Interaction) -> Optional[Profile]:
    return interaction.client.profiles.get(interaction.guild_id)


def is_staff(member: discord.abc.User, profile: Optional[Profile]) -> bool:
    """Server owner, Administrators, or anyone with one of THIS server's mod roles."""
    if profile is None or not isinstance(member, discord.Member):
        return False
    if member.id == member.guild.owner_id:
        return True
    if member.guild_permissions.administrator:
        return True
    return any(r.id in profile.mod_role_ids for r in member.roles)


def staff_only():
    """Decorator for a single slash command."""
    async def predicate(interaction: discord.Interaction) -> bool:
        if is_staff(interaction.user, get_profile(interaction)):
            return True
        raise app_commands.CheckFailure("staff only")

    return app_commands.check(predicate)


def channel_ok(interaction: discord.Interaction, channel: discord.TextChannel) -> Optional[str]:
    """Return an error message if the bot can't post embeds in `channel`, else None."""
    perms = channel.permissions_for(interaction.guild.me)
    if not (perms.view_channel and perms.send_messages and perms.embed_links):
        return f"❌ I need View Channel, Send Messages and Embed Links in {channel.mention}."
    return None
