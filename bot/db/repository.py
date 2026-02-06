import json
from dataclasses import dataclass
from datetime import datetime, timezone

import aiosqlite


@dataclass
class CtfEvent:
    guild_id: int
    ctftime_event_id: int
    event_title: str
    category_id: int
    channels: dict
    start_time: str | None
    finish_time: str | None
    created_at: str


@dataclass
class ScoreboardConfig:
    guild_id: int
    type: str
    url: str
    auth_token: str | None
    scoreboard_channel_id: int


@dataclass
class ScoreboardState:
    guild_id: int
    last_hash: str | None
    last_payload: str | None
    updated_at: str


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Repository:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    async def upsert_ctf_event(
        self,
        guild_id: int,
        ctftime_event_id: int,
        event_title: str,
        category_id: int,
        channels: dict,
        start_time: str | None,
        finish_time: str | None,
    ) -> None:
        channels_json = json.dumps(channels, ensure_ascii=False)
        created_at = _utc_now_iso()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO ctf_events
                  (guild_id, ctftime_event_id, event_title, category_id, channels_json, start_time, finish_time, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET
                  ctftime_event_id=excluded.ctftime_event_id,
                  event_title=excluded.event_title,
                  category_id=excluded.category_id,
                  channels_json=excluded.channels_json,
                  start_time=excluded.start_time,
                  finish_time=excluded.finish_time,
                  created_at=excluded.created_at
                """,
                (
                    guild_id,
                    ctftime_event_id,
                    event_title,
                    category_id,
                    channels_json,
                    start_time,
                    finish_time,
                    created_at,
                ),
            )
            await db.commit()

    async def get_ctf_event(self, guild_id: int) -> CtfEvent | None:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT guild_id, ctftime_event_id, event_title, category_id, channels_json, start_time, finish_time, created_at
                FROM ctf_events WHERE guild_id=?
                """,
                (guild_id,),
            )
            row = await cursor.fetchone()
            await cursor.close()
        if not row:
            return None
        return CtfEvent(
            guild_id=row[0],
            ctftime_event_id=row[1],
            event_title=row[2],
            category_id=row[3],
            channels=json.loads(row[4]),
            start_time=row[5],
            finish_time=row[6],
            created_at=row[7],
        )

    async def upsert_scoreboard_config(
        self,
        guild_id: int,
        type_name: str,
        url: str,
        auth_token: str | None,
        scoreboard_channel_id: int,
    ) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO scoreboard_config
                  (guild_id, type, url, auth_token, scoreboard_channel_id)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET
                  type=excluded.type,
                  url=excluded.url,
                  auth_token=excluded.auth_token,
                  scoreboard_channel_id=excluded.scoreboard_channel_id
                """,
                (guild_id, type_name, url, auth_token, scoreboard_channel_id),
            )
            await db.commit()

    async def get_scoreboard_config(self, guild_id: int) -> ScoreboardConfig | None:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT guild_id, type, url, auth_token, scoreboard_channel_id
                FROM scoreboard_config WHERE guild_id=?
                """,
                (guild_id,),
            )
            row = await cursor.fetchone()
            await cursor.close()
        if not row:
            return None
        return ScoreboardConfig(
            guild_id=row[0],
            type=row[1],
            url=row[2],
            auth_token=row[3],
            scoreboard_channel_id=row[4],
        )

    async def list_scoreboard_configs(self) -> list[ScoreboardConfig]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT guild_id, type, url, auth_token, scoreboard_channel_id
                FROM scoreboard_config
                """
            )
            rows = await cursor.fetchall()
            await cursor.close()
        return [
            ScoreboardConfig(
                guild_id=row[0],
                type=row[1],
                url=row[2],
                auth_token=row[3],
                scoreboard_channel_id=row[4],
            )
            for row in rows
        ]

    async def upsert_scoreboard_state(
        self, guild_id: int, last_hash: str | None, last_payload: str | None
    ) -> None:
        updated_at = _utc_now_iso()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO scoreboard_state (guild_id, last_hash, last_payload, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET
                  last_hash=excluded.last_hash,
                  last_payload=excluded.last_payload,
                  updated_at=excluded.updated_at
                """,
                (guild_id, last_hash, last_payload, updated_at),
            )
            await db.commit()

    async def get_scoreboard_state(self, guild_id: int) -> ScoreboardState | None:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT guild_id, last_hash, last_payload, updated_at
                FROM scoreboard_state WHERE guild_id=?
                """,
                (guild_id,),
            )
            row = await cursor.fetchone()
            await cursor.close()
        if not row:
            return None
        return ScoreboardState(
            guild_id=row[0],
            last_hash=row[1],
            last_payload=row[2],
            updated_at=row[3],
        )
