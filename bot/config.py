"""Global (non-server-specific) configuration: secrets, paths, defaults, limits.

Anything that differs per server (guild id, mod roles, theme, enabled features)
lives in profiles/<name>.json, see bot/profiles.py.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

TOKEN = os.environ["DISCORD_TOKEN"]

PROFILES_DIR = ROOT_DIR / "profiles"
DATA_DIR = ROOT_DIR / "data"          # runtime data: data/<guild_id>/templates.json
ASSETS_DIR = ROOT_DIR / "assets"      # per-server images: assets/<profile name>/pfp.png, banner.png

# Fallback look for any server whose profile doesn't override a key.
DEFAULT_THEME = {
    "accent": "#5865F2",            # embed color (hex)
    "announce_prefix": "📢",        # shown before announcement titles
    "announce_label": "Announcement",
    "footer_text": "",              # default footer; "" = no footer unless typed in the form
    "footer_icon": None,            # URL or None (None = bot avatar / server icon)
    "divider": "",                  # line under announcement titles; "" to disable
    "default_thumbnail": None,      # URL or None (None = bot avatar / server icon)
    "use_bot_avatar": True,         # use the bot's avatar for author/footer/thumbnail
    "timestamp": True,              # show the time on every embed
}

NO_THUMB = "none"                   # typing this in the thumbnail field hides the thumbnail
MAX_TEMPLATES = 25                  # per server
