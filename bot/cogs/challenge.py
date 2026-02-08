from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from bot.db.repository import Repository
from bot.utils.embeds import build_simple_embed


# Topic channels where /challenge is allowed
_TOPIC_CHANNELS = {"rev", "pwn", "web", "crypto", "for", "misc"}


class ChallengeCog(commands.Cog):
    def __init__(self, bot: commands.Bot, repo: Repository) -> None:
        self.bot = bot
        self.repo = repo

    # ── helpers ───────────────────────────────────────────────────────

    async def _find_event_by_channel(
        self, guild_id: int, channel: discord.TextChannel
    ):
        """Return the CtfEvent whose category owns this channel, or None."""
        if channel.category_id is None:
            return None
        events = await self.repo.list_ctf_events(guild_id)
        for event in events:
            if event.category_id == channel.category_id:
                return event
        return None

    @staticmethod
    def _channel_topic(channel: discord.TextChannel) -> str | None:
        """Return the normalised topic name if the channel is a topic channel."""
        name = channel.name.lower()
        if name in _TOPIC_CHANNELS:
            return name.upper()
        return None

    # ── /challenge <name> ─────────────────────────────────────────────

    @app_commands.command(
        name="challenge",
        description="Create a thread for a challenge in the current topic channel",
    )
    @app_commands.describe(name="Challenge name")
    async def challenge(self, interaction: discord.Interaction, name: str) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                embed=build_simple_embed("Guild only", "Use this in a server."),
            )
            return

        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                embed=build_simple_embed(
                    "Wrong channel type",
                    "Use this command in a text channel under a CTF category.",
                ),
                ephemeral=True,
            )
            return

        topic = self._channel_topic(channel)
        if topic is None:
            await interaction.response.send_message(
                embed=build_simple_embed(
                    "Wrong channel",
                    f"Use this in a topic channel ({', '.join(sorted(_TOPIC_CHANNELS))}).",
                ),
                ephemeral=True,
            )
            return

        event = await self._find_event_by_channel(interaction.guild.id, channel)
        if event is None:
            # Debug: show what the bot sees to help diagnose
            events = await self.repo.list_ctf_events(interaction.guild.id)
            db_info = "\n".join(
                f"- {e.event_title}: category_id={e.category_id}"
                for e in events
            ) or "(no events in DB for this guild)"
            await interaction.response.send_message(
                embed=build_simple_embed(
                    "No CTF found",
                    f"This channel does not belong to any joined CTF event.\n\n"
                    f"**Debug:**\n"
                    f"Guild ID: `{interaction.guild.id}`\n"
                    f"Channel category_id: `{channel.category_id}`\n"
                    f"DB events:\n{db_info}",
                ),
                ephemeral=True,
            )
            return

        # Check duplicate challenge name within same event + category
        existing = await self.repo.list_challenges(
            interaction.guild.id, event.ctftime_event_id
        )
        for chall in existing:
            if (
                chall.challenge_name.lower() == name.lower()
                and chall.category.lower() == topic.lower()
            ):
                await interaction.response.send_message(
                    embed=build_simple_embed(
                        "Duplicate challenge",
                        f"Challenge **{name}** already exists in {topic} (<#{chall.thread_id}>).",
                    ),
                    ephemeral=True,
                )
                return

        await interaction.response.defer()

        # Create thread
        thread = await channel.create_thread(
            name=name,
            type=discord.ChannelType.public_thread,
        )

        # Save to DB
        challenge_id = await self.repo.create_challenge(
            guild_id=interaction.guild.id,
            ctftime_event_id=event.ctftime_event_id,
            challenge_name=name,
            category=topic,
            thread_id=thread.id,
            channel_id=channel.id,
        )

        await thread.send(
            embed=build_simple_embed(
                f"Challenge: {name}",
                f"**CTF:** {event.event_title}\n"
                f"**Category:** {topic}\n"
                f"**Status:** Open\n\n"
                f"Good luck! When solved, an admin will use `/done` here.",
            )
        )

        await interaction.followup.send(
            embed=build_simple_embed(
                "Challenge created",
                f"Thread **{name}** created in {topic} → {thread.mention}",
            )
        )

    # ── /done @user ... ───────────────────────────────────────────────

    @app_commands.command(
        name="done",
        description="Mark the current challenge thread as solved (admin only)",
    )
    @app_commands.describe(
        solver="The member who solved this challenge",
        solver2="Additional solver (optional)",
        solver3="Additional solver (optional)",
        solver4="Additional solver (optional)",
    )
    @app_commands.default_permissions(administrator=True)
    async def done(
        self,
        interaction: discord.Interaction,
        solver: discord.Member,
        solver2: discord.Member | None = None,
        solver3: discord.Member | None = None,
        solver4: discord.Member | None = None,
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                embed=build_simple_embed("Guild only", "Use this in a server."),
                ephemeral=True,
            )
            return

        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                embed=build_simple_embed(
                    "Admin only", "Only admins can use this command."
                ),
                ephemeral=True,
            )
            return

        thread = interaction.channel
        if not isinstance(thread, discord.Thread):
            await interaction.response.send_message(
                embed=build_simple_embed(
                    "Wrong channel",
                    "Use this command inside a challenge thread.",
                ),
                ephemeral=True,
            )
            return

        challenge = await self.repo.get_challenge_by_thread(thread.id)

        # If thread wasn't created by /challenge, auto-register it
        if challenge is None:
            parent = thread.parent
            if not isinstance(parent, discord.TextChannel):
                await interaction.response.send_message(
                    embed=build_simple_embed(
                        "Wrong channel",
                        "Cannot determine parent channel for this thread.",
                    ),
                    ephemeral=True,
                )
                return

            event = await self._find_event_by_channel(interaction.guild.id, parent)
            if event is None:
                await interaction.response.send_message(
                    embed=build_simple_embed(
                        "No CTF found",
                        "This thread's parent channel does not belong to any joined CTF event.",
                    ),
                    ephemeral=True,
                )
                return

            topic = self._channel_topic(parent)
            category_name = topic or parent.name.upper()

            await self.repo.create_challenge(
                guild_id=interaction.guild.id,
                ctftime_event_id=event.ctftime_event_id,
                challenge_name=thread.name,
                category=category_name,
                thread_id=thread.id,
                channel_id=parent.id,
            )
            challenge = await self.repo.get_challenge_by_thread(thread.id)

        if challenge.status == "done":
            await interaction.response.send_message(
                embed=build_simple_embed(
                    "Already solved",
                    "This challenge was already marked as done.",
                ),
                ephemeral=True,
            )
            return

        # Collect unique solver IDs
        solvers = [solver]
        for s in (solver2, solver3, solver4):
            if s is not None and s.id not in [sv.id for sv in solvers]:
                solvers.append(s)
        solver_ids = [s.id for s in solvers]

        await interaction.response.defer()

        # Update DB
        await self.repo.mark_challenge_done(thread.id, solver_ids)

        # Rename thread: "challenge name" → "[DONE] challenge name"
        if thread.name.upper().startswith("[DONE]"):
            new_name = thread.name
        else:
            new_name = f"[DONE] {challenge.challenge_name}"
            await thread.edit(name=new_name)

        solver_mentions = ", ".join(s.mention for s in solvers)
        await interaction.followup.send(
            embed=build_simple_embed(
                "Challenge Solved!",
                f"**Challenge:** {challenge.challenge_name}\n"
                f"**Category:** {challenge.category}\n"
                f"**Solved by:** {solver_mentions}\n\n"
                f"Thread renamed to `{new_name}`.",
            )
        )

    # ── /challenges ───────────────────────────────────────────────────

    @app_commands.command(
        name="challenges",
        description="List all challenges for a CTF event",
    )
    @app_commands.describe(event_id="CTFtime event ID (required if multiple CTFs)")
    async def challenges(
        self, interaction: discord.Interaction, event_id: int | None = None
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                embed=build_simple_embed("Guild only", "Use this in a server."),
            )
            return

        # Resolve event
        events = await self.repo.list_ctf_events(interaction.guild.id)
        if not events:
            await interaction.response.send_message(
                embed=build_simple_embed(
                    "No active CTF", "No CTF events joined in this server."
                ),
            )
            return

        if event_id is None:
            # Try to infer from current channel's category
            channel = interaction.channel
            if isinstance(channel, discord.TextChannel) and channel.category:
                matched = next(
                    (e for e in events if e.category_id == channel.category_id),
                    None,
                )
                if matched:
                    event = matched
                elif len(events) == 1:
                    event = events[0]
                else:
                    await interaction.response.send_message(
                        embed=build_simple_embed(
                            "Need event ID",
                            "Multiple CTF events. Please provide event_id.",
                        ),
                    )
                    return
            elif len(events) == 1:
                event = events[0]
            else:
                await interaction.response.send_message(
                    embed=build_simple_embed(
                        "Need event ID",
                        "Multiple CTF events. Please provide event_id.",
                    ),
                )
                return
        else:
            event = next(
                (e for e in events if e.ctftime_event_id == event_id), None
            )
            if event is None:
                await interaction.response.send_message(
                    embed=build_simple_embed(
                        "Event not found",
                        f"Event ID {event_id} not found in this server.",
                    ),
                )
                return

        challs = await self.repo.list_challenges(
            interaction.guild.id, event.ctftime_event_id
        )
        if not challs:
            await interaction.response.send_message(
                embed=build_simple_embed(
                    f"Challenges — {event.event_title}",
                    "No challenges created yet. Use `/challenge` in a topic channel.",
                ),
            )
            return

        # Group by category
        by_cat: dict[str, list] = {}
        for ch in challs:
            by_cat.setdefault(ch.category, []).append(ch)

        embed = discord.Embed(
            title=f"Challenges — {event.event_title}",
            color=discord.Color.gold(),
        )

        total = len(challs)
        solved = sum(1 for c in challs if c.status == "done")
        embed.description = f"**Total:** {total} | **Solved:** {solved} | **Open:** {total - solved}"

        for cat in sorted(by_cat.keys()):
            lines = []
            for ch in by_cat[cat]:
                status_icon = "\u2705" if ch.status == "done" else "\u23f3"
                solver_text = ""
                if ch.status == "done" and ch.solved_by:
                    solver_text = " — " + ", ".join(
                        f"<@{uid}>" for uid in ch.solved_by
                    )
                lines.append(f"{status_icon} {ch.challenge_name}{solver_text}")
            embed.add_field(
                name=cat, value="\n".join(lines), inline=False
            )

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    repo: Repository = bot.repo  # type: ignore[attr-defined]
    await bot.add_cog(ChallengeCog(bot, repo))
