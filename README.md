# Discord CTF Bot

Discord bot for CTFs. It fetches events from CTFtime, creates per-event categories and channels, and tracks realtime scoreboards for CTFd and rCTF.

## Features

- Upcoming CTF list with pagination (3 events per page).
- Join multiple CTFs per server (each gets its own category + channels).
- Scoreboard polling with change notifications (CTFd / rCTF).
- Admin-only management commands (hide, remove).
- Automatic admin-only BOT category for logs and DB backups.
- All bot responses use embeds.

## Requirements

- Python 3.11+
- Discord bot token
- Playwright (only needed for rCTF scoreboard capture)

## Quick setup

1. Create `.env` from `.env.example` and fill in values.
2. Install dependencies:

```
pip install -r requirements.txt
playwright install
```

3. Run the bot:

```
python -m bot.main
```

## Environment variables

Required:

- `DISCORD_TOKEN` — your bot token

Optional:

- `DATABASE_PATH` — path to SQLite DB (default: `ctf_bot.db`)
- `SCOREBOARD_POLL_SECONDS` — scoreboard polling interval in seconds (default: `90`)
- `SCOREBOARD_TOP_N` — top N teams to display in scoreboard updates (default: `10`)
- `TIMEZONE` — timezone offset for event times (example: `UTC+7`)
- `CTF_REMOVE_PASSWORD` — password required by `/ctf remove`

## Commands

CTF:

- `/ctf upcoming [limit]` — list upcoming CTFs (single embed per page).
- `/ctf join <event_id>` — create category + channels for an event.
- `/ctf list` — list joined CTFs and their IDs.
- `/ctf hidden [event_id]` — hide a CTF category from non-admins.
- `/ctf remove [event_id] password:<password>` — delete category + data (admin only, response is private).

Scoreboard:

- `/scoreboard <type> <url> [auth_token] [event_id]`
  - `type`: `CTFd` or `rCTF`
  - `url`: scoreboard URL or base URL
  - `auth_token`: optional
  - `event_id`: required when multiple CTFs exist in the server

## Channels created on join

Each joined CTF gets a category named after the event, with these text channels:

- `account` (read-only for everyone)
- `general`, `rev`, `pwn`, `web`, `crypto`, `for`, `misc`
- `scoreboard`

## BOT admin category

On startup, the bot ensures a private category named `BOT` with:

- `log` — command logs
- `backup` — a DB backup file after each slash command

Only admins and the bot can view this category.

## Permissions

The bot needs:

- `manage_channels` — create categories/channels, hide/remove
- `manage_messages` (optional) — if you plan to extend moderation features

If you keep the BOT category, admins must allow the bot to create private channels.

## Notes

- The bot does not create Discord scheduled events.
- Image thumbnails are disabled for CTF upcoming list.
- Do not commit your `.env` or token to Git.