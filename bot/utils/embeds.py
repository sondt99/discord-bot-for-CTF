from __future__ import annotations

from datetime import datetime

import discord


def build_event_embed(event: dict, page: int, total: int) -> discord.Embed:
    title = event.get("title") or "CTF Event"
    description = (event.get("description") or "").strip()
    if len(description) > 600:
        description = description[:597] + "..."

    embed = discord.Embed(title=title, description=description or None)
    embed.add_field(name="CTFtime", value=event.get("ctftime_url") or "N/A", inline=False)
    embed.add_field(name="URL", value=event.get("url") or "N/A", inline=False)
    embed.add_field(name="Format", value=event.get("format") or "N/A", inline=True)

    start = event.get("start")
    finish = event.get("finish")
    if start and finish:
        embed.add_field(name="Start", value=start, inline=True)
        embed.add_field(name="Finish", value=finish, inline=True)

    logo = event.get("logo")
    if logo:
        embed.set_thumbnail(url=logo)

    embed.set_footer(text=f"Page {page + 1}/{total}")
    return embed


def build_simple_embed(title: str, description: str) -> discord.Embed:
    return discord.Embed(title=title, description=description)


def build_scoreboard_embed(
    entries: list[dict],
    changes: list[str],
    source_url: str,
    top_n: int = 10,
) -> discord.Embed:
    embed = discord.Embed(title="Scoreboard Update")
    embed.add_field(name="Source", value=source_url, inline=False)

    lines = []
    for entry in entries[:top_n]:
        lines.append(f"{entry['pos']}. {entry['name']} — {entry['score']}")
    embed.add_field(name=f"Top {min(top_n, len(entries))}", value="\n".join(lines) or "N/A", inline=False)

    if changes:
        embed.add_field(name="Changes", value="\n".join(changes[:5]), inline=False)

    embed.timestamp = datetime.utcnow()
    return embed
