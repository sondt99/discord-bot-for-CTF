# Discord CTF Bot

Discord bot for CTFs: fetches events from CTFtime, creates categories/channels, and tracks realtime scoreboard updates (CTFd/rCTF).

## Quick setup

1. Create `.env` from `.env.example` and fill in the token.
2. Install dependencies:

```
pip install -r requirements.txt
playwright install
```

3. Run the bot:

```
python -m bot.main
```

## Commands

- `/ctf upcoming [limit]` — list upcoming CTFs (embed + pagination).
- `/ctf join <event_id>` — create category + channels for the event.
- `/scoreboard <type> <url> [auth_token]` — configure scoreboard polling.

## Notes

- The bot responds using embeds only.
- Requires `manage_channels` to create categories/channels.