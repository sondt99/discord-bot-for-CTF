from __future__ import annotations

import json
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands, tasks

from bot.config import SCOREBOARD_POLL_SECONDS, SCOREBOARD_TEAM_NAME, SCOREBOARD_TOP_N
from bot.db.repository import Repository
from bot.services.scoreboard_fetcher import (
    fetch_ctfd_scoreboard,
    fetch_rctf_scoreboard,
    make_payload_hash,
)
from bot.utils.embeds import build_scoreboard_embed, build_simple_embed


class ScoreboardCog(commands.Cog):
    def __init__(self, bot: commands.Bot, repo: Repository) -> None:
        self.bot = bot
        self.repo = repo
        self.scoreboard_loop.start()
        self.bot.loop.create_task(self._run_initial_check())

    def cog_unload(self) -> None:
        self.scoreboard_loop.cancel()

    @app_commands.command(name="scoreboard", description="Configure scoreboard polling")
    @app_commands.describe(
        type="Scoreboard type (ctfd or rctf)",
        url="Scoreboard base URL",
        auth_token="Optional auth token",
        team="Team name to track (optional)",
        event_id="CTFtime event ID (required if multiple)",
    )
    @app_commands.choices(
        type=[
            app_commands.Choice(name="CTFd", value="ctfd"),
            app_commands.Choice(name="rCTF", value="rctf"),
        ]
    )
    async def scoreboard(
        self,
        interaction: discord.Interaction,
        type: app_commands.Choice[str],
        url: str,
        auth_token: str | None = None,
        team: str | None = None,
        event_id: int | None = None,
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                embed=build_simple_embed("Guild only", "Use this in a server."),
            )
            return
        await interaction.response.defer()

        events = await self.repo.list_ctf_events(interaction.guild.id)
        if not events:
            await interaction.followup.send(
                embed=build_simple_embed(
                    "No active CTF",
                    "Run /ctf join first to create channels.",
                )
            )
            return

        if event_id is None:
            if len(events) == 1:
                event = events[0]
            else:
                await interaction.followup.send(
                    embed=build_simple_embed(
                        "Need event ID",
                        "Multiple events in this server. Please provide event_id.",
                    )
                )
                return
        else:
            event = next(
                (e for e in events if e.ctftime_event_id == event_id), None
            )
            if event is None:
                await interaction.followup.send(
                    embed=build_simple_embed(
                        "Event not found",
                        f"Event ID {event_id} not found in this server.",
                    )
                )
                return

        scoreboard_channel_id = event.channels.get("Scoreboard")
        if not scoreboard_channel_id:
            await interaction.followup.send(
                embed=build_simple_embed(
                    "Missing channel", "Scoreboard channel not found."
                )
            )
            return

        await self.repo.upsert_scoreboard_config(
            guild_id=interaction.guild.id,
            ctftime_event_id=event.ctftime_event_id,
            type_name=type.value,
            url=url,
            auth_token=auth_token,
            team_name=team or SCOREBOARD_TEAM_NAME,
            scoreboard_channel_id=scoreboard_channel_id,
        )

        await interaction.followup.send(
            embed=build_simple_embed(
                "Scoreboard configured",
                (
                    f"Event ID: {event.ctftime_event_id}\nType: {type.name}\nURL: {url}"
                    + (
                        f"\nTeam: {team or SCOREBOARD_TEAM_NAME}"
                        if (team or SCOREBOARD_TEAM_NAME)
                        else ""
                    )
                ),
            )
        )

    async def _run_initial_check(self) -> None:
        await self.bot.wait_until_ready()
        await self._run_scoreboard_checks()

    @tasks.loop(seconds=SCOREBOARD_POLL_SECONDS)
    async def scoreboard_loop(self) -> None:
        await self.bot.wait_until_ready()
        await self._run_scoreboard_checks()

    async def _run_scoreboard_checks(self) -> None:
        if hasattr(self.bot, "backup_ready"):
            await self.bot.backup_ready.wait()
        configs = await self.repo.list_scoreboard_configs()

        for config in configs:
            event = await self.repo.get_ctf_event(
                config.guild_id, config.ctftime_event_id
            )
            if not event:
                continue

            if event.finish_time:
                try:
                    finish = datetime.fromisoformat(event.finish_time)
                    if datetime.now(timezone.utc) > finish:
                        continue
                except ValueError:
                    pass

            try:
                if config.type == "ctfd":
                    entries = await fetch_ctfd_scoreboard(config.url, config.auth_token)
                elif config.type == "rctf":
                    entries = await fetch_rctf_scoreboard(config.url, config.auth_token)
                else:
                    continue
            except Exception:
                continue

            tracked_team = config.team_name or SCOREBOARD_TEAM_NAME
            tracked_entry = None
            if tracked_team:
                lower_name = tracked_team.lower()
                for entry in entries:
                    if entry["name"].lower() == lower_name:
                        tracked_entry = entry
                        break
                if tracked_entry is None:
                    continue
                entries = [tracked_entry]

            payload_hash = make_payload_hash(entries)
            last_state = await self.repo.get_scoreboard_state(
                config.guild_id, config.ctftime_event_id
            )
            if last_state and last_state.last_hash == payload_hash:
                continue

            changes = []
            if last_state and last_state.last_payload:
                try:
                    previous = json.loads(last_state.last_payload)
                    prev_rank = {e["name"]: e["pos"] for e in previous}
                    for entry in entries[:SCOREBOARD_TOP_N]:
                        name = entry["name"]
                        if name in prev_rank and prev_rank[name] != entry["pos"]:
                            delta = prev_rank[name] - entry["pos"]
                            direction = "up" if delta > 0 else "down"
                            changes.append(
                                f"{name} {direction} to {entry['pos']} ({entry['score']})"
                            )
                except Exception:
                    changes = []

            channel = self.bot.get_channel(config.scoreboard_channel_id)
            if isinstance(channel, discord.TextChannel):
                embed = build_scoreboard_embed(
                    entries, changes, config.url, top_n=SCOREBOARD_TOP_N
                )
                await channel.send(embed=embed)

            await self.repo.upsert_scoreboard_state(
                config.guild_id,
                config.ctftime_event_id,
                payload_hash,
                json.dumps(entries, ensure_ascii=False),
            )


async def setup(bot: commands.Bot) -> None:
    repo: Repository = bot.repo  # type: ignore[attr-defined]
    await bot.add_cog(ScoreboardCog(bot, repo))
