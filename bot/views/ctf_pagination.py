from __future__ import annotations

import discord

from bot.utils.embeds import build_event_embed


class CtfPaginationView(discord.ui.View):
    def __init__(self, events: list[dict], author_id: int, timeout: int = 180):
        super().__init__(timeout=timeout)
        self.events = events
        self.author_id = author_id
        self.page = 0
        self.message: discord.Message | None = None

    def _build_embed(self) -> discord.Embed:
        return build_event_embed(self.events[self.page], self.page, len(self.events))

    async def _update(self, interaction: discord.Interaction) -> None:
        embed = self._build_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="Not allowed",
                    description="Only the command author can use these buttons.",
                ),
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if self.page > 0:
            self.page -= 1
        await self._update(interaction)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if self.page < len(self.events) - 1:
            self.page += 1
        await self._update(interaction)

    async def on_timeout(self) -> None:
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
        if self.message:
            await self.message.edit(view=self)
