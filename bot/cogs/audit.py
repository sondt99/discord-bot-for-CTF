from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import tempfile

import discord
from discord.ext import commands

from bot.config import DATABASE_PATH
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
            await self._restore_db_from_backup(guild)
        if hasattr(self.bot, "backup_ready"):
            self.bot.backup_ready.set()

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
        backup_channel = channels["backup"]

        user = interaction.user
        command_name = command.qualified_name
        log_embed = build_simple_embed(
            "Command Log",
            f"User: {user}\nCommand: /{command_name}\nTime: {datetime.now(timezone.utc).isoformat()}",
        )
        await log_channel.send(embed=log_embed)

        db_path = Path(DATABASE_PATH)
        if db_path.exists():
            backup_embed = build_simple_embed(
                "Database Backup", f"File: {db_path.name}"
            )
            await backup_channel.send(
                embed=backup_embed, file=discord.File(db_path)
            )

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

    async def _restore_db_from_backup(self, guild: discord.Guild) -> None:
        _, channels = await ensure_bot_admin_category(guild)
        backup_channel = channels["backup"]
        db_path = Path(DATABASE_PATH)
        target_name = db_path.name

        latest = None
        async for message in backup_channel.history(limit=50):
            for attachment in message.attachments:
                if attachment.filename == target_name:
                    latest = attachment
                    break
            if latest:
                break

        if latest is None:
            return

        data = await latest.read()
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(data)
            tmp_path = Path(tmp.name)

        tmp_path.replace(db_path)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AuditCog(bot))
