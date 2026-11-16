"""Per-server profiles: one JSON file per server in profiles/.

Files starting with "_" (e.g. _example.json) are ignored.
A broken edit never takes a server offline: if a file that loaded before fails to
load again, the previous version is kept and the problem is reported.
"""
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import discord

from bot import config
from bot.utils.colors import HEX_RE, hex_to_color, parse_color

# Feature cogs that a profile can switch on/off via "enabled_cogs".
FEATURE_COGS = ("announce", "templates")
IDENTITY_FIELDS = ("nickname", "bio", "avatar", "banner")


@dataclass
class Profile:
    key: str                    # file name without .json
    guild_id: int
    name: str
    mod_role_ids: frozenset
    enabled_cogs: frozenset
    theme: dict                 # DEFAULT_THEME merged with the profile's overrides
    identity: dict              # nickname / bio / avatar / banner (see bot/identity.py)

    @property
    def accent_color(self) -> discord.Color:
        return hex_to_color(self.theme["accent"])

    def parse_color(self, value: Optional[str]) -> discord.Color:
        return parse_color(value, self.accent_color)


def _parse(path: Path) -> Profile:
    """Read one profile file. Raises ValueError with a readable message."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise ValueError(f"cannot read JSON ({e})")
    if not isinstance(raw, dict):
        raise ValueError("top level must be a JSON object")

    try:
        guild_id = int(raw["guild_id"])
    except (KeyError, TypeError, ValueError):
        raise ValueError("missing or invalid 'guild_id'")

    try:
        mod_roles = frozenset(int(x) for x in raw.get("mod_role_ids", []))
    except (TypeError, ValueError):
        raise ValueError("'mod_role_ids' must be a list of role ID numbers")

    cogs = raw.get("enabled_cogs", list(FEATURE_COGS))
    if not isinstance(cogs, list):
        raise ValueError("'enabled_cogs' must be a list")
    unknown = [c for c in cogs if c not in FEATURE_COGS]
    if unknown:
        raise ValueError(f"unknown enabled_cogs {unknown} (valid: {list(FEATURE_COGS)})")

    overrides = raw.get("theme", {})
    if not isinstance(overrides, dict):
        raise ValueError("'theme' must be an object")
    bad = [k for k in overrides if k not in config.DEFAULT_THEME]
    if bad:
        raise ValueError(f"unknown theme keys {bad} (valid: {list(config.DEFAULT_THEME)})")
    theme = {**config.DEFAULT_THEME, **overrides}
    m = HEX_RE.match(str(theme["accent"]).strip())
    if not m:
        raise ValueError(f"theme.accent must be a hex color like #E10600, got {theme['accent']!r}")
    theme["accent"] = "#" + m.group(1).upper()

    identity = raw.get("identity", {})
    if not isinstance(identity, dict):
        raise ValueError("'identity' must be an object")
    bad = [k for k in identity if k not in IDENTITY_FIELDS]
    if bad:
        raise ValueError(f"unknown identity keys {bad} (valid: {list(IDENTITY_FIELDS)})")
    for k, v in identity.items():
        if v is not None and not isinstance(v, str):
            raise ValueError(f"identity.{k} must be text or null")
    if len(identity.get("nickname") or "") > 32:
        raise ValueError("identity.nickname is longer than 32 characters")
    if len(identity.get("bio") or "") > 190:
        raise ValueError("identity.bio is longer than 190 characters")

    return Profile(
        key=path.stem,
        guild_id=guild_id,
        name=str(raw.get("name") or path.stem),
        mod_role_ids=mod_roles,
        enabled_cogs=frozenset(cogs),
        theme=theme,
        identity=identity,
    )


class ProfileManager:
    def __init__(self, directory: Path):
        self.directory = directory
        self._by_key: dict[str, Profile] = {}
        self._by_guild: dict[int, Profile] = {}
        self.problems: list[str] = []
        self.reload()

    def reload(self) -> list[str]:
        """Re-read every profile from disk. Returns a list of problems (empty = all good)."""
        self.directory.mkdir(parents=True, exist_ok=True)
        problems: list[str] = []
        new: dict[str, Profile] = {}
        used: dict[int, str] = {}

        for path in sorted(self.directory.glob("*.json")):
            if path.name.startswith("_"):
                continue
            try:
                prof = _parse(path)
            except ValueError as e:
                msg = f"{path.name}: {e}"
                old = self._by_key.get(path.stem)
                if old is not None:
                    new[path.stem] = old
                    used[old.guild_id] = path.name
                    msg += " (keeping the previous version)"
                problems.append(msg)
                continue
            if prof.guild_id in used:
                problems.append(f"{path.name}: guild_id {prof.guild_id} is already used by {used[prof.guild_id]}")
                continue
            used[prof.guild_id] = path.name
            new[prof.key] = prof

        self._by_key = new
        self._by_guild = {p.guild_id: p for p in new.values()}
        self.problems = problems
        return problems

    # ── lookups ──
    def get(self, guild_id: Optional[int]) -> Optional[Profile]:
        return self._by_guild.get(guild_id) if guild_id is not None else None

    def all(self) -> list[Profile]:
        return list(self._by_guild.values())

    def guild_ids(self) -> list[int]:
        return list(self._by_guild)

    def guild_objects(self) -> list[discord.Object]:
        return [discord.Object(id=g) for g in self._by_guild]

    def guilds_for(self, cog: str) -> list[discord.Object]:
        """Guilds whose profile has this feature cog enabled."""
        return [discord.Object(id=p.guild_id) for p in self._by_guild.values() if cog in p.enabled_cogs]
