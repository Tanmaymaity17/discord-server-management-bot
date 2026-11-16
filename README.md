# 🐍 Server Management Bot

A local, multi-server Discord utility bot. It started as the **Team Cobra Official Bot** and now runs any number of servers from one process, each with its own look, staff roles, features and saved data.

Staff post themed announcements and custom embeds through a simple form, with a live preview, optional role pings and reusable saved templates. Each server can also give the bot its own nickname, bio, avatar and banner.

## Features

- **Multi-server**: one profile file per server decides its theme, staff roles, features and bot identity
- **`/announce`**: themed announcement embed with an optional role or `@everyone` ping
- **`/embed`**: general-purpose custom embed (no ping)
- **Form-based**: title, message, banner image, thumbnail and footer are filled in through a pop-up form
- **Preview before sending**: check the embed, then **Send**, **Save as template**, or **Cancel**
- **Saved templates**: store recurring posts (events, giveaways, rules) and reuse them in seconds, separately per server
- **Per-server bot identity**: nickname, bio, avatar and banner, applied automatically from the profile
- **Per-server staff roles**: the server owner, Administrators and that server's own mod roles
- **Per-server features**: each profile switches features on or off
- **Clickable channel links**: type `#rules` in a message and it becomes a real channel link
- **Role mentions** (`<@&ROLE_ID>`) are shown as role names inside embeds without pinging anyone
- **Runs locally**: your token, profiles and data stay on your machine; nothing is sent anywhere except Discord
- **Safe by default**: the bot leaves any server that has no profile, and a broken profile edit never takes a server offline

## Commands

| Command | Who | Description |
| --- | --- | --- |
| `/announce channel [ping] [color]` | Staff | Create a themed announcement embed |
| `/embed channel [color]` | Staff | Create a custom embed |
| `/template use name channel [ping] [color]` | Staff | Post from a saved template (opens a prefilled form you can edit) |
| `/template list` | Staff | Show this server's saved templates |
| `/template preview name` | Staff | Preview a saved template without posting |
| `/template delete name` | Staff | Delete a saved template |
| `/profile show` | Staff | Show this server's active profile, and warn about mod role IDs that don't exist in the server |
| `/identity apply [force]` | Staff | Apply this server's nickname, bio, avatar and banner now. `force` re-sends everything. 30-second cooldown per server |
| `/profile reload` | Bot owner | Re-read all profiles from disk, reload features, re-sync commands and apply identities |

"Staff" means the server owner, members with the Administrator permission, and anyone with one of that server's `mod_role_ids`. The bot's owner (the person who owns the application) can also use `/profile` and `/identity`.

`color` is an optional hex code such as `#FF8800`. If left blank, the server's accent color is used (or the template's saved color).

### Writing messages

The message field supports Discord markdown: `**bold**`, `*italic*`, `> quotes`, lists, emojis and `[text](https://link)` links.

| You type | Result |
| --- | --- |
| `#rules` | Clickable link to the channel with that exact name |
| `<@&123456789>` | Role shown by name, no ping |
| `[Read this](https://example.com)` | Clickable text instead of a raw URL |
| `none` in the thumbnail field | Hides the thumbnail |

**Footer:** if you leave the footer field blank, the server's `footer_text` is used. If that is empty too, there is no footer.
**Thumbnail:** a link you paste wins, then the server's `default_thumbnail`, then the bot's avatar.

### Saving a template

1. Run `/announce` or `/embed` and fill in the form.
2. On the preview, press **💾 Save as template** and give it a name.
3. Reuse it later with `/template use`.

Press Save *before* pressing Send. The Save button disappears once the message has been sent. Each server has up to 25 templates, and a server never sees another server's templates.

## Setup

### 1. Requirements

