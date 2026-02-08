from __future__ import annotations

from datetime import datetime, timezone

import discord
from discord.ext import commands

from bot.services.guild_setup import ensure_bot_admin_category
from bot.utils.embeds import build_simple_embed


class AuditCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.ready_once = False

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        if self.ready_once:
            return
        self.ready_once = True
        for guild in self.bot.guilds:
            try:
                await ensure_bot_admin_category(guild)
            except Exception:
                continue

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild) -> None:
        try:
            await ensure_bot_admin_category(guild)
        except Exception:
            return

    @commands.Cog.listener()
    async def on_app_command_completion(
        self, interaction: discord.Interaction, command: discord.app_commands.Command
    ) -> None:
        if interaction.guild is None:
            return

        try:
            _, channels = await ensure_bot_admin_category(interaction.guild)
        except Exception:
            return

        log_channel = channels["log"]

        user = interaction.user
        command_name = command.qualified_name
        log_embed = build_simple_embed(
            "Command Log",
            f"User: {user}\nCommand: /{command_name}\nTime: {datetime.now(timezone.utc).isoformat()}",
        )
        await log_channel.send(embed=log_embed)

    @commands.Cog.listener()
    async def on_app_command_error(
        self,
        interaction: discord.Interaction,
        error: discord.app_commands.AppCommandError,
    ) -> None:
        if interaction.guild is None:
            return
        try:
            _, channels = await ensure_bot_admin_category(interaction.guild)
        except Exception:
            return
        log_channel = channels["log"]
        log_embed = build_simple_embed(
            "Command Error",
            f"Error: {error}",
        )
        await log_channel.send(embed=log_embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AuditCog(bot))
