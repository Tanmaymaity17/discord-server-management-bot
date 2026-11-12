"""
Server announcement & embed bot (single-server, staff-only).

Commands (slash):
  /announce            -> themed announcement embed, optional role/@everyone ping
  /embed               -> general custom embed (no ping)
  /template use        -> post from a saved template (editable before sending)
  /template list       -> list saved templates
  /template preview    -> preview a saved template
  /template delete     -> delete a saved template

/announce and /embed open a form (modal) for the text, show a preview, then send on confirm.
On the preview, press "Save as template" to store it for reuse.
Templates are saved in ./data/templates.json next to this file.
Only the server owner, Administrators, and members with a configured mod role can use them.
"""

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import discord
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.environ["DISCORD_TOKEN"]
GUILD_ID = int(os.environ["GUILD_ID"])
MOD_ROLE_IDS = {int(x) for x in os.getenv("MOD_ROLE_IDS", "").split(",") if x.strip()}

# Local storage: a "data" folder next to bot.py (created automatically).
DATA_DIR = Path(__file__).resolve().parent / "data"
TEMPLATES_FILE = DATA_DIR / "templates.json"

# ───────────────────────── THEME (edit this per client) ─────────────────────────
THEME = {
    "accent": "#E10600",            # blood red, matches the Team Cobra logo
    "announce_prefix": "🐍",        # shown before announcement titles
    "announce_label": "Official Announcement",
    "footer_text": "Team Cobra Official",   # default footer
    "footer_icon": None,            # URL or None (None = bot avatar / server icon)
    "divider": "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬",  # shown under announcement titles; "" to disable
    "default_thumbnail": None,      # URL or None (None = bot avatar / server icon)
    "use_bot_avatar": True,         # use the bot's profile picture (the cobra logo) for author/footer/thumbnail
    "timestamp": True,              # show the "Today at 8:21 PM" time on every embed (even with a custom footer)
}
NO_THUMB = "none"                   # typing this in the thumbnail field hides the thumbnail
MAX_TEMPLATES = 25                  # keeps /template list readable and autocomplete complete
# ────────────────────────────────────────────────────────────────────────────────

GUILD = discord.Object(id=GUILD_ID)
HEX_RE = re.compile(r"^#?([0-9a-fA-F]{6})$")
TEMPLATE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _\-]{0,39}$")


# ───────────────────────────── storage (templates) ─────────────────────────────
class TemplateStore:
    """Saves templates to data/templates.json. Writes are atomic."""

    def __init__(self, path: Path):
        self.path = path
        self.templates: dict[str, dict] = {}   # key = lowercase name
        self._load()

    def _load(self):
        try:
            with open(self.path, encoding="utf-8") as f:
                self.templates = json.load(f)
        except FileNotFoundError:
            return
        except (json.JSONDecodeError, OSError) as e:
            # Don't silently overwrite a damaged file: keep a copy and start fresh.
            print(f"TemplateStore: could not read {self.path}: {e!r}")
            try:
                os.replace(self.path, self.path.with_suffix(".json.bak"))
            except OSError:
                pass

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.templates, f, indent=2, ensure_ascii=False)
        os.replace(tmp, self.path)

    def get(self, name: str) -> Optional[dict]:
        return self.templates.get(name.strip().lower())

    def save(self, name: str, data: dict):
        self.templates[name.strip().lower()] = {"name": name.strip(), **data}
        self._save()

    def delete(self, name: str) -> bool:
        if self.templates.pop(name.strip().lower(), None) is None:
            return False
        self._save()
        return True


store = TemplateStore(TEMPLATES_FILE)


# ───────────────────────────────────── helpers ─────────────────────────────────────
def parse_color(value: Optional[str]) -> discord.Color:
    if value:
        m = HEX_RE.match(value.strip())
        if m:
            return discord.Color(int(m.group(1), 16))
    return discord.Color(int(THEME["accent"].lstrip("#"), 16))


def hex_to_color(value: str) -> discord.Color:
    return discord.Color(int(value.lstrip("#"), 16))


def color_to_hex(color: discord.Color) -> str:
    return f"#{color.value:06X}"


def clean_url(value: Optional[str]) -> Optional[str]:
    value = (value or "").strip()
    return value if value.startswith(("http://", "https://")) else None


# "#rules" -> clickable <#id> channel mention (skips things already like <#123>, URLs, etc.)
CHANNEL_REF_RE = re.compile(r"(?<![<\w/&=])#([^\s#<>]+)")


