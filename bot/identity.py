"""Per-server bot identity: nickname, bio, avatar and banner.

Uses Discord's "Modify Current Member" endpoint (PATCH /guilds/{id}/members/@me),
called through discord.py's HTTP layer, so it works whatever the installed
discord.py wraps. Only that one server's profile of the bot changes; the bot's
global username/avatar are never touched.

Profile semantics (profiles/<name>.json -> "identity"):
    key missing or null -> not managed, left exactly as it is
    ""                  -> clear it (back to default)
    "text" / "file.png" -> set it (images are read from assets/<profile name>/)

What was last applied is remembered in data/<guild_id>/identity_state.json (a hash
of the text / image bytes), so Discord is only called when something changed.
"""
import base64
import hashlib
import json
import os
from pathlib import Path

import discord
from discord.http import Route

from bot import config
from bot.profiles import Profile

# profile key -> Discord API key
FIELDS = (("nickname", "nick"), ("bio", "bio"), ("avatar", "avatar"), ("banner", "banner"))
IMAGE_FIELDS = {"avatar", "banner"}
IMAGE_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}
MAX_IMAGE_BYTES = 10 * 1024 * 1024


# ── state file ──
def _state_file(guild_id: int) -> Path:
    return config.DATA_DIR / str(guild_id) / "identity_state.json"


def _load_state(guild_id: int) -> dict:
    try:
        return json.loads(_state_file(guild_id).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def _save_state(guild_id: int, state: dict) -> None:
    path = _state_file(guild_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    os.replace(tmp, path)


# ── value preparation ──
def _read_image(profile: Profile, filename: str) -> tuple[str, str]:
    """Return (hash, data URI) for an image inside assets/<profile name>/. Raises ValueError."""
    base = (config.ASSETS_DIR / profile.key).resolve()
    path = (base / filename).resolve()
    if base not in path.parents:
        raise ValueError("file must be inside assets/" + profile.key + "/")
    if not path.is_file():
        raise ValueError(f"file not found: assets/{profile.key}/{filename}")
    mime = IMAGE_MIME.get(path.suffix.lower())
    if mime is None:
        raise ValueError(f"unsupported image type {path.suffix!r} (use png, jpg, gif or webp)")
    data = path.read_bytes()
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError(f"image is {len(data) / 1_048_576:.1f} MB, over the {MAX_IMAGE_BYTES // 1_048_576} MB limit")
    token = hashlib.sha256(data).hexdigest()
    return token, f"data:{mime};base64,{base64.b64encode(data).decode()}"


def _prepare(profile: Profile, field: str, value: str) -> tuple[str, object]:
    """Return (token, payload value). payload None clears the field."""
    if value == "":
        return "cleared", None
    if field in IMAGE_FIELDS:
        return _read_image(profile, value)
    return hashlib.sha256(value.encode("utf-8")).hexdigest(), value


# ── main entry ──
async def apply_identity(bot, profile: Profile, guild: discord.Guild, force: bool = False) -> list[str]:
    """Apply the profile's identity to `guild`. Returns human-readable result lines."""
    ident = profile.identity
    managed = [(f, k) for f, k in FIELDS if ident.get(f) is not None]
    if not managed:
        return ["➖ no identity set in this profile"]

    state = _load_state(guild.id)
    lines: list[str] = []
    dirty = False

    for field, key in managed:
        try:
            token, payload = _prepare(profile, field, ident[field])
        except (ValueError, OSError) as e:
            lines.append(f"❌ {field}: {e}")
            continue

        # Nickname is visible on the live member, so we can verify it directly.
        if field == "nickname" and not force and guild.me is not None and guild.me.nick == payload:
            if state.get(field) != token:
                state[field] = token
                dirty = True
            lines.append(f"➖ {field} unchanged")
            continue

        if not force and state.get(field) == token:
            lines.append(f"➖ {field} unchanged")
            continue

        try:
            await bot.http.request(
                Route("PATCH", "/guilds/{guild_id}/members/@me", guild_id=guild.id),
                json={key: payload},
                reason="Server identity applied from profile",
            )
        except discord.Forbidden:
            hint = " (the bot needs the Change Nickname permission)" if field == "nickname" else ""
            lines.append(f"❌ {field}: Discord refused it{hint}")
        except discord.HTTPException as e:
            lines.append(f"❌ {field}: {e.text or e.status}")
        else:
            state[field] = token
            dirty = True
            lines.append(f"✅ {field} {'cleared' if payload is None else 'updated'}")

    if dirty:
        _save_state(guild.id, state)
    return lines
