from __future__ import annotations

from datetime import datetime, timedelta, timezone

import aiohttp


BASE_URL = "https://ctftime.org/api/v1"


def _unix_now() -> int:
    return int(datetime.now(timezone.utc).timestamp())


async def fetch_upcoming_events(limit: int = 20, window_days: int = 180) -> list[dict]:
    start_ts = _unix_now()
    finish_ts = int((datetime.now(timezone.utc) + timedelta(days=window_days)).timestamp())
    url = f"{BASE_URL}/events/?limit={limit}&start={start_ts}&finish={finish_ts}"

    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as resp:
            resp.raise_for_status()
            return await resp.json()


async def fetch_event(event_id: int) -> dict:
    url = f"{BASE_URL}/events/{event_id}/"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as resp:
            resp.raise_for_status()
            return await resp.json()
