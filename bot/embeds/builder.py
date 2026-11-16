"""Embed construction. Everything visual comes from the server's theme."""
from datetime import datetime, timezone
from typing import Optional

import discord

from bot.config import NO_THUMB
from bot.utils.text import clean_url, resolve_channel_mentions


def brand_icon(guild: discord.Guild, theme: dict) -> Optional[str]:
    """Bot avatar if enabled, otherwise the server icon."""
    if theme["use_bot_avatar"] and guild.me is not None:
        return guild.me.display_avatar.url
    return guild.icon.url if guild.icon else None


def build_embed(
    kind: str,
    guild: discord.Guild,
    theme: dict,
    title: str,
    description: str,
    color: discord.Color,
    image: Optional[str],
    thumbnail: Optional[str],
    footer: Optional[str],
) -> discord.Embed:
    icon = brand_icon(guild, theme)
    stamp = datetime.now(timezone.utc) if theme["timestamp"] else None

    if kind == "announce":
        embed = discord.Embed(
            title=f"{theme['announce_prefix']}  {title}".strip(),
            description=(f"{theme['divider']}\n\n" if theme["divider"] else "") + description,
            color=color,
            timestamp=stamp,
        )
        embed.set_author(name=f"{guild.name} • {theme['announce_label']}", icon_url=icon)
    else:
        embed = discord.Embed(
            title=title or None, description=description, color=color, timestamp=stamp
        )

    # Thumbnail: custom URL > theme default > bot avatar. Type "none" to hide it.
    if thumbnail != NO_THUMB:
        thumb = thumbnail or theme["default_thumbnail"] or icon
        if thumb:
            embed.set_thumbnail(url=thumb)

    if image:
        embed.set_image(url=image)

    footer_text = footer or theme["footer_text"]
    if footer_text:
        footer_icon = theme["footer_icon"] or brand_icon(guild, theme)
        embed.set_footer(text=footer_text, icon_url=footer_icon)
    return embed


def embed_from_data(guild: discord.Guild, theme: dict, d: dict, color: discord.Color) -> discord.Embed:
    """Build an embed from a payload dict (modal fields or a saved template)."""
    thumb_raw = (d.get("thumb") or "").strip()
    thumbnail = NO_THUMB if thumb_raw.lower() == NO_THUMB else clean_url(thumb_raw)
    return build_embed(
        d["kind"],
        guild,
        theme,
        d["title"],
        resolve_channel_mentions(guild, d["description"]),
        color,
        clean_url(d.get("image")),
        thumbnail,
        (d.get("footer") or "").strip() or None,
    )
