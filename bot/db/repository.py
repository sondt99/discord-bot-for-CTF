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
    ctftime_event_id: int
    type: str
    url: str
    auth_token: str | None
    team_name: str | None
    scoreboard_channel_id: int


@dataclass
class ScoreboardState:
    guild_id: int
    ctftime_event_id: int
    last_hash: str | None
    last_payload: str | None
    updated_at: str


@dataclass
class Challenge:
    id: int
    guild_id: int
    ctftime_event_id: int
    challenge_name: str
    category: str
    thread_id: int
    channel_id: int
    status: str
    solved_by: list[int]
    created_at: str
    solved_at: str | None


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
                ON CONFLICT(guild_id, ctftime_event_id) DO UPDATE SET
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

    async def get_ctf_event(
        self, guild_id: int, ctftime_event_id: int
    ) -> CtfEvent | None:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT guild_id, ctftime_event_id, event_title, category_id, channels_json, start_time, finish_time, created_at
                FROM ctf_events WHERE guild_id=? AND ctftime_event_id=?
                """,
                (guild_id, ctftime_event_id),
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

    async def list_ctf_events(self, guild_id: int) -> list[CtfEvent]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT guild_id, ctftime_event_id, event_title, category_id, channels_json, start_time, finish_time, created_at
                FROM ctf_events WHERE guild_id=? ORDER BY created_at DESC
                """,
                (guild_id,),
            )
            rows = await cursor.fetchall()
            await cursor.close()
        return [
            CtfEvent(
                guild_id=row[0],
                ctftime_event_id=row[1],
                event_title=row[2],
                category_id=row[3],
                channels=json.loads(row[4]),
                start_time=row[5],
                finish_time=row[6],
                created_at=row[7],
            )
            for row in rows
        ]

    async def delete_ctf_event(self, guild_id: int, ctftime_event_id: int) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM challenges WHERE guild_id=? AND ctftime_event_id=?",
                (guild_id, ctftime_event_id),
            )
            await db.execute(
                "DELETE FROM scoreboard_state WHERE guild_id=? AND ctftime_event_id=?",
                (guild_id, ctftime_event_id),
            )
            await db.execute(
                "DELETE FROM scoreboard_config WHERE guild_id=? AND ctftime_event_id=?",
                (guild_id, ctftime_event_id),
            )
            await db.execute(
                "DELETE FROM ctf_events WHERE guild_id=? AND ctftime_event_id=?",
                (guild_id, ctftime_event_id),
            )
            await db.commit()

    async def upsert_scoreboard_config(
        self,
        guild_id: int,
        ctftime_event_id: int,
        type_name: str,
        url: str,
        auth_token: str | None,
        team_name: str | None,
        scoreboard_channel_id: int,
    ) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO scoreboard_config
                  (guild_id, ctftime_event_id, type, url, auth_token, team_name, scoreboard_channel_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(guild_id, ctftime_event_id) DO UPDATE SET
                  type=excluded.type,
                  url=excluded.url,
                  auth_token=excluded.auth_token,
                  team_name=excluded.team_name,
                  scoreboard_channel_id=excluded.scoreboard_channel_id
                """,
                (
                    guild_id,
                    ctftime_event_id,
                    type_name,
                    url,
                    auth_token,
                    team_name,
                    scoreboard_channel_id,
                ),
            )
            await db.commit()

    async def get_scoreboard_config(
        self, guild_id: int, ctftime_event_id: int
    ) -> ScoreboardConfig | None:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT guild_id, ctftime_event_id, type, url, auth_token, team_name, scoreboard_channel_id
                FROM scoreboard_config WHERE guild_id=? AND ctftime_event_id=?
                """,
                (guild_id, ctftime_event_id),
            )
            row = await cursor.fetchone()
            await cursor.close()
        if not row:
            return None
        return ScoreboardConfig(
            guild_id=row[0],
            ctftime_event_id=row[1],
            type=row[2],
            url=row[3],
            auth_token=row[4],
            team_name=row[5],
            scoreboard_channel_id=row[6],
        )

    async def list_scoreboard_configs(self) -> list[ScoreboardConfig]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT guild_id, ctftime_event_id, type, url, auth_token, team_name, scoreboard_channel_id
                FROM scoreboard_config
                """
            )
            rows = await cursor.fetchall()
            await cursor.close()
        return [
            ScoreboardConfig(
                guild_id=row[0],
                ctftime_event_id=row[1],
                type=row[2],
                url=row[3],
                auth_token=row[4],
                team_name=row[5],
                scoreboard_channel_id=row[6],
            )
            for row in rows
        ]

    async def delete_scoreboard_config(self, guild_id: int, ctftime_event_id: int) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM scoreboard_config WHERE guild_id=? AND ctftime_event_id=?",
                (guild_id, ctftime_event_id),
            )
            await db.execute(
                "DELETE FROM scoreboard_state WHERE guild_id=? AND ctftime_event_id=?",
                (guild_id, ctftime_event_id),
            )
            await db.commit()

    async def upsert_scoreboard_state(
        self,
        guild_id: int,
        ctftime_event_id: int,
        last_hash: str | None,
        last_payload: str | None,
    ) -> None:
        updated_at = _utc_now_iso()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO scoreboard_state (guild_id, ctftime_event_id, last_hash, last_payload, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(guild_id, ctftime_event_id) DO UPDATE SET
                  last_hash=excluded.last_hash,
                  last_payload=excluded.last_payload,
                  updated_at=excluded.updated_at
                """,
                (guild_id, ctftime_event_id, last_hash, last_payload, updated_at),
            )
            await db.commit()

    async def get_scoreboard_state(
        self, guild_id: int, ctftime_event_id: int
    ) -> ScoreboardState | None:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT guild_id, ctftime_event_id, last_hash, last_payload, updated_at
                FROM scoreboard_state WHERE guild_id=? AND ctftime_event_id=?
                """,
                (guild_id, ctftime_event_id),
            )
            row = await cursor.fetchone()
            await cursor.close()
        if not row:
            return None
        return ScoreboardState(
            guild_id=row[0],
            ctftime_event_id=row[1],
            last_hash=row[2],
            last_payload=row[3],
            updated_at=row[4],
        )

    # ── Challenge tracking ───────────────────────────────────────────

    def _row_to_challenge(self, row: tuple) -> Challenge:
        solved_by_raw = row[8]
        solved_by = json.loads(solved_by_raw) if solved_by_raw else []
        return Challenge(
            id=row[0],
            guild_id=row[1],
            ctftime_event_id=row[2],
            challenge_name=row[3],
            category=row[4],
            thread_id=row[5],
            channel_id=row[6],
            status=row[7],
            solved_by=solved_by,
            created_at=row[9],
            solved_at=row[10],
        )

    async def create_challenge(
        self,
        guild_id: int,
        ctftime_event_id: int,
        challenge_name: str,
        category: str,
        thread_id: int,
        channel_id: int,
    ) -> int:
        created_at = _utc_now_iso()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO challenges
                  (guild_id, ctftime_event_id, challenge_name, category,
                   thread_id, channel_id, status, solved_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 'open', NULL, ?)
                """,
                (guild_id, ctftime_event_id, challenge_name, category,
                 thread_id, channel_id, created_at),
            )
            challenge_id = cursor.lastrowid
            await db.commit()
        return challenge_id

    async def get_challenge_by_thread(self, thread_id: int) -> Challenge | None:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT id, guild_id, ctftime_event_id, challenge_name, category,
                       thread_id, channel_id, status, solved_by, created_at, solved_at
                FROM challenges WHERE thread_id=?
                """,
                (thread_id,),
            )
            row = await cursor.fetchone()
            await cursor.close()
        if not row:
            return None
        return self._row_to_challenge(row)

    async def mark_challenge_done(
        self, thread_id: int, solver_ids: list[int]
    ) -> None:
        solved_at = _utc_now_iso()
        solved_by_json = json.dumps(solver_ids)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                UPDATE challenges
                SET status='done', solved_by=?, solved_at=?
                WHERE thread_id=?
                """,
                (solved_by_json, solved_at, thread_id),
            )
            await db.commit()

    async def list_challenges(
        self, guild_id: int, ctftime_event_id: int
    ) -> list[Challenge]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT id, guild_id, ctftime_event_id, challenge_name, category,
                       thread_id, channel_id, status, solved_by, created_at, solved_at
                FROM challenges
                WHERE guild_id=? AND ctftime_event_id=?
                ORDER BY created_at ASC
                """,
                (guild_id, ctftime_event_id),
            )
            rows = await cursor.fetchall()
            await cursor.close()
        return [self._row_to_challenge(row) for row in rows]

    async def delete_challenges_for_event(
        self, guild_id: int, ctftime_event_id: int
    ) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM challenges WHERE guild_id=? AND ctftime_event_id=?",
                (guild_id, ctftime_event_id),
            )
            await db.commit()
