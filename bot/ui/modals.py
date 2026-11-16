"""The main announcement / embed form."""
from typing import Optional

import discord

from bot.embeds.builder import embed_from_data
from bot.ui.views import ConfirmView
from bot.utils.colors import color_to_hex


class EmbedModal(discord.ui.Modal):
    title_in = discord.ui.TextInput(label="Title", max_length=200, placeholder="Big news!")
    desc_in = discord.ui.TextInput(
        label="Message",
        style=discord.TextStyle.paragraph,
        max_length=4000,
        placeholder="Supports **bold**, *italic*, > quotes, #channel links, lists, and emojis.",
    )
    image_in = discord.ui.TextInput(
        label="Banner image URL (optional)", required=False, placeholder="https://..."
    )
    thumb_in = discord.ui.TextInput(
        label="Thumbnail URL (optional)",
        required=False,
        placeholder="Blank = default logo. Paste a link, or type none to hide it.",
    )
    footer_in = discord.ui.TextInput(label="Footer text (optional)", required=False, max_length=200)

    def __init__(self, kind, channel, color, role, profile, prefill: Optional[dict] = None):
        super().__init__(title="New Announcement" if kind == "announce" else "New Embed")
        self.kind, self.channel, self.color, self.role = kind, channel, color, role
        self.profile = profile
        if prefill:  # fields from a saved template, editable before sending
            self.title_in.default = prefill.get("title") or None
            self.desc_in.default = prefill.get("description") or None
            self.image_in.default = prefill.get("image") or None
            self.thumb_in.default = prefill.get("thumb") or None
            self.footer_in.default = prefill.get("footer") or None

    async def on_submit(self, interaction: discord.Interaction):
        payload = {
            "kind": self.kind,
            "title": self.title_in.value,
            "description": self.desc_in.value.replace("\\n", "\n"),
            "image": self.image_in.value.strip(),
            "thumb": self.thumb_in.value.strip(),
            "footer": self.footer_in.value.strip(),
            "color": color_to_hex(self.color),
        }
        embed = embed_from_data(interaction.guild, self.profile.theme, payload, self.color)

        content, mentions = None, discord.AllowedMentions.none()
        if self.role is not None:
            # Build the ping text ourselves so @everyone is never shown as "@@everyone".
            if self.role.is_default():
                content = "@everyone"
                mentions = discord.AllowedMentions(everyone=True)
            else:
                content = f"<@&{self.role.id}>"
                mentions = discord.AllowedMentions(roles=[self.role])
        view = ConfirmView(interaction.user.id, self.channel, embed, content, mentions, payload)
        preview = f"**Preview** — will be posted in {self.channel.mention}"
        if content:
            preview += f" with ping `{'@everyone' if self.role.is_default() else '@' + self.role.name}`"
        await interaction.response.send_message(
            preview,
            embed=embed,
            view=view,
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )
