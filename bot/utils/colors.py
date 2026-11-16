"""Color helpers."""
import re
from typing import Optional

import discord

HEX_RE = re.compile(r"^#?([0-9a-fA-F]{6})$")


def parse_color(value: Optional[str], fallback: discord.Color) -> discord.Color:
    """User-typed hex -> Color. Falls back to `fallback` (the server's accent)."""
    if value:
        m = HEX_RE.match(value.strip())
        if m:
            return discord.Color(int(m.group(1), 16))
    return fallback


def hex_to_color(value: str) -> discord.Color:
    return discord.Color(int(value.lstrip("#"), 16))


def color_to_hex(color: discord.Color) -> str:
    return f"#{color.value:06X}"