def resolve_channel_mentions(guild: discord.Guild, text: str) -> str:
    """Turn #channel-name in the message into real channel links, which Discord
    shows as a clickable #channel. Unknown names are left exactly as typed."""
    by_name = {}
    for ch in guild.channels:
        if not isinstance(ch, discord.CategoryChannel):
            by_name.setdefault(ch.name.lower(), ch)

    def repl(m: re.Match) -> str:
        token = m.group(1)
        trailing = ""
        # allow punctuation straight after the name, e.g. "see #rules."
        while token and token.lower() not in by_name and token[-1] in ".,!?;:)":
            trailing = token[-1] + trailing
            token = token[:-1]
        ch = by_name.get(token.lower())
        return f"{ch.mention}{trailing}" if ch else m.group(0)

    return CHANNEL_REF_RE.sub(repl, text)


def brand_icon(guild: discord.Guild) -> Optional[str]:
    """Bot avatar (the cobra logo) if enabled, otherwise the server icon."""
    if THEME["use_bot_avatar"] and guild.me is not None:
        return guild.me.display_avatar.url
    return guild.icon.url if guild.icon else None


def is_staff(member: discord.abc.User) -> bool:
    if not isinstance(member, discord.Member):
        return False
    if member.id == member.guild.owner_id:
        return True
    if member.guild_permissions.administrator:
        return True
    return any(r.id in MOD_ROLE_IDS for r in member.roles)


def staff_only():
    async def predicate(interaction: discord.Interaction) -> bool:
        if is_staff(interaction.user):
            return True
        raise app_commands.CheckFailure("staff only")

    return app_commands.check(predicate)


class StaffGroup(app_commands.Group):
    """Command group where every subcommand is staff-only."""

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return is_staff(interaction.user)


def build_embed(
    kind: str,
    guild: discord.Guild,
    title: str,
    description: str,
    color: discord.Color,
    image: Optional[str],
    thumbnail: Optional[str],
    footer: Optional[str],
) -> discord.Embed:
    icon = brand_icon(guild)
    stamp = datetime.now(timezone.utc) if THEME["timestamp"] else None

    if kind == "announce":
        embed = discord.Embed(
            title=f"{THEME['announce_prefix']}  {title}".strip(),
            description=(f"{THEME['divider']}\n\n" if THEME["divider"] else "") + description,
            color=color,
            timestamp=stamp,
        )
        embed.set_author(name=f"{guild.name} • {THEME['announce_label']}", icon_url=icon)
    else:
        embed = discord.Embed(
            title=title or None, description=description, color=color, timestamp=stamp
        )

    # Thumbnail: custom URL > theme default > bot avatar. Type "none" to hide it.
    if thumbnail != NO_THUMB:
        thumb = thumbnail or THEME["default_thumbnail"] or icon
        if thumb:
            embed.set_thumbnail(url=thumb)

    if image:
        embed.set_image(url=image)

    footer_text = footer or THEME["footer_text"]
    if footer_text:
        footer_icon = THEME["footer_icon"] or brand_icon(guild)
        embed.set_footer(text=footer_text, icon_url=footer_icon)
    return embed


def embed_from_data(guild: discord.Guild, d: dict, color: discord.Color) -> discord.Embed:
    """Build an embed from a payload dict (modal fields or a saved template)."""
    thumb_raw = (d.get("thumb") or "").strip()
    thumbnail = NO_THUMB if thumb_raw.lower() == NO_THUMB else clean_url(thumb_raw)
    return build_embed(
        d["kind"],
        guild,
        d["title"],
        resolve_channel_mentions(guild, d["description"]),
        color,
        clean_url(d.get("image")),
        thumbnail,
        (d.get("footer") or "").strip() or None,
    )


def channel_ok(interaction: discord.Interaction, channel: discord.TextChannel) -> Optional[str]:
    perms = channel.permissions_for(interaction.guild.me)
    if not (perms.view_channel and perms.send_messages and perms.embed_links):
        return f"❌ I need View Channel, Send Messages and Embed Links in {channel.mention}."
    return None


# ──────────────────────────────── UI: confirm + modals ────────────────────────────────
class SaveTemplateModal(discord.ui.Modal, title="Save as template"):
    name_in = discord.ui.TextInput(label="Template name", max_length=40, placeholder="weekly-event")

    def __init__(self, payload: dict):
        super().__init__()
        self.payload = payload

    async def on_submit(self, interaction: discord.Interaction):
        name = self.name_in.value.strip()
        if not TEMPLATE_NAME_RE.match(name):
            return await interaction.response.send_message(
                "❌ Use letters, numbers, spaces, `-` or `_` (max 40 characters).", ephemeral=True
            )
        existed = store.get(name) is not None
        if not existed and len(store.templates) >= MAX_TEMPLATES:
            return await interaction.response.send_message(
                f"❌ You've reached the limit of {MAX_TEMPLATES} templates. Delete one with `/template delete` first.",
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
        placeholder="Blank = cobra logo. Paste a link, or type none to hide it.",
    )
    footer_in = discord.ui.TextInput(label="Footer text (optional)", required=False, max_length=200)

    def __init__(self, kind, channel, color, role, prefill: Optional[dict] = None):
        super().__init__(title="New Announcement" if kind == "announce" else "New Embed")
        self.kind, self.channel, self.color, self.role = kind, channel, color, role
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
        embed = embed_from_data(interaction.guild, payload, self.color)

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


