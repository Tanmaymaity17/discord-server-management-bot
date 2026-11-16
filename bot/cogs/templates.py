"""/template use | list | preview | delete  (templates are per server)"""
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from bot.checks import channel_ok, get_profile, is_staff
from bot.embeds.builder import embed_from_data
from bot.ui.modals import EmbedModal
from bot.utils.colors import hex_to_color


def _store(interaction: discord.Interaction):
    return interaction.client.store_for(interaction.guild_id)


async def template_autocomplete(interaction: discord.Interaction, current: str):
    if not is_staff(interaction.user, get_profile(interaction)):
        return []   # don't leak template names to non-staff
    cur = current.lower()
    return [
        app_commands.Choice(name=t["name"], value=t["name"])
        for t in _store(interaction).templates.values()
        if cur in t["name"].lower()
    ][:25]


@app_commands.guild_only()
class Templates(
    commands.GroupCog,
    group_name="template",
    group_description="Saved templates for recurring posts",
):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        super().__init__()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Every /template subcommand is staff-only (using this server's mod roles)."""
        return is_staff(interaction.user, get_profile(interaction))

    @app_commands.command(
        name="use", description="Post from a saved template (you can edit it before sending)"
    )
    @app_commands.describe(
        name="Template to use",
        channel="Where to post it",
        ping="Role (or @everyone) to ping — optional",
        color="Hex color like #FF8800 — optional, defaults to the template's saved color",
    )
    @app_commands.autocomplete(name=template_autocomplete)
    async def use(
        self,
        interaction: discord.Interaction,
        name: str,
        channel: discord.TextChannel,
        ping: Optional[discord.Role] = None,
        color: Optional[str] = None,
    ):
        t = _store(interaction).get(name)
        if t is None:
            return await interaction.response.send_message(
                f"❌ No template named **{name}**. Try `/template list`.", ephemeral=True
            )
        if err := channel_ok(interaction, channel):
            return await interaction.response.send_message(err, ephemeral=True)
        profile = get_profile(interaction)
        col = profile.parse_color(color) if color else hex_to_color(t["color"])
        await interaction.response.send_modal(
            EmbedModal(t["kind"], channel, col, ping, profile, prefill=t)
        )

    @app_commands.command(name="list", description="Show all saved templates")
    async def list(self, interaction: discord.Interaction):
        store = _store(interaction)
        if not store.templates:
            return await interaction.response.send_message(
                "No templates yet. Run `/announce` or `/embed`, then press **Save as template** on the preview.",
                ephemeral=True,
            )
        lines = []
        for t in sorted(store.templates.values(), key=lambda x: x["name"].lower()):
            title = (t.get("title") or "").replace("\n", " ")
            title = title if len(title) <= 40 else title[:37] + "..."
            lines.append(f"**{t['name']}** — `{t['kind']}` · {t['color']} · {title}")
        listing = discord.Embed(
            title="Saved templates",
            description="\n".join(lines),
            color=get_profile(interaction).accent_color,
        )
        await interaction.response.send_message(embed=listing, ephemeral=True)

    @app_commands.command(name="preview", description="Preview a saved template without posting")
    @app_commands.describe(name="Template to preview")
    @app_commands.autocomplete(name=template_autocomplete)
    async def preview(self, interaction: discord.Interaction, name: str):
        t = _store(interaction).get(name)
        if t is None:
            return await interaction.response.send_message(
                f"❌ No template named **{name}**.", ephemeral=True
            )
        embed = embed_from_data(
            interaction.guild, get_profile(interaction).theme, t, hex_to_color(t["color"])
        )
        await interaction.response.send_message(
            f"**Preview** of template **{t['name']}**", embed=embed, ephemeral=True
        )

    @app_commands.command(name="delete", description="Delete a saved template")
    @app_commands.describe(name="Template to delete")
    @app_commands.autocomplete(name=template_autocomplete)
    async def delete(self, interaction: discord.Interaction, name: str):
        if _store(interaction).delete(name):
            await interaction.response.send_message(f"🗑️ Deleted template **{name}**.", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ No template named **{name}**.", ephemeral=True)


async def setup(bot):
    guilds = bot.guilds_for("templates")
    if guilds:
        await bot.add_cog(Templates(bot), guilds=guilds)
