from __future__ import annotations

import hashlib
import json
import re
from urllib.parse import urljoin

import aiohttp
from playwright.async_api import async_playwright


CTFD_CANDIDATES = [
    "/api/v1/scoreboard",
    "/api/v1/scoreboard?count=1000",
    "/scoreboard?format=json",
    "/scores?format=json",
]

RCTF_PAT = re.compile(r"(score|scores|leader|leaderboard|standing|rank)", re.I)


def _looks_like_ctfd_scoreboard(obj: dict) -> bool:
    if not isinstance(obj, dict):
        return False
    data = obj.get("data")
    if not isinstance(data, list) or not data:
        return False
    if not isinstance(data[0], dict):
        return False
    keys = set(data[0].keys())
    return ("name" in keys or "team" in keys) and ("score" in keys or "points" in keys)


def _normalize_entries(entries: list[dict]) -> list[dict]:
    normalized = []
    for idx, entry in enumerate(entries, start=1):
        name = (
            entry.get("name")
            or entry.get("team")
            or entry.get("account_name")
            or entry.get("username")
        )
        if isinstance(name, dict):
            name = name.get("name")
        score = entry.get("score", entry.get("points"))
        pos = entry.get("pos", entry.get("place", entry.get("rank", idx)))
        if name is None or score is None:
            continue
        normalized.append({"pos": int(pos), "name": str(name), "score": float(score)})
    normalized.sort(key=lambda x: x["pos"])
    return normalized


def _find_rctf_entries(payload: dict | list) -> list[dict] | None:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return None
    for key in ("data", "leaderboard", "scores", "result", "items"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
    return None


async def fetch_ctfd_scoreboard(base_url: str, auth_token: str | None = None) -> list[dict]:
    base = base_url.rstrip("/") + "/"
    headers = {"User-Agent": "ctf-bot/1.0"}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    async with aiohttp.ClientSession(headers=headers) as session:
        for path in CTFD_CANDIDATES:
            url = urljoin(base, path)
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                    ct = (resp.headers.get("content-type") or "").lower()
                    if "json" not in ct:
                        continue
                    payload = await resp.json()
            except Exception:
                continue
            if isinstance(payload, dict) and _looks_like_ctfd_scoreboard(payload):
                return _normalize_entries(payload["data"])
    raise RuntimeError("CTFd scoreboard endpoint not found or invalid.")


async def fetch_rctf_scoreboard(url: str, auth_token: str | None = None) -> list[dict]:
    captured = []
    headers = {"User-Agent": "ctf-bot/1.0"}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(extra_http_headers=headers)
        page = await context.new_page()

        async def on_response(resp):
            try:
                if resp.request.resource_type not in ("xhr", "fetch"):
                    return
                if not RCTF_PAT.search(resp.url):
                    return
                ct = (resp.headers.get("content-type") or "").lower()
                if "json" not in ct:
                    return
                payload = await resp.json()
                captured.append({"url": resp.url, "data": payload})
            except Exception:
                return

        page.on("response", on_response)
        await page.goto(url, wait_until="networkidle", timeout=60_000)
        await page.wait_for_timeout(2_000)
        await browser.close()

    if not captured:
        raise RuntimeError("rCTF scoreboard JSON not captured.")

    payload = captured[-1]["data"]
    entries = _find_rctf_entries(payload)
    if entries is None:
        raise RuntimeError("rCTF scoreboard payload missing entries.")
    return _normalize_entries(entries)


def make_payload_hash(entries: list[dict]) -> str:
    normalized = json.dumps(entries, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
