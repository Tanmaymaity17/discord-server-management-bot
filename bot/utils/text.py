"""Text / URL helpers."""
import re
from typing import Optional

import discord

# "#rules" -> clickable <#id> channel mention (skips things already like <#123>, URLs, etc.)
CHANNEL_REF_RE = re.compile(r"(?<![<\w/&=])#([^\s#<>]+)")


def clean_url(value: Optional[str]) -> Optional[str]:
    value = (value or "").strip()
    return value if value.startswith(("http://", "https://")) else None


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
