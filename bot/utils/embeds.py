from __future__ import annotations

from datetime import datetime

import discord


DEFAULT_THUMBNAIL_URL = "https://img.freepik.com/free-vector/square-bronze-frame-white-background-vector_53876-170731.jpg"


def _format_time_range(event: dict) -> str:
    start = event.get("start")
    finish = event.get("finish")
    if start and finish:
        return f"{start} → {finish}"
    return "N/A"


def build_event_embed(event: dict, index: int | None = None) -> discord.Embed:
    title = event.get("title") or "CTF Event"
    embed_title = f"{index}. {title}" if index is not None else title
    embed = discord.Embed(title=embed_title, color=discord.Color.gold())
    embed.add_field(name="CTFtime", value=event.get("ctftime_url") or "N/A", inline=False)
    embed.add_field(name="URL", value=event.get("url") or "N/A", inline=False)
    embed.add_field(name="Format", value=event.get("format") or "N/A", inline=False)
    weight_value = event.get("weight")
    if weight_value is None:
        weight_text = "N/A"
    elif isinstance(weight_value, (int, float)):
        weight_text = f"{weight_value:.2f}"
    else:
        weight_text = str(weight_value)
    embed.add_field(name="Rating Weight", value=weight_text, inline=False)
    embed.add_field(name="Time", value=_format_time_range(event), inline=False)

    logo = event.get("logo") or DEFAULT_THUMBNAIL_URL
    embed.set_thumbnail(url=logo)

    return embed


def build_simple_embed(title: str, description: str) -> discord.Embed:
    return discord.Embed(
        title=title, description=description, color=discord.Color.gold()
    )


def build_scoreboard_embed(
    entries: list[dict],
    changes: list[str],
    source_url: str,
    top_n: int = 10,
) -> discord.Embed:
    embed = discord.Embed(title="Scoreboard Update", color=discord.Color.gold())
    embed.add_field(name="Source", value=source_url, inline=False)

    lines = []
    for entry in entries[:top_n]:
        lines.append(f"{entry['pos']}. {entry['name']} — {entry['score']}")
    embed.add_field(name=f"Top {min(top_n, len(entries))}", value="\n".join(lines) or "N/A", inline=False)

    if changes:
        embed.add_field(name="Changes", value="\n".join(changes[:5]), inline=False)

    embed.timestamp = datetime.utcnow()
    return embed


def build_event_embeds_for_page(
    events: list[dict], page: int, page_size: int
) -> list[discord.Embed]:
    total_pages = max(1, (len(events) + page_size - 1) // page_size)
    start_index = page * page_size
    slice_events = events[start_index : start_index + page_size]

    embeds = []
    for idx, event in enumerate(slice_events, start=start_index + 1):
        embeds.append(build_event_embed(event, index=idx))

    if embeds:
        embeds[0].set_footer(text=f"Page {page + 1}/{total_pages}")
    return embeds
