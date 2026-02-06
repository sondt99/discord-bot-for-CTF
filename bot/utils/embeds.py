from __future__ import annotations

from datetime import datetime, timedelta, timezone
import re

import discord

from bot.config import TIMEZONE


def _parse_timezone_offset(value: str) -> timezone:
    match = re.fullmatch(r"UTC([+-])(\d{1,2})", value.strip())
    if not match:
        return timezone.utc
    sign = 1 if match.group(1) == "+" else -1
    hours = int(match.group(2))
    return timezone(sign * timedelta(hours=hours))


def _format_time_range(event: dict) -> str:
    start = event.get("start")
    finish = event.get("finish")
    if not start or not finish:
        return "N/A"

    tz = _parse_timezone_offset(TIMEZONE or "UTC+0")
    start_dt = datetime.fromisoformat(start).astimezone(tz)
    finish_dt = datetime.fromisoformat(finish).astimezone(tz)
    return f"{start_dt:%Y-%m-%d %H:%M} → {finish_dt:%Y-%m-%d %H:%M}"


def build_event_embed(event: dict, index: int | None = None) -> discord.Embed:
    title = event.get("title") or "CTF Event"
    embed_title = f"{index}. {title}" if index is not None else title
    embed = discord.Embed(title=embed_title, color=discord.Color.gold())
    weight_value = event.get("weight")
    if weight_value is None:
        weight_text = "N/A"
    elif isinstance(weight_value, (int, float)):
        weight_text = f"{weight_value:.2f}"
    else:
        weight_text = str(weight_value)
    embed.add_field(name="Format", value=event.get("format") or "N/A", inline=True)
    embed.add_field(name="Rating Weight", value=weight_text, inline=True)

    embed.add_field(name="Time", value=_format_time_range(event), inline=False)

    ctftime_url = event.get("ctftime_url")
    site_url = event.get("url")
    embed.add_field(name="CTFtime", value=ctftime_url or "N/A", inline=True)
    embed.add_field(name="URL", value=site_url or "N/A", inline=True)

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


def _format_event_block(event: dict) -> str:
    weight_value = event.get("weight")
    if weight_value is None:
        weight_text = "N/A"
    elif isinstance(weight_value, (int, float)):
        weight_text = f"{weight_value:.2f}"
    else:
        weight_text = str(weight_value)
    title = event.get("title") or "CTF Event"
    lines = [
        f"Format: {event.get('format') or 'N/A'} | Rating Weight: {weight_text}",
        f"Time: {_format_time_range(event)}",
        f"CTFtime: {event.get('ctftime_url') or 'N/A'}",
        f"URL: {event.get('url') or 'N/A'}",
        "---",
    ]
    return "\n".join(lines)


def build_events_page_embed(
    events: list[dict], page: int, page_size: int
) -> discord.Embed:
    total_pages = max(1, (len(events) + page_size - 1) // page_size)
    start_index = page * page_size
    slice_events = events[start_index : start_index + page_size]

    embed = discord.Embed(title="Upcoming CTFs", color=discord.Color.gold())
    for event in slice_events:
        embed.add_field(
            name=event.get("title") or "CTF Event",
            value=_format_event_block(event),
            inline=False,
        )

    embed.set_footer(text=f"Page {page + 1}/{total_pages}")
    return embed
