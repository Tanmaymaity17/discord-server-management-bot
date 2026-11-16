"""Bot class: profiles, per-server command registration/sync, guild guard."""
import asyncio

import discord
from discord.ext import commands

from bot import config
from bot.identity import apply_identity
from bot.profiles import FEATURE_COGS, ProfileManager
from bot.storage.templates import TemplateStores

CORE_COGS = ("errors", "profile", "identity")   # always loaded
ALL_COGS = CORE_COGS + FEATURE_COGS        # feature cogs are gated per server by the profile


class ServerBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=commands.when_mentioned,   # slash-only bot; no prefix commands
            intents=discord.Intents.default(),
        )
        self.profiles = ProfileManager(config.PROFILES_DIR)
        self.stores = TemplateStores(config.DATA_DIR)
        self._apply_lock = asyncio.Lock()
        self._identity_applied = False

    # ── helpers used by cogs ──
    def store_for(self, guild_id: int):
        return self.stores.get(guild_id)

    def guilds_for(self, cog: str) -> list[discord.Object]:
        return self.profiles.guilds_for(cog)

    # ── profile application ──
    async def apply_profiles(self):
        """(Re)load every cog against the current profiles, then sync each server's commands."""
        async with self._apply_lock:
            for name in ALL_COGS:
                ext = f"bot.cogs.{name}"
                if ext in self.extensions:
                    await self.reload_extension(ext)
                else:
                    await self.load_extension(ext)
            for gid in self.profiles.guild_ids():
                try:
                    await self.tree.sync(guild=discord.Object(id=gid))
                except discord.HTTPException as e:
                    # e.g. bot isn't in that server yet; don't let one server block the rest
                    print(f"Could not sync commands for guild {gid}: {e}")

    async def refresh(self) -> list[str]:
        """Re-read profiles from disk and re-apply. Returns a list of problems."""
        problems = self.profiles.reload()
        await self.apply_profiles()
        return problems

    async def apply_identities(self, force: bool = False) -> dict[str, list[str]]:
        """Apply each configured server's identity (nickname/bio/avatar/banner). Returns {profile name: lines}."""
        report: dict[str, list[str]] = {}
        for p in self.profiles.all():
            guild = self.get_guild(p.guild_id)
            if guild is None:
                continue
            try:
                report[p.name] = await apply_identity(self, p, guild, force=force)
            except Exception as e:   # one server must never block the others
                report[p.name] = [f"❌ unexpected error: {e!r}"]
        return report

    # ── lifecycle ──
    async def setup_hook(self):
        for p in self.profiles.problems:
            print(f"Profile problem: {p}")
        if not self.profiles.all():
            print("WARNING: no valid server profiles found in profiles/. No commands will be registered.")
        await self.apply_profiles()

    async def on_ready(self):
        print(f"Logged in as {self.user} ({self.user.id})")
        print(f"Profiles: {[(p.name, p.guild_id) for p in self.profiles.all()]}")
        await self._leave_unknown_guilds()
        if not self._identity_applied:      # on_ready can fire again on reconnects
            self._identity_applied = True
            for name, lines in (await self.apply_identities()).items():
                print(f"Identity [{name}]: " + " | ".join(lines))

    async def _leave_unknown_guilds(self):
        # Safety: never auto-leave when profiles are missing or broken (a typo shouldn't kick the bot).
        if not self.profiles.all() or self.profiles.problems:
            print("Skipping auto-leave of unknown servers because profiles are empty or have problems.")
            return
        for g in self.guilds:
            if self.profiles.get(g.id) is None:
                print(f"Leaving unconfigured server {g.name} ({g.id})")
                await g.leave()

    async def on_guild_join(self, guild: discord.Guild):
        # Allow adding a profile file and then inviting the bot without a restart.
        if self.profiles.get(guild.id) is None:
            await self.refresh()
        if self.profiles.get(guild.id) is None:
            print(f"Joined unconfigured server {guild.name} ({guild.id}); leaving.")
            await guild.leave()
        else:
            await self.apply_profiles()
            profile = self.profiles.get(guild.id)
            try:
                for line in await apply_identity(self, profile, guild):
                    print(f"Identity [{profile.name}]: {line}")
            except Exception as e:
                print(f"Identity [{profile.name}] failed: {e!r}")