- Python 3.10 or newer
- A Discord bot application ([Discord Developer Portal](https://discord.com/developers/applications))

### 2. Create the bot

1. In the Developer Portal, create an application, open the **Bot** tab and copy the bot token.
2. Turn **Public Bot** off, so only you can add it to servers.
3. No privileged intents are needed.

### 3. Install

```bash
git clone https://github.com/Tanmaymaity17/discord-server-management-bot.git
cd discord-server-management-bot

python -m venv venv
# Windows:  venv\Scripts\activate
# macOS/Linux:  source venv/bin/activate

pip install -r requirements.txt
```

### 4. Add your token

Copy `.env.example` to `.env` and fill it in:

```env
DISCORD_TOKEN=your-bot-token
```

That is the only value needed. Server IDs and roles live in profiles, not in `.env`.

### 5. Create a server profile

Copy `profiles/_example.json` to `profiles/<name>.json` (for example `profiles/my_server.json`) and edit it. See [Profiles](#profiles) below. In Discord, turn on Developer Mode (Settings → Advanced) to copy IDs: right-click the server icon for **Copy Server ID**, and right-click a role in Server Settings → Roles for **Copy Role ID**.

### 6. Invite the bot

Create the profile **before** inviting, because the bot leaves any server that has no profile. In the Developer Portal, open OAuth2 → URL Generator and tick:

- Scopes: `bot` and `applications.commands`
- Permissions: View Channels, Send Messages, Embed Links, and Change Nickname (needed for the per-server nickname)

### 7. Run

```bash
python main.py
```

Slash commands are synced to each configured server on startup, so they appear within moments. The bot only works while this script is running; when it is offline the commands still show in Discord but won't respond.

## Profiles

Every server is one JSON file in `profiles/`. Files starting with `_` (like `_example.json`) are ignored. Only `guild_id` is required; anything left out falls back to a neutral default.

```json
{
  "guild_id": 123456789012345678,
  "name": "Example Server",
  "mod_role_ids": [111111111111111111, 222222222222222222],
  "enabled_cogs": ["announce", "templates"],
  "theme": {
    "accent": "#5865F2",
    "announce_prefix": "📢",
    "announce_label": "Announcement",
    "footer_text": "Example Server",
    "divider": "",
    "timestamp": true
  },
  "identity": {
    "nickname": "Example Bot",
    "bio": "Short bio shown on the bot's profile in this server",
    "avatar": "pfp.png",
    "banner": "banner.png"
  }
}
```

| Key | Meaning |
| --- | --- |
| `guild_id` | The server's ID. Required, and must be unique across profiles |
| `name` | A label for you, shown in `/profile show` and in the console. It does not change anything in Discord. Give each server a different one |
| `mod_role_ids` | Roles that count as staff in this server. The owner and Administrators always do. Empty means owner and Administrators only |
| `enabled_cogs` | Features this server gets: `announce` (`/announce`, `/embed`) and `templates` (`/template ...`). If the key is missing, all features are on |
| `theme` | Look of this server's embeds, see below |
| `identity` | The bot's nickname, bio, avatar and banner in this server, see below |

`/profile show`, `/identity apply` and `/profile reload` are always available and don't need to be listed in `enabled_cogs`.

### Theme

Any key you leave out uses the default.

| Key | Default | What it does |
| --- | --- | --- |
| `accent` | `#5865F2` | Default embed color |
| `announce_prefix` | `📢` | Emoji or text before the title on `/announce` embeds |
| `announce_label` | `Announcement` | Label in the author line, after the server name |
| `footer_text` | empty | Default footer for all embeds |
| `footer_icon` | none | Footer icon URL (none uses the bot avatar or server icon) |
| `divider` | empty | Line shown under announcement titles (`""` to disable) |
| `default_thumbnail` | none | Thumbnail used when none is typed (none uses the bot avatar or server icon) |
| `use_bot_avatar` | `true` | Use the bot's avatar for the author, footer and thumbnail |
| `timestamp` | `true` | Show the time on every embed |

### Identity

Set the bot's look for this server only. The bot's global name and avatar are never changed.

| Value | Meaning |
| --- | --- |
| key missing or `null` | Not managed, left exactly as it is |
| `""` | Clear it back to default |
| `"text"` or `"file.png"` | Set it |

- **Images** go in `assets/<profile file name>/`, for example `assets/my_server/pfp.png` for `profiles/my_server.json`. Formats: png, jpg, gif, webp, up to 10 MB. Paths outside that folder are rejected.
- **Limits:** nickname 32 characters, bio 190 characters.
- **Permissions:** the bot needs **Change Nickname** for the nickname.
- **When it applies:** on startup, after `/profile reload`, when the bot joins a configured server, and on `/identity apply`.
- **Only changes are sent.** A hash of what was applied is kept in `data/<guild_id>/identity_state.json`, so Discord is only called when something changed. This matters because Discord rate-limits avatar changes. Use `/identity apply force:True` to re-send everything.
- Animated images may be refused by Discord depending on the server's setup. The result message shows the exact error.

### Reloading

After editing a profile, run `/profile reload` (or restart the bot). If a file has a mistake, the reload message says what is wrong and which file. A server that was working keeps its previous version until you fix it.

## Adding a server

1. Create `profiles/<name>.json` with the new server's `guild_id`, mod roles, theme and identity.
2. Put any images in `assets/<name>/`.
3. Invite the bot (see [step 6](#6-invite-the-bot)).
4. If the bot is running, the profile is picked up when it joins. If it was already in the server, run `/profile reload`.
5. In the new server, run `/profile show` to check the setup, and `/identity apply` to confirm the identity applied.

No code changes are needed.

## Upgrading from the old single-file bot

If you used the old `bot.py` with `GUILD_ID` and `MOD_ROLE_IDS` in `.env`:

1. Create a profile with those values: `guild_id` from `GUILD_ID`, `mod_role_ids` from `MOD_ROLE_IDS`, and your old `THEME` values under `theme`.
2. Move `data/templates.json` to `data/<guild_id>/templates.json`.
3. Remove `GUILD_ID` and `MOD_ROLE_IDS` from `.env`. They are no longer read.

## Data storage

Everything is stored locally and never leaves your machine except what is posted to Discord.

| Path | Contents |
| --- | --- |
| `.env` | Your bot token |
| `profiles/<name>.json` | One server's configuration |
| `assets/<name>/` | That server's identity images |
| `data/<guild_id>/templates.json` | That server's saved templates |
| `data/<guild_id>/identity_state.json` | What identity values were last applied |

Back up `profiles/`, `assets/` and `data/` to keep your setup. `data/` is created automatically and holds server-specific content, so it should stay out of git, along with `.env`.

## Project structure

```text
.
├── main.py                    # entry point
├── requirements.txt           # dependencies
├── .env                       # your token (never committed)
├── bot/
│   ├── client.py              # bot class, loads features, per-server command sync
│   ├── config.py              # paths, default theme, limits
│   ├── profiles.py            # loads and validates profiles
│   ├── identity.py            # nickname / bio / avatar / banner per server
│   ├── checks.py              # staff checks and channel permission guard
│   ├── cogs/                  # one file per feature
│   │   ├── announce.py        # /announce, /embed
│   │   ├── templates.py       # /template ...
│   │   ├── profile.py         # /profile show, reload
│   │   ├── identity.py        # /identity apply
│   │   └── errors.py          # global error messages
│   ├── embeds/builder.py      # builds embeds from a server's theme
│   ├── storage/templates.py   # per-server template storage
│   ├── ui/                    # forms and preview buttons
│   └── utils/                 # color and text helpers
├── profiles/
│   ├── _example.json          # template for new servers
│   └── <server>.json          # one per server
├── assets/<server>/           # identity images
└── data/<guild_id>/           # runtime data, created automatically
```

## Adding a feature

Each feature is one cog file in `bot/cogs/`:

1. Create `bot/cogs/yourfeature.py`. Its `setup` function should only register the cog for servers that enabled it:

   ```python
   async def setup(bot):
       guilds = bot.guilds_for("yourfeature")
       if guilds:
           await bot.add_cog(YourCog(bot), guilds=guilds)
   ```

2. Add `"yourfeature"` to `FEATURE_COGS` in `bot/profiles.py`.
3. Each server turns it on by adding `"yourfeature"` to its `enabled_cogs`, then `/profile reload`.

## Troubleshooting

| Problem | What to check |
| --- | --- |
| Commands don't appear in a server | The server has a valid profile, the feature is in its `enabled_cogs`, and the bot was invited with the `applications.commands` scope. Run `/profile reload` |
| "This command is for the server owner, admins and mods only" | The person has none of that server's `mod_role_ids`. Run `/profile show` to check the role IDs |
| Bot left a server | That server had no profile. Create one, then invite the bot again |
| Identity field shows ❌ | The message gives the reason: a missing image file, a missing **Change Nickname** permission, or Discord refusing the value |
| `/profile reload` reports a problem | Fix the file it names. The previous working version stays active meanwhile |
| Commands show but don't respond | The bot isn't running |

## Security

Never commit `.env` or share your bot token. If a token is ever exposed, reset it right away in the Developer Portal under **Bot → Reset Token**, then update `.env`. Keep **Public Bot** switched off so only you can add the bot to servers.