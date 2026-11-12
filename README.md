# 🐍 Team Cobra Official Bot

A custom, single-server Discord utility bot for **Team Cobra**. It lets staff post themed announcements and custom embeds through a simple form, with a live preview, optional role pings, and reusable saved templates.

## Features

- **`/announce`**: themed announcement embed with an optional role or `@everyone` ping
- **`/embed`**: general-purpose custom embed (no ping)
- **Form-based**: title, message, banner image, thumbnail and footer are filled in through a pop-up form
- **Preview before sending**: check the embed, then **Send**, **Save as template**, or **Cancel**
- **Saved templates**: store recurring posts (events, giveaways, rules) and reuse them in seconds
- **Clickable channel links**: type `#rules` in a message and it becomes a real channel link
- **Role mentions** (`<@&ROLE_ID>`) are shown as role names inside embeds without pinging anyone
- **Default footer** applied to every embed unless you type your own
- **Staff-only**: usable by the server owner, Administrators and configured mod roles
- **Single server**: the bot leaves any server other than the configured one

## Commands

| Command | Description |
| --- | --- |
| `/announce channel [ping] [color]` | Create a themed announcement embed |
| `/embed channel [color]` | Create a custom embed |
| `/template use name channel [ping] [color]` | Post from a saved template (opens a prefilled form you can edit) |
| `/template list` | Show all saved templates |
| `/template preview name` | Preview a saved template without posting |
| `/template delete name` | Delete a saved template |

`color` is an optional hex code such as `#FF8800`. If left blank, the theme color is used (or the template's saved color).

### Writing messages

The message field supports Discord markdown: `**bold**`, `*italic*`, `> quotes`, lists, emojis and `[text](https://link)` links.

| You type | Result |
| --- | --- |
| `#rules` | Clickable link to the channel with that exact name |
| `<@&123456789>` | Role shown by name, no ping |
| `[Read this](https://example.com)` | Clickable text instead of a raw URL |
| `none` in the thumbnail field | Hides the thumbnail |

### Saving a template

1. Run `/announce` or `/embed` and fill in the form.
2. On the preview, press **💾 Save as template** and give it a name.
3. Reuse it later with `/template use`.

Press Save *before* pressing Send. The Save button disappears once the message has been sent.

## Setup

### 1. Requirements

- Python 3.10 or newer
- A Discord bot application ([Discord Developer Portal](https://discord.com/developers/applications))

### 2. Create and invite the bot

1. In the Developer Portal, create an application, open the **Bot** tab and copy the bot token.
2. No privileged intents are needed.
3. Invite the bot with the `bot` and `applications.commands` scopes and these permissions:
   - View Channels
   - Send Messages
   - Embed Links

### 3. Install

```bash
git clone <https://github.com/Tanmaymaity17/discord-server-management-bot.git>

python -m venv venv
# Windows:  venv\Scripts\activate
# macOS/Linux:  source venv/bin/activate

pip install -r requirements.txt
```

### 4. Configure

Copy `.env.example` to `.env` and fill it in:

```env
DISCORD_TOKEN=your-bot-token
GUILD_ID=your-server-id
MOD_ROLE_IDS=123456789012345678,234567890123456789
```

| Variable | Description |
| --- | --- |
| `DISCORD_TOKEN` | Bot token from the Developer Portal |
| `GUILD_ID` | ID of your server (enable Developer Mode, then right-click the server and Copy Server ID) |
| `MOD_ROLE_IDS` | Optional. Comma-separated role IDs allowed to use the commands. The owner and Administrators always can |

### 5. Run

```bash
python bot.py
```

Slash commands are synced to your server on startup, so they appear within moments. The bot only works while this script is running.

## Customizing the look

Edit the `THEME` block near the top of `bot.py`:

| Setting | What it does |
| --- | --- |
| `accent` | Default embed color |
| `announce_prefix` / `announce_label` | Emoji before the title and the label in the author line |
| `footer_text` | Default footer for all embeds |
| `divider` | Line shown under announcement titles (`""` to disable) |
| `default_thumbnail` / `use_bot_avatar` | Thumbnail and icon behavior |
| `timestamp` | Show the time on every embed |

## Data storage

Templates are stored locally in `data/templates.json` (created automatically next to `bot.py`). Back up this file to keep your templates. It is excluded from git, since it holds server-specific content.

## Project structure

```text
.
├── bot.py             # the bot
├── requirements.txt   # dependencies
├── .env               # your real secrets (never committed)
└── data/
    └── templates.json # saved templates (created automatically)
```

## Security

Never commit `.env` or share your bot token. If a token is ever exposed, reset it right away in the Developer Portal under **Bot → Reset Token**.