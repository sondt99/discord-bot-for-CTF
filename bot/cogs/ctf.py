from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from bot.db.repository import Repository
from bot.services.ctftime import fetch_event, fetch_upcoming_events
from bot.services.guild_setup import create_ctf_category_and_channels
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
        limit = max(1, min(limit, 50))
        await interaction.response.defer()
        events = await fetch_upcoming_events(limit=limit)
        if not events:
            await interaction.followup.send(
                embed=build_simple_embed("No events", "No upcoming CTFs found.")
            )
            return
        view = CtfPaginationView(events=events, author_id=interaction.user.id)
        embed = build_event_embed(events[0], 0, len(events))
        message = await interaction.followup.send(embed=embed, view=view)
        view.message = message

    @ctf.command(name="join", description="Create category and channels for a CTF")
    @app_commands.describe(event_id="CTFtime event ID")
    async def join(self, interaction: discord.Interaction, event_id: int) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                embed=build_simple_embed("Guild only", "Use this in a server."),
                ephemeral=True,
            )
            return

        existing = await self.repo.get_ctf_event(interaction.guild.id)
        if existing:
            await interaction.response.send_message(
                embed=build_simple_embed(
                    "CTF already configured",
                    f"Current event: {existing.event_title} (ID {existing.ctftime_event_id}).",
                ),
                ephemeral=True,
            )
            return

        await interaction.response.defer()
        event = await fetch_event(event_id)
        event_title = event.get("title") or f"CTF {event_id}"

        category, channels = await create_ctf_category_and_channels(
            interaction.guild, event_title
        )

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


async def setup(bot: commands.Bot) -> None:
    repo: Repository = bot.repo  # type: ignore[attr-defined]
    cog = CtfCog(bot, repo)
    await bot.add_cog(cog)
