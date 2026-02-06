import aiosqlite


SCHEMA = """
CREATE TABLE IF NOT EXISTS ctf_events (
  guild_id INTEGER PRIMARY KEY,
  ctftime_event_id INTEGER NOT NULL,
  event_title TEXT NOT NULL,
  category_id INTEGER NOT NULL,
  channels_json TEXT NOT NULL,
  start_time TEXT,
  finish_time TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scoreboard_config (
  guild_id INTEGER PRIMARY KEY,
  type TEXT NOT NULL,
  url TEXT NOT NULL,
  auth_token TEXT,
  scoreboard_channel_id INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS scoreboard_state (
  guild_id INTEGER PRIMARY KEY,
  last_hash TEXT,
  last_payload TEXT,
  updated_at TEXT NOT NULL
);
"""


async def init_db(db_path: str) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.executescript(SCHEMA)
        await db.commit()
