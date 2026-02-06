from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from bot.db.repository import Repository
from bot.services.ctftime import fetch_event, fetch_upcoming_events
from bot.services.guild_setup import (
    create_ctf_category_and_channels,
    hide_ctf_category_and_channels,
)
from bot.utils.embeds import build_event_embed, build_simple_embed
from bot.views.ctf_pagination import CtfPaginationView


class CtfCog(commands.Cog):
    ctf = app_commands.Group(name="ctf", description="CTFtime commands")

    def __init__(self, bot: commands.Bot, repo: Repository) -> None:
        self.bot = bot
        self.repo = repo

    @ctf.command(name="upcoming", description="List upcoming CTF events")
    @app_commands.describe(limit="Number of events to show (max 50)")
    async def upcoming(self, interaction: discord.Interaction, limit: int = 10) -> None:
        limit = max(3, min(limit, 50))
        await interaction.response.defer()
        try:
            events = await fetch_upcoming_events(limit=limit)
        except Exception:
            await interaction.followup.send(
                embed=build_simple_embed(
                    "CTFtime error",
                    "Khong the lay danh sach giai. Thu lai sau.",
                )
            )
            return
        if not events:
            await interaction.followup.send(
                embed=build_simple_embed("No events", "No upcoming CTFs found.")
            )
            return
        view = CtfPaginationView(events=events, author_id=interaction.user.id, page_size=3)
        embeds = view._build_embeds()
        message = await interaction.followup.send(embeds=embeds, view=view)
        view.message = message

    @ctf.command(name="join", description="Create category and channels for a CTF")
    @app_commands.describe(event_id="CTFtime event ID")
    async def join(self, interaction: discord.Interaction, event_id: int) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                embed=build_simple_embed("Guild only", "Use this in a server."),
            )
            return

        existing = await self.repo.get_ctf_event(interaction.guild.id, event_id)
        if existing:
            await interaction.response.send_message(
                embed=build_simple_embed(
                    "CTF already configured",
                    f"Event da co: {existing.event_title} (ID {existing.ctftime_event_id}).",
                ),
            )
            return

        await interaction.response.defer()
        try:
            event = await fetch_event(event_id)
        except Exception:
            await interaction.followup.send(
                embed=build_simple_embed(
                    "CTFtime error",
                    "Khong the lay thong tin giai. Kiem tra ID.",
                )
            )
            return
        event_title = event.get("title") or f"CTF {event_id}"

        try:
            category, channels = await create_ctf_category_and_channels(
                interaction.guild, event_title
            )
        except discord.Forbidden:
            await interaction.followup.send(
                embed=build_simple_embed(
                    "Missing permissions",
                    "Bot can thieu quyen Manage Channels.",
                )
            )
            return
        except Exception:
            await interaction.followup.send(
                embed=build_simple_embed(
                    "Setup error",
                    "Khong the tao category/channels. Thu lai sau.",
                )
            )
            return

        await self.repo.upsert_ctf_event(
            guild_id=interaction.guild.id,
            ctftime_event_id=event_id,
            event_title=event_title,
            category_id=category.id,
            channels=channels,
            start_time=event.get("start"),
            finish_time=event.get("finish"),
        )

        await interaction.followup.send(
            embed=build_simple_embed(
                "CTF configured",
                f"Created category `{category.name}` with {len(channels)} channels.",
            )
        )

    async def _resolve_event(
        self, interaction: discord.Interaction, event_id: int | None
    ):
        events = await self.repo.list_ctf_events(interaction.guild.id)
        if not events:
            await interaction.response.send_message(
                embed=build_simple_embed(
                    "No active CTF",
                    "Run /ctf join first to create channels.",
                )
            )
            return None
        if event_id is None:
            if len(events) == 1:
                return events[0]
            await interaction.response.send_message(
                embed=build_simple_embed(
                    "Need event ID",
                    "Server co nhieu giai. Hay nhap event_id.",
                )
            )
            return None
        event = next((e for e in events if e.ctftime_event_id == event_id), None)
        if event is None:
            await interaction.response.send_message(
                embed=build_simple_embed(
                    "Event not found",
                    f"Khong tim thay event ID {event_id} trong server.",
                )
            )
        return event

    @ctf.command(name="list", description="List joined CTF events")
    async def list_events(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                embed=build_simple_embed("Guild only", "Use this in a server."),
            )
            return
        events = await self.repo.list_ctf_events(interaction.guild.id)
        if not events:
            await interaction.response.send_message(
                embed=build_simple_embed("No active CTF", "Chua co giai nao."),
            )
            return

        lines = []
        for event in events:
            lines.append(f"{event.ctftime_event_id} - {event.event_title}")

        await interaction.response.send_message(
            embed=build_simple_embed("CTF Events", "\n".join(lines)),
        )

    async def _handle_hidden(
        self, interaction: discord.Interaction, event_id: int | None
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                embed=build_simple_embed("Guild only", "Use this in a server."),
            )
            return
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                embed=build_simple_embed(
                    "Admin only",
                    "Chi admin moi duoc dung lenh nay.",
                )
            )
            return
        event = await self._resolve_event(interaction, event_id)
        if event is None:
            return

        await interaction.response.defer()
        try:
            await hide_ctf_category_and_channels(interaction.guild, event.category_id)
        except discord.Forbidden:
            await interaction.followup.send(
                embed=build_simple_embed(
                    "Missing permissions",
                    "Bot can thieu quyen Manage Channels.",
                )
            )
            return
        except Exception:
            await interaction.followup.send(
                embed=build_simple_embed(
                    "Hide error",
                    "Khong the an category/channels. Thu lai sau.",
                )
            )
            return

        await interaction.followup.send(
            embed=build_simple_embed(
                "Hidden",
                f"Da an category `{event.event_title}`.",
            )
        )

    @ctf.command(name="hidden", description="Hide CTF category from non-admins")
    @app_commands.describe(event_id="CTFtime event ID (required if multiple)")
    @app_commands.default_permissions(administrator=True)
    async def hidden(
        self, interaction: discord.Interaction, event_id: int | None = None
    ) -> None:
        await self._handle_hidden(interaction, event_id)


async def setup(bot: commands.Bot) -> None:
    repo: Repository = bot.repo  # type: ignore[attr-defined]
    cog = CtfCog(bot, repo)
    await bot.add_cog(cog)
