"""Preview confirmation view (Send / Save as template / Cancel)."""
import discord

from bot.ui.save_template import SaveTemplateModal


class ConfirmView(discord.ui.View):
    def __init__(self, author_id, channel, embed, content, mentions, payload):
        super().__init__(timeout=300)
        self.author_id = author_id
        self.channel = channel
        self.embed = embed
        self.content = content
        self.mentions = mentions
        self.payload = payload

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.author_id

    @discord.ui.button(label="Send", style=discord.ButtonStyle.success, emoji="✅")
    async def send(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await self.channel.send(
                content=self.content, embed=self.embed, allowed_mentions=self.mentions
            )
        except discord.Forbidden:
            await interaction.response.edit_message(
                content="❌ I don't have permission to post in that channel.", embed=None, view=None
            )
            return
        await interaction.response.edit_message(
            content=f"✅ Sent to {self.channel.mention}", embed=None, view=None
        )
        self.stop()

    @discord.ui.button(label="Save as template", style=discord.ButtonStyle.primary, emoji="💾")
    async def save_template(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SaveTemplateModal(self.payload))

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="🗑️")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Cancelled.", embed=None, view=None)
        self.stop()
