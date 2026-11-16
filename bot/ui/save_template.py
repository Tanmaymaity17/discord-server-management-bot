"""Modal that saves the previewed embed as a template."""
from datetime import datetime, timezone

import discord

from bot import config
from bot.storage.templates import TEMPLATE_NAME_RE


class SaveTemplateModal(discord.ui.Modal, title="Save as template"):
    name_in = discord.ui.TextInput(label="Template name", max_length=40, placeholder="weekly-event")

    def __init__(self, payload: dict):
        super().__init__()
        self.payload = payload

    async def on_submit(self, interaction: discord.Interaction):
        store = interaction.client.store_for(interaction.guild_id)
        name = self.name_in.value.strip()
        if not TEMPLATE_NAME_RE.match(name):
            return await interaction.response.send_message(
                "❌ Use letters, numbers, spaces, `-` or `_` (max 40 characters).", ephemeral=True
            )
        existed = store.get(name) is not None
        if not existed and len(store.templates) >= config.MAX_TEMPLATES:
            return await interaction.response.send_message(
                f"❌ You've reached the limit of {config.MAX_TEMPLATES} templates. "
                "Delete one with `/template delete` first.",
                ephemeral=True,
            )
        store.save(
            name,
            {
                **self.payload,
                "created_by": interaction.user.id,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        verb = "updated" if existed else "saved"
        await interaction.response.send_message(
            f"💾 Template **{name}** {verb}. Use it with `/template use`.", ephemeral=True
        )
