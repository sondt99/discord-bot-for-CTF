from __future__ import annotations

import re

import discord


CHANNELS = [
    "Account",
    "General",
    "REV",
    "PWN",
    "WEB",
    "CRYPTO",
    "FOR",
    "MISC",
    "Scoreboard",
]


def _sanitize_category_name(name: str) -> str:
    name = re.sub(r"\s+", " ", name).strip()
    if len(name) > 100:
        return name[:97] + "..."
    return name


async def create_ctf_category_and_channels(
    guild: discord.Guild, event_title: str
) -> tuple[discord.CategoryChannel, dict[str, int]]:
    category_name = _sanitize_category_name(event_title)
    category = await guild.create_category(name=category_name)

    channels: dict[str, int] = {}
    for channel_name in CHANNELS:
        if channel_name == "Account":
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(
                    view_channel=True, send_messages=False
                )
            }
        else:
            overwrites = {}

        channel = await category.create_text_channel(
            name=channel_name.lower(),
            overwrites=overwrites,
        )
        channels[channel_name] = channel.id

    return category, channels


async def hide_ctf_category_and_channels(
    guild: discord.Guild, category_id: int
) -> None:
    category = guild.get_channel(category_id)
    if not isinstance(category, discord.CategoryChannel):
        raise ValueError("Category not found.")

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False)
    }
    await category.edit(overwrites=overwrites)

    for channel in category.channels:
        await channel.edit(overwrites=overwrites)


async def delete_ctf_category_and_channels(
    guild: discord.Guild, category_id: int
) -> None:
    category = guild.get_channel(category_id)
    if not isinstance(category, discord.CategoryChannel):
        raise ValueError("Category not found.")

    for channel in list(category.channels):
        await channel.delete()
    await category.delete()