# ───────────────────────────────────── bot + commands ─────────────────────────────────────
class Bot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync(guild=GUILD)

    async def on_ready(self):
        print(f"Logged in as {self.user} ({self.user.id})")
        for g in self.guilds:
            if g.id != GUILD_ID:
                await g.leave()

    async def on_guild_join(self, guild: discord.Guild):
        if guild.id != GUILD_ID:
            await guild.leave()


bot = Bot()
tree = bot.tree


async def template_autocomplete(interaction: discord.Interaction, current: str):
    cur = current.lower()
    return [
        app_commands.Choice(name=t["name"], value=t["name"])
        for t in store.templates.values()
        if cur in t["name"].lower()
    ][:25]


# ── /announce and /embed ──
@tree.command(name="announce", description="Create a themed announcement embed", guild=GUILD)
@app_commands.describe(
    channel="Where to post it",
    ping="Role (or @everyone) to ping — optional",
    color="Hex color like #FF8800 — optional, defaults to the server theme",
)
@staff_only()
async def announce(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
    ping: Optional[discord.Role] = None,
    color: Optional[str] = None,
):
    if err := channel_ok(interaction, channel):
        return await interaction.response.send_message(err, ephemeral=True)
    await interaction.response.send_modal(EmbedModal("announce", channel, parse_color(color), ping))


@tree.command(name="embed", description="Create a custom embed message", guild=GUILD)
@app_commands.describe(channel="Where to post it", color="Hex color like #FF8800 — optional")
@staff_only()
async def embed(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
    color: Optional[str] = None,
):
    if err := channel_ok(interaction, channel):
        return await interaction.response.send_message(err, ephemeral=True)
    await interaction.response.send_modal(EmbedModal("embed", channel, parse_color(color), None))


# ── /template ──
template = StaffGroup(
    name="template", description="Saved templates for recurring posts", guild_only=True
)


@template.command(name="use", description="Post from a saved template (you can edit it before sending)")
@app_commands.describe(
    name="Template to use",
    channel="Where to post it",
    ping="Role (or @everyone) to ping — optional",
    color="Hex color like #FF8800 — optional, defaults to the template's saved color",
)
async def template_use(
    interaction: discord.Interaction,
    name: str,
    channel: discord.TextChannel,
    ping: Optional[discord.Role] = None,
    color: Optional[str] = None,
):
    t = store.get(name)
    if t is None:
        return await interaction.response.send_message(
            f"❌ No template named **{name}**. Try `/template list`.", ephemeral=True
        )
    if err := channel_ok(interaction, channel):
        return await interaction.response.send_message(err, ephemeral=True)
    col = parse_color(color) if color else hex_to_color(t["color"])
    await interaction.response.send_modal(EmbedModal(t["kind"], channel, col, ping, prefill=t))


@template.command(name="list", description="Show all saved templates")
async def template_list(interaction: discord.Interaction):
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
        color=parse_color(None),
    )
    await interaction.response.send_message(embed=listing, ephemeral=True)


@template.command(name="preview", description="Preview a saved template without posting")
@app_commands.describe(name="Template to preview")
async def template_preview(interaction: discord.Interaction, name: str):
    t = store.get(name)
    if t is None:
        return await interaction.response.send_message(f"❌ No template named **{name}**.", ephemeral=True)
    preview = embed_from_data(interaction.guild, t, hex_to_color(t["color"]))
    await interaction.response.send_message(
        f"**Preview** of template **{t['name']}**", embed=preview, ephemeral=True
    )


@template.command(name="delete", description="Delete a saved template")
@app_commands.describe(name="Template to delete")
async def template_delete(interaction: discord.Interaction, name: str):
    if store.delete(name):
        await interaction.response.send_message(f"🗑️ Deleted template **{name}**.", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ No template named **{name}**.", ephemeral=True)


for _cmd in (template_use, template_preview, template_delete):
    _cmd.autocomplete("name")(template_autocomplete)

tree.add_command(template, guild=GUILD)


@tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CheckFailure):
        msg = "🚫 This command is for the server owner, admins and mods only."
    else:
        msg = "⚠️ Something went wrong. Please try again."
        print(f"Command error: {error!r}")
    if interaction.response.is_done():
        await interaction.followup.send(msg, ephemeral=True)
    else:
        await interaction.response.send_message(msg, ephemeral=True)


if __name__ == "__main__":
    bot.run(TOKEN)
